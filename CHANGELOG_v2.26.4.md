# AI Director v2.26.4 — Media Performance & Parallel Render

## Added
- Background proxy generation layer with content-addressed cache.
- Cached waveform extraction with viewport-aware decimation.
- Beat visualization model with marker/nearest-beat helpers.
- FFmpeg transition preview thumbnail cache.
- GPU-aware parallel batch renderer with per-device concurrency limits and CPU fallback.
- Fast performance unit tests and FFmpeg smoke coverage.

## Performance safeguards
- Heavy media work stays outside the UI thread.
- Proxy generation is opportunistic and should not compete with active playback.
- Waveform data is cached and decimated to display resolution.
- Parallel render concurrency is explicitly bounded instead of spawning an unbounded number of FFmpeg processes.

## Validation
- New media/performance unit tests: 4/4 passed.
- Python compileall: passed.
- FFmpeg smoke: proxy + 3 thumbnails + waveform cache + beat analysis passed.
- Full legacy export suite was not used as a release gate because the sandbox imposes a short execution timeout on long FFmpeg suites.

## v2.26.6 - Realtime Preview Engine

- Added Qt-light `PreviewEngine` for stateful timeline/media resolution.
- Added adjacent-clip proxy prefetch without blocking playback.
- Added coalesced timeline seek handling; rapid scrub events collapse to the latest seek.
- Kept expensive FFmpeg/proxy work outside the UI thread.
- Preserved existing proxy, waveform, beat, transition-thumbnail and adaptive-quality layers.

## v2.27 — Context-Aware AI Editorial Engine
- `app/ai/editorial_style_engine.py` eklendi.
- 22 içerik türü için ayrı editoryal reçeteler eklendi.
- Eğitim, eğlence, korku vb. içeriklerde pacing, motion, caption, sound, B-roll ve silence davranışı içerik türüne göre değişiyor.
- `build_professional_edit_plan()` artık içerik metni/başlık/etiket ve istenen stil alabiliyor.
- Stil seçimi gerçek motion/caption/sound kararlarına bağlandı.
- Açıklanabilir kalite kuralları ve gelecekteki AI/LLM sinyal entegrasyonu için sözleşme eklendi.
