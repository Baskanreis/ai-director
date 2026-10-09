# v2.101.7 — Release Hygiene + E2E Verification

- Removed empty `app/export/test_delivery_matrix.py` orphan; canonical test remains in `app/tests/test_delivery_matrix.py`.
- Removed all `__pycache__`/`.pyc` build artifacts from the release source package.
- Removed duplicate `opencv-python-headless` optional dependency declaration.
- Updated README roadmap status for completed Smart Reframe / Shorts Factory / Creator Assistant.
- Verified API audit and packaging preflight.
- Verified 89 critical regression tests and 122 export/AI/subtitle/Shorts/pipeline tests.
- Verified real FFmpeg pipeline E2E media rendering tests.

# v2.101.6 — Release Gap Completion

- Fixed Shorts Factory and Smart Reframe sidebar routes.
- Added standalone Smart Reframe 9:16 render flow.
- Added per-user YouTube runtime configuration in Connection Center.
- Removed unused empty roadmap stub packages; app.render bridges to app.export.
- Added .env.example, LICENSE, pytest.ini and release-gap regression tests.

# v2.101.6 — Unified Subtitle Render Layer

- Unified ASS/SRT subtitle layer is now part of the real FFmpeg export filtergraph.
- AI Pipeline subtitle stage prepares a styled ASS layer for the render stage.
- Added subtitle export contract/regression tests and real FFmpeg E2E validation.

## v2.101.4 — Runtime API Audit Fixes

- Fixed `installer/api_contract_audit.py` standalone `importlib.util` dependency.
- Extended API audit to detect project-local absolute imports such as `proxy.*` and
  resolve relative imports correctly.
- Fixed remaining `app/proxy` test imports using the non-canonical `proxy.*` namespace.
- Added clean-process API audit regression tests.
- Updated OpenAI cloud provider default from stale `gpt-5.6` to `gpt-5.6-sol`.
- Hardened POSIX YouTube OAuth token permissions to `0600`.
- Documented optional `psutil` dependency.
- Reconciled README/ROADMAP with the current Windows-first single-Setup distribution strategy.

# Changelog

## 2.101.3 — Runtime API Contract Hardening
- Added a pre-freeze API contract audit for every `app.*` module/symbol import.
- Packaging preflight now fails before PyInstaller if a lazy-loaded feature has a broken module or symbol reference.
- Qt-dependent modules are explicitly deferred when PySide6 is unavailable in the build environment.
- Corrected the legacy YouTube production-queue test import to the current `app.youtube.*` namespace.

## v2.101.2 — AI Runtime Reliability

- Local Qwen3/llama.cpp is now the default final AI path; cloud providers remain optional.
- Whisper Base is enabled for speech analysis with deterministic fallback.
- AI self-test validates bundled Whisper/Qwen/llama runtime assets and detects truncated packages.
- Local model health rejects suspiciously small/truncated runtime files.

## v2.101.1 — Final Reliability Hotfix
- Synchronized application/installer/release version to 2.101.1.
- Hardened frozen FFmpeg/FFprobe runtime path resolution for Windows onedir installs.
- Hardened Whisper model loading to support both official openai-whisper and reduced provider/mock signatures.
- Final validation: 122 non-Qt tests passed, 3 skipped; runtime self-test 17/17.

## v2.101.0 — Reliability + Professional UI
- Added full runtime self-test for critical modules, FFmpeg/FFprobe and real encode/probe roundtrip.
- Added safe lazy-page loading so a broken optional feature no longer terminates the whole application.
- Bundled full Windows FFmpeg + FFprobe runtime during Setup build and prepend it to runtime PATH.
- Added build-time VERSION ↔ Inno Setup version consistency gate.
- Refreshed the main UI with a professional dark workspace, top project bar, health indicator and KPI dashboard.

## v2.97.0 — Hardware Acceleration Detection & Renderer Selection

Best-effort GPU vendor/FFmpeg capability detection, safe preview/render backend selection, and PreviewPlayer telemetry accessors. CPU fallback remains authoritative when hardware capability cannot be proven.

