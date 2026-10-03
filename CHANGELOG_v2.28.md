# AI Director v2.28

- Fixed `app.export.command_builder` ↔ `app.render` circular import using lazy render package exports.
- Added model-agnostic content understanding with segment-level hook/payoff/information/suspense/comedy/action/B-roll signals.
- Added explainable Edit Decision Graph with protected semantic ranges.
- Added pre-render graph quality gates for invalid ranges, protected-content conflicts and effect spam.
- Expanded creator preference learning with dimension biases and reference profiles.
- Added explicit feedback learning loop for style/action acceptance.
- Added 36+ composable editorial styles and content-aware recommendations.
- Integrated content understanding, decision graph and quality report into `ProfessionalEditPlan`.
- Preserved Qt `QVideoFrame -> QVideoSink` GPU telemetry path and CPU-map avoidance from v2.27.
