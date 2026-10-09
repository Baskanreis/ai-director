param([string]$StageDir)
$ErrorActionPreference = 'Stop'

if (-not $StageDir) { throw 'StageDir belirtilmedi.' }
$StageDir = (Resolve-Path $StageDir).Path
$ModelDir = Join-Path $StageDir 'models\llm'
$WhisperDir = Join-Path $StageDir 'models\whisper'
$RuntimeDir = Join-Path $StageDir 'runtime\llama'
$FfmpegDir = Join-Path $StageDir 'runtime\ffmpeg'
New-Item -ItemType Directory -Force -Path $FfmpegDir | Out-Null
New-Item -ItemType Directory -Force -Path $ModelDir,$WhisperDir,$RuntimeDir | Out-Null

function Download-File([string]$Url, [string]$OutFile) {
  if (Test-Path $OutFile) { return }
  Write-Host "Downloading $Url"
  Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}


# Bundle a full Windows FFmpeg build so ffmpeg AND ffprobe are available to every feature.
$ffmpegZip = Join-Path $env:TEMP ('ai_director_ffmpeg_' + [guid]::NewGuid().ToString('N') + '.zip')
$ffmpegUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
Download-File $ffmpegUrl $ffmpegZip
$ffmpegExtract = Join-Path $env:TEMP ('ai_director_ffmpeg_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtract -Force
$ffmpegExe = Get-ChildItem $ffmpegExtract -Filter 'ffmpeg.exe' -Recurse | Select-Object -First 1
$ffprobeExe = Get-ChildItem $ffmpegExtract -Filter 'ffprobe.exe' -Recurse | Select-Object -First 1
if (-not $ffmpegExe -or -not $ffprobeExe) { throw 'FFmpeg/FFprobe bulunamadı.' }
Copy-Item $ffmpegExe.FullName (Join-Path $FfmpegDir 'ffmpeg.exe') -Force
Copy-Item $ffprobeExe.FullName (Join-Path $FfmpegDir 'ffprobe.exe') -Force
& (Join-Path $FfmpegDir 'ffmpeg.exe') -version | Out-Null
& (Join-Path $FfmpegDir 'ffprobe.exe') -version | Out-Null
Remove-Item $ffmpegExtract,$ffmpegZip -Recurse -Force -ErrorAction SilentlyContinue

$whisperUrl = 'https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt'
$whisperFile = Join-Path $WhisperDir 'base.pt'
Download-File $whisperUrl $whisperFile
$hash = (Get-FileHash $whisperFile -Algorithm SHA256).Hash.ToLower()
if ($hash -ne 'ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e') { throw 'Whisper Base SHA256 doğrulaması başarısız.' }

$qwenUrl = 'https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf'
$qwenFile = Join-Path $ModelDir 'Qwen3-1.7B-Q4_K_M.gguf'
Download-File $qwenUrl $qwenFile

$headers = @{ 'User-Agent' = 'AI-Director-Build' }
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest' -Headers $headers
$asset = $release.assets | Where-Object { $_.name -match 'win.*x64.*cpu.*\.zip$' } | Select-Object -First 1
if (-not $asset) { $asset = $release.assets | Where-Object { $_.name -match 'win.*x64.*\.zip$' -and $_.name -notmatch 'cuda' } | Select-Object -First 1 }
if (-not $asset) { throw 'Windows x64 llama.cpp CPU paketi bulunamadı.' }
$zip = Join-Path $env:TEMP ('ai_director_' + $asset.name)
Download-File $asset.browser_download_url $zip
$extract = Join-Path $env:TEMP ('ai_director_llama_' + [guid]::NewGuid().ToString('N'))
Expand-Archive -Path $zip -DestinationPath $extract -Force
$server = Get-ChildItem $extract -Filter 'llama-server.exe' -Recurse | Select-Object -First 1
if (-not $server) { throw 'llama-server.exe bulunamadı.' }
Copy-Item $server.FullName (Join-Path $RuntimeDir 'llama-server.exe') -Force
Get-ChildItem $server.Directory.FullName -File | Where-Object { $_.Extension -in '.dll','.exe' -and $_.Name -ne 'llama-server.exe' } | ForEach-Object { Copy-Item $_.FullName (Join-Path $RuntimeDir $_.Name) -Force }
Remove-Item $extract,$zip -Recurse -Force -ErrorAction SilentlyContinue

@{ bundled=$true; ffmpeg=$true; ffprobe=$true; whisper=$true; qwen=$true; llama=$true; built=(Get-Date).ToString('o') } | ConvertTo-Json | Set-Content (Join-Path $StageDir 'runtime\ai_runtime_status.json') -Encoding UTF8
Write-Host 'Bundled AI runtime ready.'