## v2.96 — Playback Runtime Integration
- Connected measured preview timer cadence to the PlaybackPerformanceGovernor through a Qt-independent runtime bridge.
- PreviewPlayer now emits playback performance decisions and exposes optional scheduler hooks.
- ProxyGenerationService can pause new background proxy jobs and boost queued proxy priority under playback pressure.
- Dropped-frame pressure now decays during healthy playback, allowing controlled governor recovery.
- Added runtime bridge and worker integration regression tests.

## 2.95.0
- Added Playback Performance Governor for responsive interactive playback.

## v2.94.0 — Predictive Proxy Warmup
- Added playhead-motion-aware proxy warmup prediction.
- Prefetches active and near-future clips according to playback direction and speed.
- Reverse playback receives symmetric warmup support.
- Warmup skips media already present in cache or ready proxy state.
- Proxy queue deduplicates active jobs by media ID.
## v2.92.0 — Proxy Cache Intelligence + LRU

- Added bounded disk proxy cache with LRU eviction and timeline protection.
- Added cache reconciliation, persistence, access tracking, pin/protect controls, and automatic quota cleanup.
- Integrated playback access tracking and proxy-worker completion registration.
- Proxy cache never evicts pinned or protected media during cleanup.

# v2.90 — Real FFmpeg Smart Proxy Worker

- Added a real FFmpeg-backed proxy worker with shell-free process execution.
- Added atomic temporary-output handling so failed/cancelled encodes never become valid-looking proxies.
- Added progress parsing from FFmpeg `out_time_ms`, cancellation, error capture and output validation.
- Added bounded `ProxyGenerationService` for background queue execution, priority ordering, cancellation and scheduler admission.
- Preserved the single-Setup distribution contract and existing adaptive/predictive render scheduling.

## 2.69.0 — Timeline Creative Asset Inspector
- Live timeline asset inspector with recipe controls, Similar and Replace.
- Single-session undo/redo transaction semantics.
- Non-destructive `asset://` workflow preserved.

## 2.68.0 — Smart Drag & Drop
- Added non-destructive Smart Drag & Drop ghost preview from Creative Library to Timeline.
- Added live drop target/time/duration feedback while dragging a 50K asset.
- Ghost preview never mutates the timeline until the drop is committed.
- Existing AssetTimelineBridge/creative pass remains the single commit path.
- Preserved single-file Windows release contract: `AI_Director_Setup.exe`.

# v2.67.0 — Asset Browser ↔ Timeline Bridge

- Added non-destructive `AssetTimelineBridge` for direct Browser → Timeline actions.
- Added **Klibe Uygula**, **Timeline’a Ekle**, and **Varyasyon Oluştur** actions to Creative Library.
- Effect/filter/overlay/motion/transition assets are stored as timeline asset stacks; text/subtitle assets become creative text cues; audio assets become resolver-ready audio cues.
- Procedural/marketplace inserts use `asset://...` references, avoiding 50K duplicated media files.
- Added deterministic variation seeds for lightweight, repeatable asset variations.
- Existing 50K visual similarity, category filters, micro-previews, Pack Director and Single Setup distribution remain intact.

## 2.64.0 — Autonomous Edit Pass
- Added a unified **Autonomous Edit Controller** combining scene creative planning, Marketplace Pack Director and the existing Autonomous Revision engine.
- Added deterministic scene-by-scene decisions for primary/secondary Marketplace packs, creative intensity and timeline asset cues.
- Added safe revision orchestration with the existing preview/QC evaluator; no second AI model is loaded.
- Autonomous repairs never add new heavy effects and never intentionally regress a previously accepted candidate.
- Added structural tests for pack-first planning, secondary-pack safety and non-regressive revision.
- Preserved the one-Setup GitHub release contract: users install no separate runtime or dependency package.

## 2.62.0
- Added AI Marketplace Pack Director: scene-first pack selection with coherent effect/motion/text/SFX/audio choices.
- Scene Creative Director now records primary/secondary pack decisions and mix weight.
- Preserved single-Setup distribution contract; no user-side dependency installation.

## 2.61.0 — Asset Marketplace / Single Setup

