# AI Director — v2.14 Performance Edition

## v2.9 Professional Editor Upgrade

This release adds a dedicated professional NLE core on top of the existing AI Director
pipeline. Studio now exposes **⚙ Professional Tools…**.

### Professional editing
- Frame-accurate nudge and snap-to-edit-point.
- Insert and overwrite editing primitives.
- Roll, slide and slip edit operations.
- Range ripple-delete for editorial cleanup.
- Persistent timeline markers with notes/duration.
- Missing-media relink workflow.
- Serializable render queue foundation.
- Color-grade primitives for exposure/contrast/saturation/gamma and temperature/tint.
- New `app/pro/` package keeps the professional engine independent from Qt, so the same
  operations can later power keyboard shortcuts, trim tools and background workers.

The existing AI Director features remain available: AI edit analysis, beat sync, motion,
subtitle studio, effects/music, audio processing, versioning, autosave, crash recovery,
FFmpeg export and channel/reference intelligence.

# AI Director

Uzun videoları otomatik düzenleyen, Shorts üreten, altyazı oluşturan ve içerik üretici
iş akışını tek uygulamada yönetmeyi hedefleyen açık mimarili **Creator Operating System**
projesi.

## Proje Durumu

| Bilgi | Durum |
|-------|-------|
| Sürüm | **v2.14 — Performance Edition + AI Shorts Director** |
| Geliştirme | Aktif |
| Hedef | Windows / Linux / macOS |
| Ana dil | Python 3.10+ |
| UI | PySide6 |
| Video | FFmpeg |
| Görüntü işleme | OpenCV |
| AI | Whisper + yerel modeller |


## v2.14.0 — Performance Edition

Bu sürüm, profesyonel özellikleri korurken uygulamanın günlük kullanımda daha hafif
hissetmesine odaklanır.

- Ağır Studio / AI Subtitle / Pipeline sayfaları artık **lazy-load** edilir; uygulama açılışında topluca oluşturulmaz.
- Başlangıçta hafif bir loading ekranı gösterilir; son kullanılan sayfa event-loop'a bırakılarak açılır.
- Studio `refresh()` artık ana UI thread'inde toplu FFmpeg thumbnail üretmez; thumbnail'lar **ertelenmiş ve kademeli** doldurulur.
- Timeline preview, aynı klip içinde sürekli lineer klip taramasını önlemek için **preview cache** kullanır.
- Performans regression testleri eklendi.
- Tam test paketi uzun sürebildiğinden CI/yerel çalıştırmada hedefli testlerin ayrıca çalıştırılması önerilir.

Performans ilkesi: AI/Whisper, scene analysis ve render gibi ağır işler kullanıcı arayüzündenyrı worker'larda tutulur; “viral” veya AI analizleri otomatik olarak açılışta çalıştırılmaz.

## Bu Sürümde Neler Var?

**v0.1** — proje iskeleti, PySide6 penceresi, sistem kontrolü, modül yol haritası.

**v0.2** — Timeline modeli, video yükleme (ffprobe/OpenCV), proje aç/kaydet (`.aidproj`).

**v0.3** — FFmpeg export (ilk sürüm): Studio → **Dışa Aktar…** ile timeline'ı tek bir MP4
dosyasına render eder; çözünürlük ön ayarları (1080p/720p/dikey/480p), arka planda
çalışma, ilerleme + iptal.

**v0.4** — Basic Timeline: sürükleyerek taşıma (move), kenardan kırpma (trim),
böl/sil/ripple-sil, snap (yapış), zoom, playhead sürükleme, SMPTE timecode.

**v0.5** — Video Preview
- Studio'ya, timeline'daki video izini gerçek zamanlı oynatan bir **önizleme paneli**
  eklendi (`QMediaPlayer` tabanlı).
- Play / Pause, Seek (sürgü), bir kare ileri/geri adımlama, ses düzeyi, tam ekran.
- Timeline ile çift yönlü senkronizasyon: oynatırken playhead ilerler; cetvelden
  playhead'i sürüklemek önizlemeyi de o ana taşır.
