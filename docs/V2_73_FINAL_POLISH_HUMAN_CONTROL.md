# v2.73 — Final Polish + Human Control

Adds a non-destructive AI suggestion layer after autonomous editing.

## Rules
- AI proposes; it does not mutate the timeline while generating suggestions.
- Each suggestion has confidence, before/after payloads and a quality improvement score.
- Users can **Accept**, **Reject**, or **Modify** each suggestion.
- Every decision creates a snapshot, enabling local undo of the last decision.
- Locked timeline targets are protected.
- Learning is project-local: accept/reject counts influence only the current `PreferenceProfile`.
- No second AI model is loaded by this layer.

## Quality gate
Suggestions are discarded when confidence is below the configured threshold or the
predicted quality improvement is below the configured minimum.

## Integration
`FinalPolishSession` accepts the existing autonomous edit plan and can be called after
Autonomous Edit/QC. A UI can bind the three decisions directly to the session API.
