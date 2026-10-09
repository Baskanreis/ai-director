# v2.76 — AI Director Control Center

The Control Center is a non-destructive orchestration layer for the Story,
Rhythm, Visual, Audio and Subtitle specialist passes.

Modes:
- Review one-by-one
- Accept all
- Reject all
- Auto-apply high confidence

Suggestions are filtered by confidence and predicted gain, ranked with
project-local preference signals, and recorded transactionally by the host.
Automatic revision requests are bounded to one revision per domain by default.

Final QC aggregates all five domains and treats missing domain results as
`missing`, never as an implicit pass.
