"""Low-cost final director: one synthesis decision after specialist work.

It can use one configured model call; otherwise a deterministic consensus compiler
is used. No specialist model is loaded for this stage.
"""
from __future__ import annotations
from typing import Any
from .contracts import AgentResult

class FinalDirector:
    name = "final_director"
    version = "1.0"

    def synthesize(self, results: dict[str, AgentResult], context: dict[str, Any],
                   provider=None) -> AgentResult:
        if provider is not None:
            try:
                prompt = self._prompt(results, context)
                data = provider.generate(
                    agent=self.name,
                    system=("You are the final AI video director. Reconcile specialist evidence, "
                            "respect hard constraints, remove contradictions, and output only JSON."),
                    prompt=prompt, context=context,
                )
                if not data.get("fallback"):
                    return AgentResult(self.name, self.version, "ok",
                                       float(data.pop("confidence", .9)), data)
            except Exception as exc:
                warning = f"Final AI fallback: {exc}"
        else:
            warning = "Final AI provider disabled; deterministic consensus used."
        return self._consensus(results, warning)

    def _prompt(self, results, context):
        import json
        evidence = {k: r.data for k,r in results.items() if r.status == "ok"}
        return json.dumps({"profile":context.get("profile","shorts"),
                           "events":context.get("plan_events",[]), "youtube_channel_dna":context.get("youtube_channel_dna",{}), "channel_brain":context.get("channel_brain",{}), "scene_context_summary":context.get("scene_context_summary",{}), "evidence":evidence,
                           "instruction":"Return decisions: approved_agents, conflicts, timeline_policy, asset_policy, qc_rules."},
                          ensure_ascii=False, default=str)

    def _consensus(self, results, warning):
        approved = [k for k,r in results.items() if r.status == "ok" and r.confidence >= .65]
        quality = results.get("quality")
        policy = {"max_simultaneous_heavy":2, "prefer_event_driven":True,
                  "preserve_speech_clarity":True, "avoid_repeated_transition":True}
        if quality and isinstance(quality.data, dict):
            policy["qc_rules"] = quality.data.get("checks", [])
        return AgentResult(self.name, self.version, "ok", .86,
                           {"approved_agents":approved, "conflicts":[], "timeline_policy":policy,
                            "asset_policy":{"selection":"contextual","diversity":.72},
                            "qc_rules":quality.data.get("checks",[]) if quality else []},
                           warnings=[warning])
