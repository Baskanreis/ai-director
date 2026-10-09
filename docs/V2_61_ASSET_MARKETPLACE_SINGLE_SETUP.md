# V2.61 — Asset Marketplace / Pack Engine + Single Setup

AI Director artık 50K yaratıcı öğeyi yalnızca düz bir katalog olarak değil,
paket (Pack) mantığıyla yönetir.

## Built-in Packs

- Creator Core
- Cinematic Studio
- Viral Shorts
- Gaming & Glitch
- Podcast & Talking Head
- Beauty & Fashion
- Travel B-Roll
- Education & Tutorial
- Meme & Social
- Subtitle Studio
- LUT & Filter Lab
- Sound FX & Audio

B-roll, subtitle style ve LUT/filter ayrı bir harici uygulama değildir; mevcut
render motorunun uyumlu effect/motion/text/filter/template reçeteleri olarak
Pack Engine üzerinden yönetilir.

## Tek Setup sözleşmesi

GitHub Release/Actions çıktısı **yalnızca `AI_Director_Setup.exe`** olmalıdır.
PyInstaller'ın geçici onedir çıktısı ve model/runtime klasörleri build sırasında
oluşturulur, Inno Setup içine gömülür ve release'e ayrı dosya olarak gönderilmez.

Başarılı kurulumdan sonra kullanıcı ayrıca Python, FFmpeg, Whisper, llama.cpp
veya başka bir runtime kurmak zorunda değildir. AI runtime build aşamasında
Setup içine alınır; kurulum Program Files altındaki uygulama dosyalarını kendi
oluşturur.

Kullanıcı tarafından sonradan içe aktarılabilen Creative Pack JSON'ları
opsiyoneldir; temel marketplace özellikleri için gerekli değildir.

## Lisans

Built-in katalog orijinal, metadata-first/procedural reçetelerden oluşur.
CapCut, Premiere veya başka bir üçüncü tarafın lisanslı/proprietary assetleri
pakete kopyalanmaz.