- Added built-in AI Asset Marketplace / Pack Engine for the 50K creative catalog.
- Added curated packs for Creator, Cinematic, Shorts, Gaming, Podcast, Beauty/Fashion, Travel B-roll, Education, Meme/Social, Subtitle styles, LUT/Filter and Sound FX.
- Added Pack filtering/export to Creative Library.
- Added pack aliases for B-roll, subtitle-style and LUT workflows.
- Preserved metadata-first/original licensing boundary; no proprietary third-party asset files are bundled.
- Hardened Windows build distribution contract: GitHub release output is exactly one `AI_Director_Setup.exe`.
- Version synchronized to 2.61.0.

## 2.59.0 — Shared Multimodal Scene Context
- Added one shared timestamped SceneContext for Vision/Speech/Rhythm/Creative agents.
- Added scene-aware semantic asset matching from shared context.
- Kept the default path CPU-light and single-model friendly.

# AI Director Changelog

## 2.56.0
- Regional hotspot revision engine with non-destructive candidates.
- Hotspot-scoped B-roll, reframe, pattern-break and pacing alternatives.
- Reuses the existing preview/QC evaluator; no extra model process.
- Orchestrator regional_revision API.


## 2.51.0 — Channel Brain
- Fused public YouTube DNA, first-party Analytics, learning hints and optional owned edit evidence.
- Added deterministic Channel Brain soft targets and guardrails for Final Director.
- Preserved single-model synthesis / low-CPU architecture.
# v2.50.0 — YouTube Intelligence

- Added public YouTube Channel ID ingestion and Channel DNA.
- Added first-party YouTube Analytics OAuth with local AppData token storage.
- Added YouTube Intelligence UI under the YouTube menu.
- Stored Channel DNA is automatically injected into Multi-Agent/Final Director context.
- Added build-time GitHub secret injection so end users never manage API/OAuth config files.
- Preserved single `AI_Director_Setup.exe` release contract.

# 2.49.0

- Collaborative multi-agent blackboard with dependency phases.
- Single Final Director synthesis stage; no model-per-agent requirement.
- Local SQLite learning memory for user ratings, QC and real platform outcomes.
- Learning hints are fed into future decisions without uncontrolled self-retraining.
- Conservative provider default: real model calls disabled unless explicitly enabled.
- One final model can be enabled without spawning nine local model processes.

## v2.44 — Automatic Timeline Director
- Added a deterministic Auto Timeline Director that combines scene-aware creative stacks, transitions, beat timing and persistent clip metadata into one non-destructive timeline plan.
- Added one-click **AI Auto Timeline** to Studio with style and BPM selection.
- Automatic transitions now vary by edit style while preserving the Creative Library asset kind.
- Beat timestamps, scene IDs, style and variant are persisted on clips for preview/export consumers.
- Existing source media, source ranges and clip timing remain untouched by the creative pass.
- Preserved the Windows distribution contract: GitHub artifact/release contains only `AI_Director_Setup.exe`.

## v2.42 — Context-Aware Creative Director
- Added context-aware Creative Library ranking using scene, energy, speech, music, face, platform and style signals.
- Added non-destructive preview plans and deterministic creative variations.
- Added one-click AI clip recipe flow in Creative Library Studio.
- Transition application now respects the selected Creative Library transition kind.
- Preserved the one-Setup GitHub distribution contract.

## v2.40 — Creative Library Studio
- Added a searchable Creative Library Studio UI backed by the full 1,000-item catalog.
- Added category filtering, tag/name search, favorites and parameter/licensing inspection.
- Added one-click application for effect, motion, transition and text assets to the selected timeline clip.
- Unsupported asset types remain available to AI Composer instead of being incorrectly coerced into effects.
- Library UI keeps large catalogs responsive by limiting search results and avoiding media rendering work.
- Preserved the one-file Windows distribution contract: GitHub artifact/release contains only `AI_Director_Setup.exe`.

## v2.39 — 1,000-Item Creative Library
- Expanded the original parameterized Creative Library from 289 to exactly 1,000 creative definitions.
- Added music recipe assets alongside effects, transitions, motion, text, overlays, stickers, SFX, audio FX, filters and templates.
- Added deterministic Pro variants with stable IDs and reusable parameters for Composer/Agent selection.
- Added a one-time weighted search index for faster 1,000-item library search.
- Normalized legacy duplicate IDs so all 1,000 assets are uniquely addressable by favorites, cache and Composer.
- Added regression coverage for exact count, unique IDs, category coverage and large-library search.
- Assets remain original metadata/preset definitions; proprietary CapCut/Premiere media is not bundled.