- Klipler arası boşluklarda (henüz klip olmayan aralıklarda) boş/siyah görünüm
  gösterilir; önizleme klibin kendi gömülü sesini çalar (ayrı ses izlerinin tam
  karışımı yalnızca export'ta uygulanır, bkz. v0.6).

**v0.6** — Real FFmpeg Engine
- Export artık **tek bir ffmpeg çağrısında** tüm timeline'ı işleyen bir
  `-filter_complex` grafiği kullanır (ara dosya üretimi yok); klipler arası
  boşluklar siyah kare + sessizlikle dolduruluyor, böylece export süresi
  timeline süresiyle birebir eşleşiyor.
- **Audio mixing**: birden fazla ses izi varsa hepsi tek çıktı akışında karıştırılır.
- **Kodek seçimi**: H.264, H.265 ve (sisteminizde varsa) AV1; export diyaloğu yalnızca
  gerçekten kurulu olan kodekleri listeler.
- Gerçek zamana dayalı ilerleme yüzdesi ve anında iptal.

**v0.7** — Audio Engine
- **Klip bazlı**: kazanç/ses seviyesi (dB), mute, fade in/out (`app/timeline/model.py`
  → `Clip.gain_db/muted/fade_in/fade_out`; Studio → **Ses Klibi…**).
- **İz bazlı**: müzik/seslendirme (`voice`) rolleri, iz kazancı, mute, EBU R128
  normalizasyon (`loudnorm`, -16 LUFS), ve **ducking** — `voice` izi konuşurken
  `duck=True` olan müzik izi otomatik kısılır (`sidechaincompress`);
  Studio → **Ses İzleri…**.
- **Waveform üretimi**: ffmpeg + numpy ile dalga formu (peak) çıkarımı, diske
  önbelleklenir (`app/audio/engine.py::generate_waveform_peaks`).
- Tüm filtreler `command_builder.py`'deki tek geçişli filtergraph'a entegre;
  gerçek ffmpeg ile mute/kazanç/ducking doğrulayan export testleri eklendi.

**v0.8 (bu sürüm)** — AI Subtitle
- **Whisper entegrasyonu** (`app/subtitle/transcribe.py`, opsiyonel `openai-whisper`
  bağımlılığı): kelime bazlı zaman damgalarıyla transkripsiyon. Kurulu değilse
  açık bir hata mesajı gösterilir, uygulamanın geri kalanı etkilenmez.
- **Türkçe öncelikli**; İngilizce, Almanca, Fransızca ve otomatik dil algılama
  da desteklenir.
- **Cümle segmentasyonu**: kelime zaman damgalarından okunabilir altyazı satırları
  (karakter/süre/kelime sayısı sınırları + noktalama) — saf Python, test edilebilir.
- **SRT / VTT dışa aktarma**; videoya **yumuşak gömme** (mov_text akışı, yeniden
  encode yok) veya **yakma** (burn-in, kalıcı, yeniden encode gerekir).
- **UI**: Studio → **Altyazı…** butonu ve sidebar'da bağımsız **AI Subtitle** sayfası;
  transkripsiyon arka planda (`QThread`) çalışır, UI donmaz.

**v1.0 (bu sürüm) — İlk Gerçek Beta**
- **Scene Detection** (`app/scene/detector.py`): ek bir OpenCV/PySceneDetect bağımlılığı
  gerektirmeden, zaten zorunlu olan ffmpeg'in `select='gt(scene,T)'` + `showinfo`
  filtreleriyle sahne (sert kesim) zaman damgalarını tespit eder — video/ses çıktısı
  üretmediği için gerçek zamanlıdan çok daha hızlıdır. Bulunan zaman damgaları, saf
  Python `split_at_scenes()` ile seçili klibi (ve bağlı ses klibini) o noktalarda
  otomatik olarak böler; timeline'daki ilişkisiz diğer izler etkilenmez.
- **UI**: Studio → **Sahne Algıla…** butonu; hassasiyet eşiği ayarlanabilir, tespit
  arka planda (`QThread`) çalışır.
- Bu sürümle birlikte **ilk uçtan uca akış** (medya içe aktar → timeline düzenle →
  sahne tespiti ile otomatik böl → ses ayarları → altyazı → FFmpeg export) tamamlandı;
  bu nedenle proje v1.0 "ilk gerçek beta" olarak etiketlendi. Smart Reframe ve Creator
  Assistant gibi daha önce v0.9/v1.0 için planlanmış özellikler, kapsam netliği için
  v1.1+'a ertelendi (bkz. Yol Haritası).

**v1.1 (bu sürüm) — Basic Editing Engine + Real FFmpeg Render + Audio Engine**
- **Basic Editing Engine**: Speed, Reverse, Freeze frame, Crop, Rotate; keyframe
  altyapısı (opacity/position/scale/rotation) ve klipler arası Crossfade geçişi.
- **Real FFmpeg Render**: Platform ön ayarları (YouTube/Shorts/TikTok/Instagram/
  Özel), ses kodeği seçimi (AAC/MP3/WAV); render sırasında FPS/bit hızı/hız (Nx)/
  ETA ve CPU/GPU kullanımı gösterilir.
- **Audio Engine**: EQ, Compressor, Limiter, Noise reduction, Voice enhancement
  (mevcut kazanç/fade/mute/ducking/normalizasyon özelliklerine ek olarak).
- Ayrıntılar için [CHANGELOG.md](CHANGELOG.md#v110-basic-editing-engine--real-ffmpeg-render--audio-engine-tamamlandı).

**v1.2 (bu sürüm) — Subtitle Studio + AI Basic Editor**
- **Subtitle Studio**: altyazı satırlarını DÜZENLEME (metin/zamanlama/birleştirme/bölme),
  5 hazır STİL ön ayarı (renk/font/konum/kutu), giriş ANİMASYONU (fade/pop/kayma), o an
  konuşulan kelimeyi vurgulayan KARAOKE tarzı kelime vurgusu, anahtar kelimeye dayalı
  otomatik EMOJİ ekleme; hepsi `.ass` formatına (`Stilli Yak`) basılabilir.
- **AI Basic Editor** (yeni sidebar sayfası: **AI Video Edit**): sessizlik, uzun duraklama,
  tekrar ve dolgu kelime tespiti + sahne değişimi bilgisi + önemli kelime önerisi; her
  öneri ayrı ayrı kabul/ret edilip tek tıkla timeline'dan kesilir.
- Ayrıntılar için [CHANGELOG.md](CHANGELOG.md#v120-subtitle-studio-tamamlandı--ai-basic-editor-eklendi).

**v1.3 (bu sürüm) — Non-Destructive Editing: Sürüm Geçmişi + Autosave + Crash Recovery**
- **Sürüm Geçmişi (Versioning)**: Ctrl+Z geçmişinden farklı, proje kapatılıp açılsa bile
  KALICI kalan, kullanıcının elle isimlendirdiği kontrol noktaları. Düzen → **"Sürüm
  Geçmişi…"** (Ctrl+Alt+V) ile sürüm oluştur/listele/geri yükle/sil; geri yüklemeden
  önce mevcut çalışma otomatik olarak yedeklenir.
- **Otomatik Kayıt (Autosave)**: proje kaydedilmemiş değişiklik içeriyorsa arka planda
  2 dakikada bir sessizce bir kurtarma kopyası yazılır; ana `Kaydet` akışını etkilemez.
- **Çökme Sonrası Kurtarma (Crash Recovery)**: uygulama bir önceki çalıştırmada düzgün
  kapatılmadıysa (çökme/güç kesintisi/zorla sonlandırma), açılışta kurtarılabilir
  oturumlar listelenir ve tek tıkla geri yüklenebilir.
- **AI düzenlemeleri de dahil TÜM düzenlemeler** tek tuşla (Ctrl+Z / Düzen → Geri Al)
  geri alınabilir — AI Basic Editor'ün uyguladığı kesimler diyalog açılmadan hemen önce
  otomatik olarak undo geçmişine eklenir.
- Ayrıntılar için [CHANGELOG.md](CHANGELOG.md#v130-non-destructive-editing-tamamlandı--sürüm-geçmişi--autosave--crash-recovery).

## v2.6 — Adaptive Beat Sync & Director Motion

Bu sürüm, v2.5'teki BPM tabanlı senkronizasyonu gerçek ses analizi ve kontrollü
motion uygulama katmanıyla genişletir.

- **Gerçek beat analizi:** `app/audio/beat_detector.py` FFmpeg + NumPy ile ses
  akışından BPM ve onset/beat zamanlarını çıkarabilir. Librosa zorunlu değildir.
- **Detected-beat sync:** Director artık `bpm=` veya `beat_times=` alarak kesim ve
  transition kararlarını gerçek beat zamanlarına hizalayabilir.
- **Phase offset:** Müzik intro'su/offset'i için beat grid fazı desteklenir.
- **Motion safety:** Hook, pattern-break, B-roll ve beat olayları için profile göre
  yoğunluk sınırı ve cooldown uygulanır; sürekli zoom/shake üretimi engellenir.
- **Non-destructive motion:** `app/motion/director_motion.py` mevcut Clip keyframe
  altyapısına scale/position hareketlerini uygular; mevcut keyframe'leri yalnızca
  aynı zaman noktasında günceller.
- **Director entegrasyonu:** `build_director_plan(..., bpm=..., beat_times=...)`
  sonucu `metadata["edit_sync"]` içinde makine-okunabilir sync planı taşır.
- **Geriye dönük uyumluluk:** Eski `build_director_plan(report, transcript, profile)`
  çağrıları çalışmaya devam eder.

## Kurulum

```bash
git clone https://github.com/yourname/AI_Director.git
cd AI_Director

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
python app/main.py
```

### FFmpeg (export için ZORUNLU)

- Windows: `winget install Gyan.FFmpeg`
- macOS: `brew install ffmpeg`
- Linux (Debian/Ubuntu): `sudo apt install ffmpeg`

FFmpeg kurulu değilse uygulama yine açılır ve video yükleyip timeline'da düzenleyebilirsiniz;
yalnızca **Dışa Aktar** adımı FFmpeg ister ve eksikse anlaşılır bir hata gösterir.

H.265 ve AV1 kodekleri, FFmpeg derlemenizde sırasıyla `libx265` ve `libsvtav1`/`libaom-av1`
bulunmasını gerektirir; export diyaloğundaki **Kodek** listesi yalnızca sisteminizde
gerçekten kullanılabilir olan kodekleri gösterir (yoksa yalnızca H.264 sunulur).

### Testler

```bash
pip install -r requirements-dev.txt
python -m pytest app/tests
```

Ekransız ortamda (sunucu/CI): `QT_QPA_PLATFORM=offscreen python -m pytest app/tests`

Export testleri gerçek `ffmpeg` çalıştırır; FFmpeg kurulu değilse bu testler otomatik atlanır.

## Kullanım

1. **Studio** sayfasında **"+ Medya Ekle"** ile bir veya birden çok video seçin.
2. Medya havuzundan bir videoya çift tıklayın (veya seçip **"Timeline'a Ekle"**) —
   video izine ve (sesi varsa) ses izine otomatik eklenir.
3. **Önizleme** panelinden videoyu oynatın; timeline cetveline tıklayıp playhead'i
   sürükleyerek de belirli bir ana atlayabilirsiniz (ikisi birbiriyle senkronize).
4. Timeline'da bir klibe tıklayıp **"Böl (ortadan)"**, **"Sil"** veya kenarından
   sürükleyerek kırpın; snap ve zoom kontrolleriyle hassas düzenleyin.
5. **"Dışa Aktar…"** ile çözünürlük/FPS/**kodek** (H.264/H.265/AV1)/çıktı dosyası
   seçip render'ı başlatın; ilerleme çubuğundan gerçek zamanlı takip edin, gerekirse
   iptal edin.
6. **"Ses Klibi…"** ile seçili ses klibinin kazancını/mute/fade in-out'unu, **"Ses
   İzleri…"** ile müzik/seslendirme izlerini (rol, kazanç, normalizasyon, ducking)
   ayarlayın.
7. **"Altyazı…"** (veya sidebar'daki **AI Subtitle** sayfası) ile Whisper'la otomatik
   altyazı çıkarın; satırları düzenleyin, bir stil/animasyon/vurgu/emoji ön ayarı seçin,
   SRT/VTT olarak kaydedin ya da videoya gömün (yumuşak akış, düz yakma veya stilli
   "Stilli Yak (ASS)").
8. **"Sahne Algıla…"** ile seçili video klibini, otomatik tespit edilen sahne
   kesimlerinde (hassasiyet eşiği ayarlanabilir) tek tıkla parçalara bölün.
9. **"AI Düzenle…"** (veya sidebar'daki **AI Video Edit** sayfası) ile sessizlik, uzun
   duraklama, tekrar ve dolgu kelimeleri tespit edin; önerileri tek tek kabul/ret edip
   kabul ettiklerinizi tek tıkla timeline'dan kesin.
10. **Dosya → Kaydet** ile projeyi `.aidproj` dosyasına kaydedin; **Dosya → Proje Aç…**
   veya **Son Projeler** ile geri yükleyin.
11. **Düzen → Geri Al / İleri Al** (Ctrl+Z / Ctrl+Y) ile herhangi bir düzenlemeyi (AI
   Düzenle dahil) tek tuşla geri alın. Önemli bir aşamayı KALICI olarak işaretlemek
   isterseniz **Düzen → Sürüm Geçmişi…** (Ctrl+Alt+V) ile adlandırılmış bir sürüm
   oluşturun; istediğiniz zaman o ana geri dönebilirsiniz. Uygulama beklenmedik
   şekilde kapanırsa bir sonraki açılışta kurtarılabilir çalışmanız sorulur.

## Klasör Yapısı

```
AI_Director/
  app/
    main.py            giriş noktası
    runtime/           yollar, ayar, log, sistem kontrolü, modül kaydı, yardımcılar
    timeline/          Timeline / Track / Clip veri modeli
    video/             ffprobe/OpenCV ile medya bilgisi okuma
    project/           Project / MediaItem, .aidproj kaydet-yükle, Sürüm Geçmişi
                       (versioning.py), Autosave + Crash Recovery (autosave.py, v1.3)
    preview/           timeline zamanı → aktif klip/kaynak zamanı çözümleme (v0.5)
    export/            FFmpeg filtergraph motoru (command_builder) + worker
    audio/              ses filtre motoru: kazanç/fade/mute/normalizasyon/ducking,
                        waveform üretimi (v0.7)
    subtitle/          Whisper transkripsiyon, düzenleme, stil/animasyon/vurgu/emoji,
                       SRT/VTT/ASS, gömme (v0.8, v1.2'de genişletildi)
    scene/             ffmpeg tabanlı sahne (kesim) tespiti + otomatik bölme (v1.0)
    ai/                AI Basic Editor: sessizlik/tekrar/dolgu kelime/duraklama analizi,
                       öneri kabul/ret, timeline'a otomatik kesim uygulama (v1.2)
    ui/                tema, bileşenler, Studio sayfası, timeline çizimi,
                       önizleme oynatıcısı (preview_widget), export/ses/altyazı/
                       sahne/AI düzenleme diyalogları
    plugins/           eklenti arayüzü
    brain/ capture/ cloud/ creator/ effects/ genesis/
    installer/ motion/ network/ performance/ render/
    shorts/ studio/ workflow/                     (sonraki sürümler)
    tests/             pytest testleri (100+)
  docs/                mimari ve yol haritası
  requirements*.txt
```

## Yeni Modül Eklemek

`app/runtime/module_registry.py` içindeki `MODULES` listesine bir `ModuleInfo` ekleyin;
kenar çubuğu butonu ve sayfa otomatik oluşur.

## Yol Haritası

| Sürüm | Hedef |
|-------|-------|
| v0.1 Alpha | Proje yapısı, PySide6 başlangıcı, ilk pencere, temel yapı ✅ |
| v0.2 Alpha | Timeline iskeleti, video yükleme, proje aç/kaydet ✅ |
| v0.3 Alpha | FFmpeg entegrasyonu, ilk export ✅ |
| v0.4 Alpha | Basic Timeline (move/trim/snap/zoom/playhead/timecode) ✅ |
| v0.5 Alpha | Video Preview (play/pause/seek/frame step/volume/fullscreen) ✅ |
| v0.6 Alpha | Real FFmpeg Engine (filtergraph, audio mixing, H.264/H.265/AV1) ✅ |
| v0.7 Alpha | Audio Engine (kazanç/fade/mute, müzik/seslendirme izleri, normalizasyon, ducking, waveform) ✅ |
| v0.8 Alpha | AI Subtitle (Whisper, kelime zamanlama, SRT/VTT, gömme — TR öncelikli) ✅ |
| v1.0 Beta | İlk gerçek beta: Scene Detection (ffmpeg tabanlı, otomatik bölme) + tüm önceki modüllerin uçtan uca akışı ✅ |
| v1.1 Beta | Basic Editing Engine (speed/reverse/freeze/crop/rotate/keyframe/crossfade) + Real FFmpeg Render (platform ön ayarları, FPS/ETA/CPU/GPU) + Audio Engine (EQ/compressor/limiter/denoise/voice enhance) ✅ |
| v1.2 Beta | Subtitle Studio (düzenleme + stil/animasyon/kelime vurgusu/emoji) + AI Basic Editor (sessizlik/tekrar/dolgu kelime analizi, kabul/ret, otomatik kesim) ✅ |
| **v1.3 Beta** | **Non-Destructive Editing: Sürüm Geçmişi (versioning) + Otomatik Kayıt (autosave) + Çökme Sonrası Kurtarma (crash recovery)** ✅ |
| v1.4+ | Smart Reframe (yüz/nesne takibi, otomatik 9:16), Shorts Factory, Creator Assistant (doğal dil/sesli komut) |

Ayrıntılar: [docs/ROADMAP.md](docs/ROADMAP.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [CHANGELOG.md](CHANGELOG.md)


### v1.6 Auto Director

Auto Director artık kesim önerilerini güvenlik bütçesiyle seçmenin yanında transcript üzerinden hook, anlatı beat, pattern-break ve B-roll cue olayları üretir. `DirectorPlan` içindeki `hook_score`, `narrative_score` ve `events` alanları sonraki kanal-öğrenme ve referans-stil motorlarının temel sözleşmesidir.

### v1.7 Channel Intelligence
The new `app.ai.channel` module converts multiple Director plans into a reusable
`ChannelStyleProfile` (edit DNA). It measures hook strength, narrative density,
cut ratio, pacing, B-roll cues/minute, pattern breaks/minute, beats/minute and
highlight density. `compare_style()` compares a target DirectorPlan to that
profile and returns similarity plus concrete edit adjustments. The module is
deterministic and does not require an LLM, making it suitable as the stable
contract for future YouTube reference ingestion and style-learning layers.

## v2.8 — Professional Edit Planning Core

`app.ai.pro_editor` introduces a reviewable edit blueprint for raw footage. With optional
`opencv-python`, `analyze_video(path)` samples frames and estimates shot boundaries and
visual signals (brightness, sharpness, motion, histogram change). `build_pro_edit_plan(...)`
turns those signals plus optional beat times and transcript events into explainable edit beats.

```python
from app.ai.pro_editor import analyze_video, build_pro_edit_plan

duration, shots = analyze_video("raw.mp4", sample_fps=1.0)
plan = build_pro_edit_plan("raw.mp4", duration, shots, style="balanced", beat_times=[])
print(plan.to_json())
```

Styles: `balanced`, `dynamic`, `cinematic`, `talking_head`, `short_form`. Visual analysis is
heuristic, not semantic scene comprehension; flagged shots are not automatically removed.
Preview and human approval remain important. Focused tests: `pytest -q app/tests/test_pro_editor.py`.


## v2.8 — Professional Edit Intelligence

- Added `app.ai.pro_editor`: sampled-frame visual quality, brightness, sharpness, motion and histogram-change analysis.
- Added explainable edit blueprints with cinematic, balanced, dynamic, talking-head and short-form styles.
- Long/low-quality shots are flagged for review or pattern-break suggestions instead of being blindly deleted.
- Beat accents are sparse and cooldown-limited to avoid over-editing.
- API: `analyze_video(path)` then `build_pro_edit_plan(source, duration, shots, style=..., beat_times=..., transcript_events=...)`.
- OpenCV is optional; install `opencv-python` for sampled-frame analysis. This version provides explainable heuristics, not human-level semantic understanding; preview and approval remain important.

## v2.9 Channel Autopilot

`app.ai.channel_autopilot` is the channel-level intelligence layer. It accepts normalized YouTube Analytics rows and public competitor/reference metadata and produces:

- historical channel baseline
- CTR / 30-second retention / average-view-percentage diagnostics
- competitor edit fingerprints
- measurable pacing/edit recipes
- title + description + tags + thumbnail concepts
- Turkey-local publishing windows from the channel's own viewer-online histogram
- an end-to-end autopilot workflow manifest

The core intentionally does not claim access to private YouTube Analytics until the user connects/imports that data. It also converts named creator references into measurable traits instead of attempting to reproduce a creator's exact signature.

For real account analysis, add a YouTube OAuth/Analytics ingestion adapter that maps YouTube Studio metrics into `AnalyticsPoint` and maps the Audience "When your viewers are on YouTube" report into `viewer_hours_tr`.

## v3.0 — Professional Editor Core
The new Professional Editor mode is designed around editorial decisions rather than automatic effects. It protects spoken content, removes only high-confidence dead air/redundancy within a cut budget, adds sparse pacing accents, and applies restrained camera motion. Use **AI Video Edit → Profesyonel Otomatik Kurgu** after analysis.

## v2.13 — AI Shorts Director
- Uzun videodan 12 adede kadar çeşitlendirilmiş Shorts adayı çıkarma.
- Hook / build-up / payoff, bağlam, duygu, pacing ve rewatch sinyallerini birlikte puanlama.
- Hook→payoff bütünlüğünü koruyan aday pencereleri ve duplicate suppression.
- 9:16 safe-center fallback + yüz/konuşmacı tracking cue kontratı.
- Dynamic caption cue'ları, vurgu kelimeleri ve güvenli altyazı alanı.
- B-roll/cutaway önerileri, narrative punch-in ve beat cue'ları.
- Transcript tabanlı sessizlik aralıklarını tespit edip edit planına ekleme.
- Seçilen Short'u non-destructive biçimde timeline'a aktarabilme.
- Proje içine `editor_data.shorts_director` metadata kaydı.
- Virallik garantisi iddia edilmez; sistem editoryal/watchability sinyallerini optimize eder.


### v2.15 Turbo Performance
- UI thread'inde ffprobe/OpenCV medya analizi yok.
- FFmpeg thumbnail işleri 2 worker'lı muhafazakar thread pool'da.
- Dashboard sistem kontrolleri açılıştan ayrıldı.
- Timeline/preview CPU yarışını azaltmak için medya işleri düşük paralellikte tutuluyor.
- Ağır AI/Whisper işlemleri kullanıcı başlatana kadar çalıştırılmıyor.


### v2.16 Adaptive Performance
- Added dependency-light resource profiles for Eco/Balanced/Performance hardware tiers.
- Added a bounded LRU cache utility to prevent unbounded preview metadata growth.
- Added conservative battery-mode resource planning and proxy-resolution targets.
- Existing project files and export presets remain backward compatible.

## V2.26.1 Unified Professional Render

- Word-level karaoke ASS events are burned in the same FFmpeg graph as Smart Reframe and transitions.
- Render profiles support automatic CPU/NVIDIA/VideoToolbox selection with CPU fallback.
- Preview renders reuse the same filtergraph and only lower resolution/quality.
- Render queue state can be persisted to JSON and resumed/reset after application restart.
- Music ducking exposes threshold/ratio/attack/release controls; optional EBU-style `loudnorm` finalization is available.

Recommended next steps: waveform-driven audio preview, GPU-aware proxy caching, scene-level transition presets, and render farm/batch delivery.

## v2.26.7 — GPU Preview / Zero-Copy Path

- Backend-neutral GPU decode selection for D3D11VA, CUDA/NVDEC, VAAPI,
  VideoToolbox and Vulkan with a universal software fallback.
- Preview texture handles can remain GPU-backed; Python does not map/copy pixel
  buffers unless an effect explicitly requires CPU pixels.
- FFmpeg hardware-acceleration arguments are generated from the selected backend.
- Preview compositor tracks GPU/CPU/zero-copy frame usage without adding heavy
  graphics bindings as mandatory dependencies.

## v2.30 Multimodal Model Layer

The editor can now consume optional model observations (objects, scene, emotion, shot type, action and VLM description) through `MultimodalModelAdapter`. Results are cached under `.ai_cache/multimodal` and fused into the same explainable Edit Decision Graph used by the GPU compositor.

A local deterministic `JsonModelAdapter` is included so a real VLM/ONNX/TensorRT/CoreML/DirectML runner can be integrated without changing editorial or rendering code.
