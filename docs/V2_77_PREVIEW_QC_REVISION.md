# v2.77 — Preview/QC Dashboard + Targeted AI Revision Loop

The dashboard is a Qt-free state model intended for the editor UI. It exposes:
- final score/status
- per-domain before/after delta
- failed domains
- preview markers
- revision events

The revision loop evaluates the current plan, selects only one failed domain at a time,
asks the caller for a safe repair, re-evaluates it, and accepts it only when that domain
improves by the configured minimum. Rejected candidates are discarded, so later revisions
cannot inherit a regression.

No extra AI model or runtime dependency is introduced.