## v2.36 — Agent Model Isolation & Runtime Health

- Her agent artık aynı provider altında bile bağımsız model seçebilir.
- Agent model seçimi cache fingerprint'ine dahil edildi.
- Provider Studio'ya agent bazında model ve fallback düzenleme eklendi.
- Yerel Whisper/llama.cpp/command provider'ları agent model override'ını destekliyor.
- Provider/runtime health kontrol katmanı eklendi.
- Windows dağıtım sözleşmesi korunuyor: GitHub artifact/release yalnızca `AI_Director_Setup.exe`.
# Changelog

## v2.34.0 — Multi-Agent Director
- Added 9 specialist agents: Vision, Speech, Caption, Rhythm, Creative, Platform, Quality, Scene and Copy.
- Added parallel agent execution outside the UI thread.
- Added persistent per-agent cache keyed by deterministic context fingerprints.
- Added Final Compiler that produces one `CompiledEditPlan` for the renderer.
- Added Multi-Agent Director button to AI Editor.
- Rendering remains separate from analysis to reduce UI freezes and duplicated work.

# Changelog

## v2.31.0 — AI Visual QC
- Added sampled-frame visual QC after every successful delivery render.
- Detects decode failures, near-black frame clusters, frozen-frame patterns and excessive blur as conservative delivery warnings/failures.
- Added FFmpeg `volumedetect` peak analysis to flag obvious clipping risk.
- Integrated visual/audio QC into `ExportWorker` without modifying the source timeline.
- Hard visual failures block delivery; creative warnings remain visible without destroying a usable export.
- Kept v2.30 automatic delivery repair for resolution/audio/duration defects.

# Changelog

## v2.30.0
- Added automatic second-pass delivery repair after export QC.
- Repairs wrong resolution, missing audio, and bounded duration mismatches without touching the source timeline.
- Re-validates repaired output with the normal QC gate before marking export successful.
- Uses atomic temporary output replacement to avoid corrupting a valid export.
- Added delivery repair regression coverage.

- Post-render FFprobe kalite kontrolü: dosya, video/audio stream, çözünürlük, süre ve container doğrulaması.
- ExportWorker final dosyayı kullanıcıya teslim etmeden önce QC çalıştırıyor.
- QC raporu puan ve fail/warning kayıtları üretiyor.

AI Director v2.30 — AI Export Quality Control

# AI Director v2.25

## Creative Pass Render Bridge

- Added `app.ai.creative_apply` to apply AI Creative Pass decisions directly to the timeline.
- Visual effect decisions now become animated `effect:*` keyframes and are rendered by the existing FFmpeg export engine.
- Punch/impact motion decisions now become scale/position keyframes and are rendered by the existing transform pipeline.
- Transition decisions are applied as non-destructive timeline transitions.
- Text animation cues are stored on clips and persist through project save/load for the subtitle/text renderer.
- Added **7) Creative Pass Uygula** to the AI Editor dialog.
- Added regression tests for Creative Pass application and project round-tripping.
- Source media remains untouched; the pass only modifies project timeline metadata.

# AI Director v2.26

## Typography & Creative Library Expansion
- Added shared `app.subtitle.typography` catalog with 8 short-form typography presets.
- Expanded subtitle animations: slide-left, bounce, typewriter, glitch, neon pulse, highlight sweep, shake and zoom.
- Added Bold Hook, Kinetic Bounce, Glitch Caption, Neon Pulse, Typewriter and Highlight Sweep subtitle styles.
- Shorts Remix renderer now uses the shared ASS typography engine instead of a fixed caption style.
- Added a caption-style selector to AI Shorts Director; selected style is passed through the render worker.
- Added new original text animation presets including Shake Word, Zoom Word, Marker Sweep, Split Reveal and Counter Roll.
- Added regression coverage for typography catalog/search and ASS animation rendering.

# AI Director v2.28

