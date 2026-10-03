# AI Director v2.28 — Editorial Intelligence

## Pipeline

`Transcript / Scene / Audio / Vision signals -> Content Understanding -> Content/Platform/Creator Style -> Edit Decision Graph -> Quality Gates -> Timeline/Render`

The system is deliberately model-agnostic. A future vision model, local LLM, Whisper variant, beat detector or multimodal model can populate the same bounded signals.

## Content-aware behavior

The Director distinguishes educational, tutorial, entertainment, comedy, horror, documentary, cinematic, gaming, vlog, podcast, news, review, storytelling, motivational, music, sports, travel, product, wedding, social and automotive intent. Each recipe controls pacing, shot length, motion, captions, sound, silence and B-roll behavior.

## Style catalog

The v2.28 catalog contains 36+ composable styles including Clean Pro, Minimal Cinematic, Dynamic Social, Hyper Cut, Comedy Timing, Horror Suspense, Found Footage, Documentary, Investigative, Educator, Masterclass, Podcast Clean/Dynamic, Story Arc, Emotional Story, Motivational Rise, Gaming Reactive/Cinematic, Sports Highlight/Analysis, Travel Immersive/Fast, Product Clean/Premium, Review Trust/Hype, News Broadcast/Social, Music Beat/Cinematic, Wedding Elegant, Auto Action/Premium, Retro, Documentary Raw, Creator Authentic and Viral Hook.

## Learning

Creator feedback is explicit and reversible. Accepted/rejected style or action feedback changes bounded preference weights and dimension biases; content semantics still have priority.

## Quality

Before render, the decision graph checks duration/ranges, protected information, action density and effect spam. The render path should simplify or flag questionable actions rather than silently applying every available effect.
