# Mimari (v1.0)

```
app/main.py            -> giriş noktası (log + QApplication + MainWindow)
app/runtime/            -> paths, config, logger, system_check, module_registry, util
app/timeline/model.py    -> Timeline / Track / Clip (Qt'den bağımsız, saf Python)
                          Clip: gain_db/muted/fade_in/fade_out (v0.7)
                          Track: role(music|voice)/gain_db/muted/normalize/duck (v0.7)
app/video/media_info.py -> ffprobe/OpenCV ile video bilgisi okuma
app/project/project.py  -> Project / MediaItem, .aidproj kaydet/yükle (atomik, göreli yol)
app/audio/
  engine.py             -> klip/iz ses filtre parçaları (volume/afade/loudnorm/
                           sidechaincompress) + waveform peak üretimi (saf Python, v0.7)
app/subtitle/
  models.py             -> Word / Segment / Transcript (Qt'den ve Whisper'dan bağımsız)
  formats.py             -> SRT/VTT üretimi + kelime->cümle segmentasyonu (saf Python)
  transcribe.py           -> openai-whisper entegrasyonu (opsiyonel bağımlılık)
  embed.py                -> SRT/VTT dosyaya yazma, soft-mux (mov_text), burn-in
  worker.py                -> QThread sarmalayıcı (TranscribeWorker)
app/scene/
  detector.py             -> detect_scene_changes(): ffmpeg select='gt(scene,T)'+showinfo
                           (saf subprocess, video/ses çıktısı yok); split_at_scenes():
                           saf Python, zaman damgalarını timeline bölmesine çevirir (v1.0)
  worker.py                -> QThread sarmalayıcı (SceneDetectWorker)
app/preview/
  compositor.py         -> timeline zamanı -> aktif klip + kaynak zamanı (Qt'den bağımsız, v0.5)
app/export/
  command_builder.py     -> ExportSettings + tek geçişli ffmpeg -filter_complex üretici;
                           v0.7'den itibaren klip/iz ses filtreleri ve ducking dahil
  ffmpeg_export.py       -> export_timeline(): süreci çalıştırır, ilerleme/iptal/hata yönetimi
  worker.py               -> QThread sarmalayıcı (UI'yi bloklamaz)
app/ui/
  theme.py              -> QSS
  widgets.py            -> Card, Badge, row()
  pages.py              -> Panel / Ayarlar / AI Subtitle / yer tutucu sayfalar
  studio_page.py         -> medya havuzu + önizleme + timeline + ses/altyazı/export butonları
  preview_widget.py       -> PreviewPlayer: QMediaPlayer tabanlı önizleme oynatıcısı (v0.5)
  timeline_view.py       -> özel QPainter tabanlı timeline çizimi
  export_dialog.py       -> çözünürlük/fps/kodek/çıktı seçimi + ilerleme
  audio_panel.py          -> ClipAudioDialog / TrackAudioDialog / AudioTracksDialog (v0.7)
  subtitle_dialog.py      -> SubtitleDialog: transkripsiyon + SRT/VTT + gömme (v0.8)
  scene_dialog.py          -> SceneDetectDialog: eşik seçimi + tespit + otomatik bölme (v1.0)
  main_window.py          -> kenar çubuğu, sayfa yönlendirme, Dosya menüsü, proje yaşam döngüsü
app/plugins/base.py      -> Plugin / PluginManager
```

## İlkeler
- **Modül kaydı tek kaynaktır:** kenar çubuğu ve sayfalar `runtime/module_registry.py`
  üzerinden üretilir.