## Mega Creative Library + Rhythm Engine
- Expanded the original Creative Library with 120+ parameterized effect, transition, motion, text, overlay, filter and audio-processing assets.
- Added original short-form typography packs: karaoke, quote, creator tag, counter, comic, retro, gradient, outline and shadow styles.
- Added transition families: slides, pushes, doorway, circle reveals, pixelize, morph, RGB split, strobe, lens flash and digital wipe.
- Added motion families: soft/fast zooms, reveal zoom, drift, tilt, handheld, impact zoom, rubber-band, bounce, elastic, swing, float and jitter.
- Added overlays/textures: dust, bokeh, rain, snow, confetti, hearts, sparkles, scanlines, vignettes, paper and halftone.
- Added original generated music loops for hype, hip-hop, house, pop, cinematic, chill, phonk, drill, fashion, travel, corporate and gaming use cases.
- Added original generated SFX for long whoosh, cinematic impact, short riser, glitch burst, soft pop, sparkle, swipe and hard impact.
- Added `app.audio.beat_sync` with beat grid, downbeats, nearest/floor/ceil quantisation, cut snapping and rhythm-plan generation.
- Creative assets remain metadata-first and user-importable; no proprietary CapCut/Premiere assets are bundled.

## v2.34 — Managed AI Runtime + Provider Studio

- Windows Setup now provisions the AI runtime automatically inside `Program Files\AI Director`.
- Whisper Base model is downloaded and SHA-256 verified during Setup.
- Qwen3 1.7B Q4_K_M is provisioned as the compact local agent LLM.
- llama.cpp is selected automatically: NVIDIA CUDA build when available, otherwise CPU build.
- Managed local LLM starts lazily only when an agent actually needs it.
- New **AI Provider Studio** UI lets each agent select its provider/model/retry policy independently.
- Mutable settings remain in LocalAppData; runtime binaries/models stay inside the installed application.
- Cloud providers remain optional; local agents work without API keys when the installer runtime download succeeds.

## v2.37 — Rich Edit Styles
- Added 15 declarative editorial styles: Cinematic, Viral Fast, Story Driven, Podcast, Talking Head, Educational, Documentary, Vlog, Gaming, Music Video, Product, News, Sports, Meme and Minimal.
- Director plans now carry an `edit_style` and full style recipe without breaking the existing plan contract.
- Creative Pass now adapts effect/motion/text/transition intensity and music selection to the chosen style.
- Added UI style selection alongside platform/profile selection.

## v2.38 — Mega Creative Library & Style Composer
- Expanded the original creative metadata library to 289 assets across 10 categories.
- Added large original catalogs for effects, transitions, motion, text, overlays, stickers, templates and more.
- Added weighted full-library search, category discovery, featured assets and library statistics.
- Added non-destructive hybrid style composer (e.g. Gaming + Meme, Cinematic + Documentary).
- Kept the library metadata-first: no proprietary CapCut/Premiere assets are bundled.
- Added regression tests for library coverage/search and style mixing.

## v2.41 - Creative Library Studio Flow
- Added reusable Creative Library Studio orchestration helpers.
- Added metadata preview specs for library assets.
- Added AI Top-3 creative recommendations.
- Added multi-select Creative Library stacking/apply support.
- Extended Creative Library UI with AI recommendations and stack apply actions.
- Preserved one-Setup-only GitHub distribution contract.

## v2.43 — Scene Creative Director
- Added deterministic scene-by-scene creative stack planning.
- Added per-scene asset diversity and context-aware scoring.
- Added alternate creative variants without randomness.
- Added flattening into the existing Creative Stack apply contract.
- Added Creative Library Studio action: AI Tüm Sahneleri Yönet.
- Preserved one-setup GitHub distribution policy.

## v2.46.0 — 10,000 Creative Library + Live Preview + Timeline Drop
- Creative Library expanded from 5,000 to exactly 10,000 unique original recipe assets.
- Procedural thumbnails remain lightweight and cache-friendly across all asset types.
- Added animated live preview with play/pause and frame scrubbing.
- Added delayed hover auto-preview for library cards.
- Added Creative Library → Timeline drag-and-drop with non-destructive application to the target clip.
- Creative Library window is modeless so the timeline can remain accessible while browsing assets.
- Windows release contract remains unchanged: GitHub release contains only `AI_Director_Setup.exe`.

