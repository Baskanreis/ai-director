# AI Director — v2.101.7

AI Director, PySide6 tabanlı profesyonel video düzenleme, AI-assisted editing, Shorts ve FFmpeg render uygulamasıdır.

> **Current release:** **2.101.7 — Release Hygiene + E2E**  
> **Dağıtım:** Windows birincil hedeftir. Production dağıtımı tek `AI_Director_Setup.exe` sözleşmesiyle yapılır.

## Proje durumu

| Alan | Durum |
|---|---|
| Sürüm | **2.101.7** |
| UI | PySide6 / Qt |
| Video | FFmpeg |
| Görüntü işleme | OpenCV headless |
| Konuşma analizi | Whisper Base |
| Yerel final AI | Qwen3 + llama.cpp |
| Ana platform | Windows |

## Kurulum ve Windows dağıtımı

Kaynak paket doğrudan son kullanıcı kurulumu değildir. Windows production paketi `installer/build_windows.bat` ile hazırlanır ve hedef çıktı tek `AI_Director_Setup.exe` dosyasıdır.

Kurulum/build aşamasında FFmpeg ve AI runtime bileşenleri stage edilir. Kaynak ZIP'inde API anahtarları veya OAuth sırları tutulmaz.

### YouTube yapılandırması

`app/youtube/build_config.py` kaynak güvenli placeholder'dır; gerçek production secret'ları kaynak koda commit edilmez. Windows build pipeline'ı gerekiyorsa `YOUTUBE_API_KEY` ve base64 kodlu `YOUTUBE_OAUTH_CLIENT_JSON_B64` environment değişkenlerinden build-time configuration üretebilir.

Son kullanıcı için YouTube bağlantısı ayrıca **Connection Center** üzerinden yapılandırılabilir; bu nedenle yalnızca source ZIP'in placeholder dosyasına bakarak YouTube'un kaynak paketten doğrudan çalışması beklenmemelidir.

## Ana işlevler

- Profesyonel timeline editing, trim/ripple/insert/overwrite ve marker işlemleri.
- Gerçek FFmpeg export, çoklu ses miksleme, ducking ve teslimat QC.
- AI Director, scene/rhythm/visual/audio/subtitle çok aşamalı düzenleme.
- Whisper tabanlı konuşma analizi ve gerçek subtitle → FFmpeg render bağlantısı.
- Smart Reframe ve Shorts Factory.
- 50K metadata-first Creative Library / Asset Marketplace.
- Proxy generation, cache/LRU, predictive warmup ve playback performance governor.
- GPU-aware/adaptive render scheduling.
- YouTube Creator Studio, queue, QC ve upload altyapısı.
- Autosave, crash recovery, transactional revision ve runtime self-test.

## Klasör yapısı

Yalnızca release içinde gerçekten bulunan ve aktif kullanılan ana paketler aşağıdadır:

```text
app/
├── agents/       AI agent/orchestration katmanı
├── ai/           AI Director ve AI yardımcıları
├── audio/        ses motoru/waveform/audio processing
├── brain/        AI karar/creative mantığı
├── effects/      efekt ve Creative Library
├── export/       gerçek FFmpeg export/render pipeline
├── motion/       motion/animation katmanı
├── performance/  playback ve hardware acceleration
├── plugins/      plugin/entegrasyon katmanı
├── preview/      preview/cache yardımcıları
├── pro/          profesyonel NLE işlemleri
├── project/      proje, autosave ve recovery
├── proxy/        proxy worker/cache/profile/warmup
├── reference/    reference DNA ve style bilgisi
├── render/       export motoruna compatibility facade
├── runtime/      FFmpeg/runtime/path yardımcıları
├── scene/        scene analysis
├── shorts/       Shorts Factory ve Smart Reframe
├── subtitle/     subtitle üretim/stil/render bağlantısı
├── tests/        proje testleri
├── timeline/     timeline modeli ve işlemleri
├── ui/           PySide6 arayüzü
├── video/        video yardımcıları
└── youtube/      YouTube Studio/OAuth/queue/upload
```

`capture`, `cloud`, `creator`, `genesis`, `network`, `studio` ve `workflow` gibi daha önce planlama metinlerinde görülen klasör adları bu release'in gerçek `app/` ağacında değildir; bunlar aktif modül gibi belgelenmez.

## Doğrulama

Release hazırlığında syntax/compile, API contract audit, packaging preflight ve hedefli regression/E2E testleri çalıştırılır. Windows Qt smoke test, gerçek GPU donanımı ve gerçek YouTube hesabı gerektiren testler yalnızca ilgili gerçek ortamda doğrulanabilir.

## Sürüm geçmişi

| Sürüm | Ana değişiklik |
|---|---|
| **v2.101.7** | Release hygiene, gerçek medya E2E, subtitle render, Shorts/Reframe routing ve temiz source package |
| **v2.101.6** | Release gap completion; Shorts/Smart Reframe routing, standalone 9:16 flow, render compatibility bridge |
| **v2.101.5** | Unified subtitle render pipeline; ASS/SRT → FFmpeg filtergraph bağlantısı |
| **v2.101.4** | Runtime API hardening, import audit, packaging/preflight düzeltmeleri |
| **v2.101.x** | YouTube/AI/runtime reliability, proxy, playback ve packaging hardening katmanları |
| **v2.9–v2.100** | Professional editor, AI Director, asset library, proxy/render intelligence, YouTube Studio ve performans katmanlarının kademeli teslimi |
| **v0.1–v2.8** | Proje iskeleti, timeline, preview, FFmpeg export, audio engine, subtitles ve temel AI editing katmanları |

## Lisans

Bu release ile birlikte `LICENSE` dosyası dağıtılır. Üçüncü taraf runtime/model lisansları kendi paketlerinin lisans koşullarına tabidir.