- **UI ile iş mantığı ayrıdır:** `timeline/`, `video/`, `project/`, `export/`, `preview/`,
  `audio/`, `subtitle/`, `scene/` paketleri PySide6'ya bağımlı değildir; bağımsız test edilebilir
  (bkz. `app/tests/`). `preview/compositor.py`, `export/command_builder.py`,
  `audio/engine.py` ve `subtitle/{models,formats}.py` saf Python olduğu için PySide6
  kurulu olmayan bir ortamda bile (örn. CI) doğrudan test edilebilir; `subtitle/transcribe.py`
  ise `openai-whisper`i yalnızca çağrıldığında (`import`) arar, kurulu değilse
  `SubtitleError` fırlatır — böylece opsiyonel bağımlılık eksikliği diğer testleri
  etkilemez. Yalnızca ince bir Qt katmanı (`preview_widget.py`, `worker.py`,
  `subtitle/worker.py`) bunları arayüze bağlar.
- **Export tek geçişli bir filtergraph motorudur (v0.6, v0.7'de ses filtreleriyle
  genişletildi):** her klip için ara dosya üretilmez; tüm timeline (klipler + aralarındaki
  boşluklar) tek bir `ffmpeg -filter_complex` grafiğinde ifade edilir (`trim`/`atrim` +
  `setpts`/`asetpts` + `concat`), böylece hem daha hızlı hem de klipler arası boşluklar ve
  çoklu ses izi karışımı (`amix`) doğru şekilde ele alınır. Klip/iz bazlı kazanç, fade,
  mute ve normalizasyon (`loudnorm`) filtergraph'a eklenir; `duck=True` olan müzik izleri,
  `voice` rolündeki izlerin sesi `sidechaincompress` ile yan-zincir referansı olarak
  kullanılarak otomatik kısılır — aynı pad'in hem miks hem yan-zincir girişi olarak
  kullanılabilmesi için `asplit` ile açıkça ikiye bölünür (ffmpeg aynı etiketi iki filtreye
  örtük olarak paylaştırmaz). Kodek (H.264/H.265/AV1) sistemde kurulu ilk uygun encoder'a
  göre seçilir (`command_builder.resolve_codec`). İlerleme, ffmpeg'in `-progress pipe:1`
  çıktısından okunan gerçek `out_time` değerine dayanır; iptal, çalışan tek sürece
  `SIGTERM`/gerekirse `SIGKILL` gönderilerek anında uygulanır.
- **Önizleme, export'tan ayrı ve daha basit bir modeldir (v0.5):** `PreviewPlayer`,
  video izindeki aktif klibi kendi gömülü sesiyle birlikte tek bir `QMediaPlayer` ile
  oynatır; duvar-saati tabanlı bir "master saat" playhead'i sürer, aktif klip
  değiştiğinde oynatıcının kaynağı değiştirilir, boşluklarda oynatıcı durdurulup
  boş bir görünüm gösterilir. Ayrı ses izlerinin tam karışımı (ve v0.7'deki
  kazanç/fade/ducking) yalnızca export aşamasında (`command_builder`) uygulanır —
  önizlemede canlı çoklu-iz ses mixi yoktur (bkz. `docs/ROADMAP.md`).
- **Altyazı motoru Whisper'ı sarmalar, dikte etmez (v0.8):** `subtitle/transcribe.py`
  Whisper'ın ham segment/kelime çıktısını `subtitle/models.py`'deki bağımsız veri
  modeline (`Word`/`Segment`/`Transcript`) çevirir; ekrana uygun satırlara bölme
  (`formats.segment_words_into_lines`) ayrı ve saf bir fonksiyondur, böylece gerçek
  bir Whisper modeli çalıştırmadan da (sahte/mock sonuçlarla) test edilebilir.
  Gömme iki ayrı yoldan sunulur: `embed.mux_soft_subtitles` (mov_text akışı,
  `-c copy`, yeniden encode yok) ve `embed.burn_in_subtitles` (`subtitles=` filtresiyle
  kalıcı, yeniden encode gerektirir).
- **Uzun işlemler UI'yi bloklamaz:** export ve transkripsiyon `QThread` üzerinde
  çalışır, ilerleme ve iptal sinyallerle iletilir.
- Kullanıcı verisi `~/.ai_director/` altında tutulur (ayarlar + loglar); proje dosyaları
  kullanıcının seçtiği herhangi bir yerde `.aidproj` olarak saklanır.