## 2.48.0
- Professional creative search: up to 100,000 candidate stacks per scene.
- Diversity-aware ranking, retention/visual-density/audio QA scoring.
- Windows distribution contract: one Setup.exe; bundled Whisper, Qwen and llama.cpp runtime.
- Setup no longer runs a second runtime installer or requires extra files after installation.

## 2.52.0 — Reference Edit DNA
- Added low-cost local reference-video edit DNA analyzer.
- Added optional one-thread FFmpeg scene/silence analysis.
- Connected reference analysis to Channel Brain and Final Director context.
- Added deterministic reference analysis tests.
- Preserved Single Setup / zero extra runtime installation design.

## 2.53.0 — Autonomous Revision Engine
- Added model-free v1/v2/v3 autonomous revision controller.
- Reuses existing real-media preview and visual/audio QC callbacks.
- Diagnoses integrity, audio peak, blur and duration issues and applies targeted safe repairs.
- Never accepts a regression; stops early when QC is clean or improvement is insufficient.
- Connected revision scoring to Channel Brain without loading another AI model.
- Preserved low-CPU single-model synthesis and Single Setup distribution.

## 2.54.0
- Added CPU-light Retention Predictor with confidence/evidence separation.
- Connected Retention Predictor to Autonomous Revision scoring.
- Owned YouTube Analytics can calibrate channel-level retention baselines.
- Added actionable retention hotspots without loading another AI model.

## v2.60.0 — 50,000 Creative Studio + Shared Vision
- Expanded the original procedural creative catalog to exactly **50,000** searchable recipes.
- Balanced catalog coverage across effects, transitions, motion, typography, overlays, stickers, SFX, audio FX, filters, templates and music.
- Added a common semantic recipe contract: intent, mood, style family, target format, semantic tags and safe-to-auto-apply metadata.
- Added optional **Shared Vision Enricher**: representative frames are extracted once and sent in one multimodal batch to the configured vision provider.
- Shared Vision can return objects, people/faces, screen/UI, product, environment, shot type, OCR, visual cues and confidence.
- Semantic Asset Matcher now consumes those visual fields together with transcript and scene energy.
- Final Director now receives the shared multimodal scene summary, reducing specialist contradictions.
- No proprietary CapCut assets are copied; the 50K library is original/procedural and compatible with licensed user packs.
- Preserved the one-Setup distribution architecture and CPU/RAM guardrail: no model per scene.

## v2.66.0 — Smart Asset Discovery
- Added 50K category counts and compact category metadata.
- Added advanced intent/mood/style/safety/favorites filters.
- Added natural-language visual/semantic discovery and "Şuna Benzer" similarity mode.
- Kept previews lazy/cached; no 50K animation files are bundled.

## v2.66 — Visual Similarity Discovery
- Added lightweight visual-character signatures for the 50K asset browser.
- “Şuna Benzer” now blends visual preview character with semantic metadata similarity.
- Visual signatures cover motion, scale, rotation, blur, glow, contrast, saturation,
  sharpness, energy, rhythm, complexity, softness, warmth and density.
- No second AI model and no 50K GIF/MP4 payloads are introduced; signatures are computed
  from asset recipes and cached/lazily evaluated.
- Existing structured filters, categories, packs and Single Setup distribution remain intact.

## v2.73.0 — Final Polish + Human Control
- Added non-destructive AI suggestion layer with Accept/Reject/Modify decisions.
- Added per-suggestion confidence and quality-improvement gates.
- Added project-local preference learning from user decisions.
- Added snapshot-based undo for the last human decision.
- Locked timeline targets cannot be modified by AI suggestions.
- Preserved single-Setup distribution architecture.

## 2.75.0 — v2.70–v2.72 integration
- v2.70 Asset Keyframe Animation: intensity/speed/blend/position/duration keyframes on metadata-only creative assets.
- v2.71 Beat-Synced Animation Director: intensity ceiling, cooldown, minimum beat distance and manual-keyframe protection.
- v2.72 Unified AI Auto-Rhythm: one deterministic rhythm map for cuts, transitions, zoom/pan, asset animation, subtitle emphasis and SFX.
- Added Qt-free controllers and regression tests; no additional runtime dependency.

## v2.76.0 — AI Director Control Center + Unified Final QC
- Added non-destructive Control Center with review/accept/reject/auto-high-confidence modes.
- Added bounded per-domain automatic revision planning.
- Added preference-aware suggestion ranking with project-local history.
- Added unified five-domain Final QC with explicit missing-domain failures.

