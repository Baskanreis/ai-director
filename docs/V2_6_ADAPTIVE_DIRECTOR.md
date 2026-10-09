# AI Director v2.6 — Adaptive Beat Sync & Director Motion

## Amaç

v2.5'teki BPM tabanlı planlayıcıyı gerçek ses sinyaliyle beslemek ve planlanan
motion efektlerini mevcut keyframe motoruna güvenli biçimde uygulamak.

## Akış

1. `detect_audio_beats(path)` FFmpeg ile mono PCM çıkarır.
2. NumPy onset envelope üzerinden BPM ve beat zamanları tahmin edilir.
3. `build_edit_sync_plan(..., beat_times=[...])` kesimleri en yakın beat'e hizalar.
4. Director `metadata["edit_sync"]` içinde beats/transitions/motion planını taşır.
5. İstenirse `apply_motion_plan(clips, cues)` bu planı Clip keyframe'lerine uygular.

## Güvenlik

Motion yoğunluğu profile göre sınırlandırılır. Cooldown, art arda gelen efektleri
bastırır. Uygulama mevcut keyframe'leri silmez; yalnızca üretilen zaman noktalarında
günceller. Timeline/export katmanı değiştirilmediği için bu sürüm non-destructive
kalmaya devam eder.

## Örnek

```python
from app.audio.beat_detector import detect_audio_beats
from app.ai.director import build_director_plan

audio = detect_audio_beats("music.wav")
plan = build_director_plan(report, transcript, profile,
                           bpm=audio["bpm"],
                           beat_times=audio["beats"])
```

Not: Bu beat detector, özel bir MIR/neural beat tracker'ın yerini tutmaz. Gürültülü,
çok ritimsiz veya yoğun konuşmalı kayıtlarda sonuçlar yaklaşık olabilir.
