from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .agents import (
    VisionAgent, SpeechAgent, CaptionAgent, RhythmAgent, CreativeAgent,
    PlatformAgent, QualityAgent, SceneAgent, CopyAgent,
)
from .cache import AgentCache
from .contracts import AgentResult
from .compiler import compile_edit_plan
from .provider_config import load_provider_config
from .providers import ProviderRegistry
from .runtime import AgentPolicy, ProviderBackedAgent
from .blackboard import Blackboard
from .learning_db import LearningDB
from .final_director import FinalDirector


class AgentRunResult:
    def __init__(self, results, compiled):
        self.results, self.compiled = results, compiled


class MultiAgentOrchestrator:
    """Runs specialist agents independently, then creates exactly one final plan.

    Each agent may use a different provider/model. A provider failure is isolated:
    retry -> next fallback provider -> mature built-in agent. Successful results are
    cached using a fingerprint that includes provider/model policy.
    """

    def __init__(
        self,
        max_workers: int = 6,
        cache: AgentCache | None = None,
        provider_config: dict[str, Any] | None = None,
        enable_real_providers: bool | None = None,
    ):
        self.max_workers = max(2, max_workers)
        self.cache = cache or AgentCache()
        self.config = provider_config or load_provider_config()
        if enable_real_providers is None:
            env_flag = os.getenv("AI_DIRECTOR_ENABLE_PROVIDERS")
            if env_flag is not None:
                enable_real_providers = env_flag.lower() not in {"0", "false", "no", "off"}
            else:
                enable_real_providers = bool(self.config.get("enable_real_providers", False))
        self.enable_real_providers = enable_real_providers
        self.registry = ProviderRegistry.from_dict(self.config.get("providers", {}))
        try:
            from app.runtime.paths import learning_db_file
            self.learning = LearningDB(learning_db_file())
        except Exception:
            self.learning = None
        self.final_director = FinalDirector()

        builtin = [
            VisionAgent(), SpeechAgent(), CaptionAgent(), RhythmAgent(),
            CreativeAgent(), PlatformAgent(), QualityAgent(), SceneAgent(), CopyAgent(),
        ]
        self.agents = [self._wrap(a) for a in builtin]

    def _wrap(self, agent):
        if not self.enable_real_providers:
            return agent
        raw = self.config.get("agents", {}).get(agent.name, {})
        # Specialist model calls are opt-in. This is the main CPU/RAM guardrail:
        # many logical agents, at most one model process by default (Final Director).
        if not raw or not bool(raw.get("enabled", False)):
            return agent
        return ProviderBackedAgent(
            agent,
            self.registry,
            AgentPolicy(
                provider=str(raw.get("provider", "builtin")),
                fallback=list(raw.get("fallback", ["builtin"])),
                retries=int(raw.get("retries", 1)),
                retry_delay_s=float(raw.get("retry_delay_s", 0.25)),
                model=str(raw.get("model", "")),
            ),
        )

    def run(self, context: dict, use_cache=True) -> AgentRunResult:
        """Run specialists in dependency phases, sharing a compact blackboard.

        Phase A is independent sensing. Phase B consumes Phase A findings. Only the
        final director gets the complete compact evidence set. This avoids loading
        many local models at once and prevents contradictory specialist decisions.
        """
        # Build one shared multimodal timeline once. Vision/Speech/Rhythm/Creative
        # agents consume this compact context instead of independently re-reading media.
        try:
            from app.ai.scene_context import build_scene_context, summarize_scene_context
            context = dict(context)
            context["scene_context"] = build_scene_context(context)
            # One optional multimodal pass enriches the shared timeline. Every
            # specialist and the final director then reuse the same visual evidence.
            if self.enable_real_providers:
                from app.ai.scene_context_enricher import enrich_scene_context
                vision_cfg = self.config.get("shared_vision", {})
                if bool(vision_cfg.get("enabled", False)):
                    context["scene_context"] = enrich_scene_context(
                        context["scene_context"], context, self.registry,
                        provider_name=str(vision_cfg.get("provider", "local_vision")),
                        max_scenes=int(vision_cfg.get("max_scenes", 12)),
                    )
            context["scene_context_summary"] = summarize_scene_context(context["scene_context"])
        except Exception:
            context = dict(context)
        board = Blackboard(context=dict(context))
        profile = context.get("profile", "shorts")
        try:
            from app.youtube.manager import YouTubeIntelligenceManager
            youtube_dna = YouTubeIntelligenceManager.load()
            if youtube_dna:
                context = dict(context)
                context["youtube_channel_dna"] = youtube_dna
        except Exception:
            pass
        if self.learning:
            context = dict(context)
            context["learning_hints"] = self.learning.hints(profile)

        # Channel Brain fuses public YouTube DNA, first-party analytics and local learning
        # into one compact, deterministic prior. It never loads another model.
        try:
            from app.ai.channel_brain import build_channel_brain
            context = dict(context)
            reference_edit = context.get("reference_edit_analysis", {})
            # Optional local reference videos. Fast mode uses ffprobe only; deep mode
            # enables one-thread FFmpeg scene/silence analysis when explicitly requested.
            paths = context.get("reference_video_paths", [])
            if paths and not reference_edit:
                from app.reference.edit_dna import analyze_reference_videos
                reference_edit = analyze_reference_videos(
                    paths, deep=bool(context.get("reference_edit_deep", False)),
                    max_videos=int(context.get("reference_edit_max_videos", 20)),
                )
                context["reference_edit_analysis"] = reference_edit
            context["channel_brain"] = build_channel_brain(
                context.get("youtube_channel_dna"),
                context.get("youtube_analytics", []),
                context.get("learning_hints", {}),
                reference_edit,
            ).to_dict()
        except Exception:
            pass

        # Keep the local model count at one: if real providers are enabled, only the
        # configured final director provider is called by default. Specialist agents
        # remain cheap deterministic analyzers unless explicitly overridden.
        phase_a = ["vision", "speech", "rhythm", "scene", "platform"]
        phase_b = ["caption", "creative", "quality", "copy"]
        results = {}
        for names in (phase_a, phase_b):
            phase_agents = [a for a in self.agents if a.name in names]
            if names == phase_b:
                # Give dependent specialists the current blackboard evidence.
                context["collaboration"] = board.snapshot()
            phase_results = self._run_agent_list(phase_agents, context, use_cache)
            for name, result in phase_results.items():
                results[name] = result
                board.publish(name, result)

        # One final synthesis call, never one LLM per specialist by default.
        final_provider = None
        if self.enable_real_providers and self.config.get("final_director", {}).get("enabled", True):
            raw = self.config.get("final_director", {})
            provider_name = str(raw.get("provider", "strong_llm"))
            try:
                final_provider = self.registry.resolve(provider_name)
            except Exception:
                final_provider = None
        final = self.final_director.synthesize(results, context, final_provider)
        results[final.agent] = final
        board.publish(final.agent, final)

        compiled = compile_edit_plan(results, context)
        compiled.metadata.update({
            "parallel_agents": True, "collaborative_blackboard": True,
            "dependency_phases": [phase_a, phase_b], "final_director": final.to_dict(),
            "render_separate": True, "cache_enabled": bool(use_cache),
            "provider_layer": True, "real_providers_enabled": self.enable_real_providers,
            "single_model_synthesis": True, "learning_db": bool(self.learning),
        })
        if self.learning:
            try:
                run_id = self.learning.record_run(
                    context.get("source_fingerprint", ""), profile, compiled.to_dict())
                compiled.metadata["learning_run_id"] = run_id
            except Exception:
                pass
        return AgentRunResult(results, compiled)

    def autonomous_revision(self, compiled_plan: dict, evaluate, *, max_rounds: int = 3, min_improvement: float = 0.5):
        """Run the low-cost autonomous revision loop on a compiled plan.

        ``evaluate`` is supplied by the existing preview/QC pipeline and may render
        real media. No additional AI model is loaded by this controller.
        """
        from app.ai.autonomous_revision import RevisionPolicy, run_revision_loop
        from app.ai.retention_predictor import predict_retention
        from app.ai.channel_brain import score_plan_against_brain, ChannelBrainProfile
        brain_data = compiled_plan.get("channel_brain") or compiled_plan.get("metadata", {}).get("channel_brain")
        brain = None
        if isinstance(brain_data, dict):
            try:
                brain = ChannelBrainProfile(**{k: brain_data[k] for k in ChannelBrainProfile.__dataclass_fields__ if k in brain_data})
            except Exception:
                brain = None
        def brain_score(plan):
            if brain is None:
                return 1.0
            return float(score_plan_against_brain(plan, brain).get("score", 1.0))
        def retention_score(plan):
            try:
                pred = predict_retention(plan, channel_brain=brain_data if isinstance(brain_data, dict) else None)
                plan.setdefault("metadata", {})["retention_prediction"] = pred.to_dict()
                return float(pred.score)
            except Exception:
                return 70.0
        return run_revision_loop(
            compiled_plan, evaluate,
            policy=RevisionPolicy(max_rounds=max_rounds, min_improvement=min_improvement),
            brain_score=brain_score, retention_score=retention_score,
        )

    def regional_revision(self, compiled_plan: dict, hotspot: dict | Any, evaluate=None, *, max_candidates: int = 3):
        """Revise only one retention hotspot; no additional AI model is loaded."""
        from app.ai.retention_hotspots import RetentionHotspot
        from app.ai.regional_revision import RegionalRevisionPolicy, revise_hotspot
        if isinstance(hotspot, dict):
            hs = RetentionHotspot(
                float(hotspot.get("start", 0.0)), float(hotspot.get("end", 0.0)),
                str(hotspot.get("reason", "retention_risk")), str(hotspot.get("severity", "medium")),
                float(hotspot.get("confidence", 0.0)), str(hotspot.get("source", "retention_predictor")),
            )
        else:
            hs = hotspot
        return revise_hotspot(compiled_plan, hs, evaluate, policy=RegionalRevisionPolicy(max_candidates=max_candidates))

    def record_feedback(self, run_id: int, rating: float, notes: str = "", outcome: dict | None = None):
        """Store human feedback; future runs use aggregated signals, not raw prompts."""
        if not self.learning:
            return False
        score = max(0.0, min(1.0, float(rating) / 5.0 if float(rating) > 1 else float(rating)))
        payload = dict(outcome or {})
        payload["notes"] = notes
        self.learning.record_outcome(int(run_id), score, payload, float(rating))
        self.learning.add_signal(int(run_id), "user_rating", score, source="user")
        return True

    def record_performance(self, run_id: int, metrics: dict[str, float]):
        """Feed real post-publish metrics into the local learning memory."""
        if not self.learning:
            return False
        vals = {k: float(v) for k,v in metrics.items() if isinstance(v, (int,float))}
        score = 0.0
        parts = []
        for key, value in vals.items():
            normalized = max(0.0, min(1.0, value if value <= 1 else value / 100.0))
            self.learning.add_signal(int(run_id), key, normalized, source="analytics")
            parts.append(normalized)
        if parts:
            score = sum(parts) / len(parts)
        self.learning.record_outcome(int(run_id), score, vals)
        return True

    def _run_agent_list(self, agents, context, use_cache):
        results = {}
        def task(agent):
            fp = agent.fingerprint(context)
            if use_cache:
                hit = self.cache.get(agent.name, fp)
                if hit:
                    return hit
            result = agent.run(context)
            if result.status == "ok":
                self.cache.put(result, fp)
            return result
        with ThreadPoolExecutor(
            max_workers=min(self.max_workers, max(1, len(agents))),
            thread_name_prefix="ai-agent"
        ) as pool:
            futures = {pool.submit(task, a): a.name for a in agents}
            for f in as_completed(futures):
                name = futures[f]
                try:
                    results[name] = f.result()
                except Exception as exc:
                    results[name] = AgentResult(name, "1.0", "error", 0, {}, error=str(exc))
        return results

    def _run_agents(self, context, use_cache):
        # Backward-compatible helper used by provider overrides.
        return self._run_agent_list(self.agents, context, use_cache)

    def _run_with_overrides(self, context, use_cache):
        """Create only the requested provider policies for this run."""
        overrides = context.get("agent_providers", {})
        original = self.agents
        wrapped = []
        by_name = {a.name: a for a in original}
        for name, policy in overrides.items():
            base = by_name.get(name)
            if base is None:
                continue
            # unwrap if already wrapped; use the original implementation.
            base_agent = getattr(base, "agent", base)
            cfg = {
                "provider": policy.get("provider", "builtin"),
                "fallback": policy.get("fallback", ["builtin"]),
                "retries": policy.get("retries", 1),
                "retry_delay_s": policy.get("retry_delay_s", 0.25),
                "model": policy.get("model", ""),
            }
            wrapped.append(
                ProviderBackedAgent(
                    base_agent, self.registry,
                    AgentPolicy(**cfg)
                )
            )
        # Agents not explicitly overridden still use their configured/default agent.
        wrapped_names = {a.name for a in wrapped}
        wrapped.extend(a for a in original if a.name not in wrapped_names)
        old = self.agents
        self.agents = wrapped
        try:
            return self._run_agents(context, use_cache)
        finally:
            self.agents = old