## v2.77.0 — Preview/QC Dashboard + Targeted AI Revision Loop
- Added a Qt-free Preview/QC Dashboard state model with before/after domain deltas and preview markers.
- Added targeted AI revision loop: only failed QC domains are retried, with per-domain isolation and non-regression acceptance.
- Revision attempts are bounded and never compound a rejected candidate.
- Added deterministic regression tests for dashboard deltas and selective revision.
- Preserved v2.70–v2.72 keyframe, beat-animation and unified auto-rhythm systems.
- Preserved Single Setup distribution contract.


## v2.78 — YouTube Creator Studio
- YouTube URL parser for video, Shorts, channel and @handle references.
- Creator Package: title variants, description starter, tag set, chapters, thumbnail briefs.
- SEO scoring with actionable title/description/tag suggestions.
- Creator workflow exposed in YouTube Intelligence dialog.
- Existing Data API, Channel DNA and first-party Analytics integration preserved.
- No video downloading/scraping dependency added.

## v2.79.0 — YouTube Auto-Publish Studio
- Added first-party YouTube publish planning and pre-upload QC.
- Added resumable YouTube Data API video upload through OAuth `youtube.upload` scope.
- Added scheduled publishing validation, privacy-state validation and metadata limits.
- Added optional thumbnail upload after successful video creation.
- Added upload progress callback and deterministic injected uploader for tests.
- Reused the existing YouTube Analytics token store; no separate user-side runtime is required.
- No scraping/downloader dependency was introduced.

## v2.85.0
- Added GPU/CPU-aware RenderAdmission scheduler.
- Added bounded parallel render admission with editor-safe CPU/GPU thresholds.
- Integrated scheduler into YouTube ProductionQueue render stage.
- Unknown GPU telemetry remains non-blocking for compatibility.

## 2.86.0 — Adaptive Render Scheduler
- Added adaptive job priorities for preview, thumbnail, short and long renders.
- Production Queue uses scheduler priority when available.
- Existing CPU/GPU admission limits remain authoritative.

## v2.88 — Predictive Render Scheduler
- Feature-aware ETA using duration, resolution, FPS, codec, effects and proxy state.
- Conservative fallback when history is insufficient.
- Production Queue records render features for future estimates.
- Hard CPU/GPU/VRAM admission limits remain authoritative.

## v2.89.0
- Smart Proxy Intelligence with conservative media scoring.
- Proxy generation queue with priority, persistence and cancellation.
- Designed to cooperate with Adaptive/Predictive Render Scheduler resource gates.

## v2.91.0 — Playhead-Aware Proxy Auto-Switch
- Added deterministic playhead proximity ranking for proxy jobs.
- Active playhead clip gets highest proxy priority; near-future clips are prefetched next.
- Added non-destructive ProxyAutoSwitch playback resolution: timeline data is never rewritten.
- Proxy generation service now supports completion callbacks for automatic asset registration/UI refresh.

## v2.93.0
- Added Smart Proxy Profile Selection: adaptive 360/540/720/1080-class proxy sizing from source metadata and live CPU/GPU/VRAM/timeline/storage pressure.
- Added per-job proxy metadata persistence and explicit profile override support.
- Integrated profile selection into the real FFmpeg proxy worker.

## v2.99.0 — YouTube Runtime & Packaging Hardening
- Explicitly bundle all lazy-loaded YouTube modules in the Windows frozen build.
- Extend packaging preflight to import-check YouTube Data API, OAuth, publish, Studio and production modules.
- Add YouTube runtime health diagnostics for Data API/OAuth/package configuration.
- Surface YouTube configuration/module failures in the UI instead of silently disabling the Production Manager.
- Refresh the Production Manager queue on dialog creation.


## v2.100.0 — YouTube Connection Center & Queue Hardening
- Added YouTube Connection Center for Data API, Google OAuth, token and module status.
- Added explicit YouTube configuration diagnostics instead of ambiguous disabled controls.
- Added safe existing-output upload path for Production Queue; missing renderer/output now fails explicitly.
- Added packaging/preflight coverage for the new YouTube connection UI.
