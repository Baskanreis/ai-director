"""Ses motoru: klip/iz bazlı kazanç, fade, mute, normalizasyon, ducking ve
waveform (dalga formu) üretimi (v0.7 Audio Engine).

Bu paket Qt'den ve `app.export`'tan bağımsızdır: burada üretilen ffmpeg filtre
parçaları `app.export.command_builder` tarafından ana filtergraph'a eklenir.
"""

from .mix_engine import AudioMixEngine, build_audio_mix_plan
