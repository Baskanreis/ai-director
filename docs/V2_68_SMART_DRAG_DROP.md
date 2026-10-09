# v2.68 Smart Drag & Drop

Creative Library assets can be dragged directly onto a timeline clip. While dragging, the timeline renders a lightweight ghost preview showing the intended start/duration and target clip.

The ghost is UI-only and non-destructive. No timeline model mutation occurs during drag/hover. On drop, the existing creative pass / AssetTimelineBridge path commits the asset recipe.

The drag payload remains `application/x-ai-director-creative` and carries only the asset id, so 50K catalog assets do not get copied into the timeline or duplicated as media files.

Windows/GitHub distribution remains exactly one `AI_Director_Setup.exe`.
