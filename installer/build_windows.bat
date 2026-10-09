@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set CI_MODE=0
if /I "%~1"=="--ci" set CI_MODE=1

echo ========================================
echo AI Director - Windows Setup Build
echo ========================================

where py >nul 2>nul
if errorlevel 1 (
  echo [HATA] Python bulunamadi.
  if "%CI_MODE%"=="0" pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/6] Sanal ortam olusturuluyor...
  py -3 -m venv .venv
)

echo [2/6] Bagimliliklar kuruluyor...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo [3/6] Eski build temizleniyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
mkdir dist\installer

if not exist "assets\AI_Director.ico" (
  echo [HATA] assets\AI_Director.ico bulunamadi.
  goto :fail
)

echo [4/7] YouTube build configuration hazırlanıyor...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File installer\generate_youtube_config.ps1
if errorlevel 1 goto :fail

echo [5/7] Surum senkronizasyonu...
for /f %%V in (VERSION) do set APP_VERSION=%%V
powershell.exe -NoProfile -Command "$v=(Get-Content VERSION -Raw).Trim(); $iss=(Select-String -Path installer\AI_Director.iss -Pattern '#define MyAppVersion').Line; if($iss -notmatch [regex]::Escape($v)){ Write-Error ('ISS surumu VERSION ile uyusmuyor: '+$v+' / '+$iss); exit 1 }"
if errorlevel 1 goto :fail

echo [5/7] Paketleme preflight kontrolu...
".venv\Scripts\python.exe" installer\preflight_packaging.py
if errorlevel 1 goto :fail

echo [6/7] Uygulama derleniyor...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean installer\AI_Director.spec
if errorlevel 1 goto :fail

if not exist "dist\AI_Director\AI_Director.exe" (
  echo [HATA] EXE olusturulamadi.
  goto :fail
)

echo [7/7] Yerel AI runtime Setup.exe icine gomuluyor...
if exist "dist\AI_Director\models" rmdir /s /q "dist\AI_Director\models"
if exist "dist\AI_Director\runtime" rmdir /s /q "dist\AI_Director\runtime"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File installer\stage_ai_runtime.ps1 -StageDir "dist\AI_Director"
if errorlevel 1 goto :fail

echo [8/8] Sadece Setup.exe paketleniyor...
where ISCC >nul 2>nul
if errorlevel 1 (
  echo [HATA] Inno Setup Compiler (ISCC.exe) bulunamadi.
  echo GitHub Actions runner'inda Inno Setup kurulu olmalidir.
  goto :fail
)
ISCC /Qp installer\AI_Director.iss
if errorlevel 1 goto :fail

if not exist "dist\installer\AI_Director_Setup.exe" (
  echo [HATA] Setup.exe olusturulamadi.
  goto :fail
)

rem Distribution contract: GitHub'a/son kullaniciya portable klasor degil, sadece Setup.exe verilir.
if exist "dist\AI_Director" rmdir /s /q "dist\AI_Director"
if exist "dist\AI_Director_Setup.exe" del /q "dist\AI_Director_Setup.exe"
move /Y "dist\installer\AI_Director_Setup.exe" "dist\AI_Director_Setup.exe" >nul
if errorlevel 1 goto :fail
if exist "dist\installer" rmdir /s /q "dist\installer"
if exist "dist\AI_Director" rmdir /s /q "dist\AI_Director"
if exist "build" rmdir /s /q "build"

rem Final distribution contract: release root contains exactly one deliverable.
for /f %%N in ('dir /b /a-d "dist" 2^>nul ^| find /c /v ""') do set DIST_FILE_COUNT=%%N
if not "%DIST_FILE_COUNT%"=="1" goto :distribution_fail
if not exist "dist\AI_Director_Setup.exe" goto :distribution_fail

echo.
echo [8/8] BASARILI: dist\AI_Director_Setup.exe
echo Kurulum hedefi: Program Files\AI Director
echo Windows Apps/Programs and Features altindan kaldirilabilir.
if "%CI_MODE%"=="0" pause
exit /b 0

:distribution_fail
echo.
echo [HATA] dist klasoru yalnızca AI_Director_Setup.exe icermelidir.
dir /b /a "dist"
if "%CI_MODE%"=="0" pause
exit /b 1

:fail
if exist "app\youtube\build_config.py" del /q "app\youtube\build_config.py"
echo.
echo [HATA] Windows Setup build basarisiz.
if "%CI_MODE%"=="0" pause
exit /b 1
