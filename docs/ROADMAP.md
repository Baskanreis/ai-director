# AI Director Roadmap — v2.101.7

Bu dosya yalnızca **henüz teslim edilmemiş** işleri listeler. Teslim edilmiş özelliklerin
tarihçesi için `CHANGELOG.md` tek doğruluk kaynağıdır.

## v2.101.7 itibarıyla teslim edilen ana katmanlar

- Proje / autosave / crash recovery / persistent versioning
- Gerçek FFmpeg export ve export QC
- Audio engine, waveform ve audio ducking altyapısı
- Whisper tabanlı subtitle/transcription zinciri
- Scene detection ve worker altyapısı
- Smart Reframe / Shorts / Remix
- 50K metadata-first Creative Library / Asset Marketplace
- AI Timeline Director, beat sync ve multi-pass AI Director
- Final QC / human control / transactional revision
- Proxy worker, cache, warmup ve playback performance governor
- GPU-aware/adaptive/predictive render scheduling
- YouTube Creator Studio, OAuth, production queue ve upload pipeline
- Windows single-Setup packaging ve Runtime API Contract Audit
- Runtime self-test ve packaging preflight

## Sonraki üretim hedefleri

| Öncelik | Hedef | Kabul ölçütü |
|---|---|---|
| P0 | Windows Qt smoke test | Kurulu Setup sonrası tüm ana sayfalar/dialoglar açılır |
| P0 | Gerçek medya E2E export | Video + ses + subtitle tek uçtan uca render edilir |
| P0 | AI E2E zinciri | Whisper → AI Director → timeline apply → render |
| P1 | GPU render doğrulaması | Desteklenen GPU'da hızlandırma, yoksa CPU fallback |
| P1 | 50K gerçek preview paketi | Metadata kaydı ile gerçek/eklenebilir medya paketleri eşleşir |
| P1 | YouTube production E2E | OAuth → queue → upload → QC → status |
| P2 | Linux/macOS packaging | Ayrı native paketleme ve CI hatları |
