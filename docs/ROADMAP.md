# Roadmap update

- **v1.8:** Reference Video Analyzer + Channel DNA bridge — implemented.
- **v1.9:** Channel Intelligence workflow, multi-reference aggregation, title-pattern analysis, normalized ingestion records, and persistent style profiles — implemented.
- **v2.0:** Autonomous edit pass + retention-aware QA — implemented.
- **v2.1:** Live YouTube Analytics connector + empirical retention calibration — planned.

# Yol Haritası

| Sürüm | Hedef | Durum |
|-------|-------|-------|
| v0.1 Alpha | Proje yapısı, PySide6 başlangıcı, ilk pencere, temel yapı | Tamamlandı |
| v0.2 Alpha | Timeline iskeleti, video yükleme, proje aç/kaydet | Tamamlandı |
| v0.3 Alpha | FFmpeg entegrasyonu, ilk export | Tamamlandı |
| v0.4 Alpha | Basic Timeline (move/trim/snap/zoom/playhead/timecode) | Tamamlandı |
| v0.5 Alpha | Video Preview (play/pause/seek/frame step/volume/fullscreen, timeline senk.) | Tamamlandı |
| v0.6 Alpha | Real FFmpeg Engine (filtergraph, audio mixing, H.264/H.265/AV1, gerçek ilerleme/iptal) | Tamamlandı |
| v0.7 Alpha | Audio Engine (kazanç/fade/mute, müzik/seslendirme izleri, normalizasyon, ducking, waveform) | Tamamlandı |
| v0.8 Alpha | AI Subtitle (Whisper, kelime zamanlama, cümle segmentasyonu, SRT/VTT, gömme — TR öncelikli, EN/DE/FR) | Tamamlandı |
| **v1.0 Beta** | **Scene Detection (ffmpeg tabanlı sahne tespiti + otomatik bölme) — ilk gerçek kullanılabilir beta** | **Tamamlandı** |
| v1.1 | Basic Editing Engine (speed/reverse/freeze/crop/rotate/keyframe) + gerçek FFmpeg render + Audio Engine | Tamamlandı |
| v1.2 | Subtitle Studio (düzenleme + stil/animasyon/kelime vurgusu/emoji) + AI Basic Editor (sessizlik/tekrar/dolgu kelime analizi, kabul/ret, otomatik kesim) | Tamamlandı |
| **v1.3** | **Non-Destructive Editing: Sürüm Geçmişi (kalıcı, isimli kontrol noktaları) + Otomatik Kayıt (autosave) + Çökme Sonrası Kurtarma (crash recovery)** | **Tamamlandı** |
| v1.4+ | Smart Reframe (yüz/nesne takibi, otomatik 9:16 kırpma) | Planlandı |
| v1.4+ | Shorts Factory (uzun videodan otomatik Shorts) | Planlandı |
| v1.4+ | Creator Assistant (doğal dil komutları) | Planlandı |


## v2.2 delivered
- Effects & Music Library with visual presets, SFX, music loops, and audio-only timeline insertion.
- Future licensed content packs can use the same asset metadata contract.

## v2.18 delivered — Autonomous Professional Director
- Platform-aware autonomous edit planning for YouTube, Shorts, TikTok and Instagram Reels.
- Semantic cut safety gates layered on top of the existing Director engine.
- Reviewable machine-readable edit plans (`AutonomousEditPlan`) without destructive timeline mutation.
- Long-video performance recommendations: proxy media, background analysis and cached render.
- Quality gates for cut ratio, narrative, hook, decision risk and platform duration.
