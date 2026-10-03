# GitHub'a Manuel Yükleme ve .exe Oluşturma

## Neden app1 / app2 / app3?

GitHub'ın web **"Add file > Upload files"** ekranı tek seferde en fazla **100 dosya**
kabul ediyor. Projenin `app/` paketi 241 dosya içerdiğinden tek parça halinde
yüklenemiyordu. Bu yüzden `app/` klasörü üç ayrı üst-düzey klasöre bölündü:

| Klasör | İçerik | Dosya sayısı |
|---|---|---|
| `app1/` | `ai`, `export`, `pro`, `shorts`, `runtime` | 86 |
| `app2/` | `tests`, `subtitle`, `render`, `preview` | 86 |
| `app3/` | `ui`, `brain` + diğer küçük alt klasörler, `main.py`, `__init__.py` | 69 |

Kod içindeki `from app.X import Y` satırları **hiç değiştirilmedi** — çünkü
derlemeden/çalıştırmadan hemen önce `merge_app.py` script'i bu üç klasörü otomatik
olarak tek bir `app/` klasöründe birleştiriyor. Yani:

- **GitHub Actions** (`.github/workflows/build-windows.yml`) her push'ta önce
  `python merge_app.py` çalıştırır, sonra PyInstaller ile `.exe` derler. Elle bir şey
  yapmanız gerekmez.
- **Yerelde** çalıştırmak/denemek isterseniz önce `python merge_app.py` komutunu bir
  kez çalıştırıp `app/` klasörünü oluşturmanız yeterli.
- `app/` klasörü `.gitignore`'da — yani repoya **commitlenmiyor**, her build'de
  `app1+app2+app3`'ten yeniden üretiliyor. Gerçek kaynak kod `app1/`, `app2/`, `app3/`.

## GitHub'a Manuel Yükleme Adımları (web arayüzü)

1. Yeni, boş bir GitHub deposu oluşturun.
2. **Add file > Upload files** → bu zip'in İÇİNDEKİ şu öğeleri (zip'in kendisini değil)
   tek seferde sürükleyip "Commit changes" deyin:
   `app1/`, `app2/`, `app3/`, `assets/`, `docs/`, `models/`, `.github/`, `README.md`,
   `requirements*.txt`, `CHANGELOG*.md`, `docs_*.md`, `AI_Director.spec`,
   `merge_app.py`, `.gitignore`, `BUILD_EXE_TR.md`.
   - Bunların hepsi birlikte **294 dosya** eder ama GitHub'ın sınırı "tek bir sürükle-
     bırak hareketinde seçtiğiniz **üst düzey öğe/dosya sayısına** değil, o hareketle
     yüklenen toplam dosyaya" uygulanır; bu yüzden tamamını tek seferde seçmek yine
     sınırı aşabilir. Sorun çıkarsa aynı adımı **iki parça** halinde tekrarlayın
     (örn. önce `app1/`+`app2/`+diğer kök dosyalar, sonra `app3/`) — her ikisi de
     rahatça 100'ün altında kalır.
3. Depo sayfasında **Actions** sekmesine girin — "Build Windows EXE" otomatik başlar
   (önce `merge_app.py` ile `app/`'i oluşturur, sonra PyInstaller ile derler).
4. Bitince **Actions > (son çalışma) > Artifacts** bölümünden `AI_Director-windows`
   zip'ini indirin; içinde `AI_Director.exe` olur.

## Daha Güvenilir Alternatif: GitHub Desktop (tek tık, dosya sınırı yok)

1. Zip'i bilgisayarınıza çıkarın.
2. desktop.github.com adresinden kurun, hesabınızla giriş yapın.
3. **File > Add Local Repository** → çıkardığınız klasörü seçin → "create a repository".
4. **Publish repository** butonuna basın. 294 dosya tek seferde, sınırsız şekilde gider.

## Yerelde Deneme (Windows)

```bash
pip install -r requirements.txt pyinstaller
python merge_app.py
pyinstaller AI_Director.spec --noconfirm --clean
```
Çıktı: `dist/AI_Director/AI_Director.exe`

## Önemli Notlar

- **FFmpeg zorunludur** ama pip ile kurulmaz; export/render için kullanıcının
  bilgisayarında `ffmpeg` PATH'te olmalı.
- `requirements-optional.txt` (opencv, whisper) isteğe bağlıdır; dahil etmek
  isterseniz workflow'daki `pip install -r requirements.txt` satırının altına ekleyin.
- Etiketli bir sürüm (Release) için: `git tag v2.33.0 && git push origin v2.33.0`.
