"""app1/, app2/, app3/ klasorlerini tek bir app/ paketinde birlestirir.

Neden: GitHub'in web "Upload files" ekrani tek seferde en fazla 100 dosya kabul
ediyor. Orijinal `app/` paketi 241 dosya icerdigi icin depoda app1/app2/app3
olarak uc parcaya bolundu (her biri < 100 dosya, sorunsuz manuel yuklenebilir).
Kod icindeki `from app.X import Y` satirlari degismedi; bu yuzden calistirmadan
veya derlemeden once bu uc klasor fiziksel olarak `app/` altinda birlestirilmek
zorunda. Bu script onu yapar.

Kullanim:
    python merge_app.py

GitHub Actions is akisi (.github/workflows/build-windows.yml) bunu derlemeden
hemen once otomatik calistirir; yerel derleme/test icin de manuel calistirmaniz
yeterli.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "app"
PARTS = ["app1", "app2", "app3"]


def main() -> int:
    missing = [p for p in PARTS if not (ROOT / p).exists()]
    if missing:
        print(f"HATA: eksik klasor(ler): {', '.join(missing)}", file=sys.stderr)
        return 1

    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir()

    for part in PARTS:
        src = ROOT / part
        for item in src.iterdir():
            dest = TARGET / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    file_count = sum(1 for _ in TARGET.rglob("*") if _.is_file())
    if not (TARGET / "main.py").exists() or not (TARGET / "__init__.py").exists():
        print("HATA: birlestirme sonrasi app/main.py veya app/__init__.py bulunamadi.", file=sys.stderr)
        return 1

    print(f"OK: '{TARGET}' olusturuldu ({file_count} dosya).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
