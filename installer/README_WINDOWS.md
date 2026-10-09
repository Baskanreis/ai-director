# Windows tek Setup dağıtımı

`installer\build_windows.bat` kaynak ağacından tek `dist\AI_Director_Setup.exe` üretir.

Build sırasında `stage_ai_runtime.ps1` Whisper Base, Qwen3 1.7B Q4_K_M ve llama.cpp Windows x64 CPU runtime bileşenlerini `dist\AI_Director` içine alır. Inno Setup bunların tamamını tek Setup.exe içine paketler.

Son kullanıcı Setup.exe dışında dosya çalıştırmaz ve ayrıca FFmpeg, Python, Whisper, llama.cpp veya model kurmaz. GitHub Actions ayrıca `dist` altında yalnızca Setup.exe bulunduğunu doğrular.

Not: Yerel AI runtime build aşamasında indirildiği için Setup üretim makinesinin internet erişimi gerekir; bu gereksinim son kullanıcıya yansıtılmaz.
