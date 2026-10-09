$ErrorActionPreference = 'Stop'
$AppDir = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $AppDir 'runtime\llama'
$ModelDir = Join-Path $AppDir 'models\llm'
$WhisperDir = Join-Path $AppDir 'models\whisper'
New-Item -ItemType Directory -Force -Path $RuntimeDir,$ModelDir,$WhisperDir | Out-Null

function Download-File([string]$Url, [string]$OutFile) {
    if (Test-Path $OutFile) { return }
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

# Whisper Base — balanced Turkish accuracy / startup / CPU cost.
$whisperUrl = 'https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt'
$whisperFile = Join-Path $WhisperDir 'base.pt'
try {
    Download-File $whisperUrl $whisperFile
    $hash = (Get-FileHash $whisperFile -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne 'ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e') {
        throw 'Whisper base model SHA256 doğrulaması başarısız.'
    }
} catch {
    Write-Warning "Whisper modeli kurulamadı: $($_.Exception.Message)"
}

# Qwen3 1.7B Q4_K_M — compact local agent LLM (~1.3 GB).
$qwenUrl = 'https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf'
$qwenFile = Join-Path $ModelDir 'Qwen3-1.7B-Q4_K_M.gguf'
try {
    Download-File $qwenUrl $qwenFile
} catch {
    Write-Warning "Yerel Qwen modeli kurulamadı: $($_.Exception.Message)"
}

# Latest official llama.cpp Windows x64 runtime. NVIDIA systems get CUDA 12;
# other systems get CPU so the application remains installable everywhere.
try {
    $headers = @{ 'User-Agent' = 'AI-Director-Setup' }
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest' -Headers $headers
    $hasNvidia = $false
    try { & nvidia-smi.exe -L *> $null; $hasNvidia = ($LASTEXITCODE -eq 0) } catch { $hasNvidia = $false }
    if ($hasNvidia) {
        $asset = $release.assets | Where-Object { $_.name -match 'win.*x64.*cuda.*\.zip$' } | Select-Object -First 1
    } else {
        $asset = $release.assets | Where-Object { $_.name -match 'win.*x64.*cpu.*\.zip$' } | Select-Object -First 1
    }
    if (-not $asset) {
        $asset = $release.assets | Where-Object { $_.name -match 'win.*x64.*\.zip$' } | Select-Object -First 1
    }
    if (-not $asset) { throw 'Uygun Windows llama.cpp paketi bulunamadı.' }
    $zip = Join-Path $env:TEMP $asset.name
    Download-File $asset.browser_download_url $zip
    $extract = Join-Path $env:TEMP ('ai_director_llama_' + [guid]::NewGuid().ToString('N'))
    Expand-Archive -Path $zip -DestinationPath $extract -Force
    $server = Get-ChildItem $extract -Filter 'llama-server.exe' -Recurse | Select-Object -First 1
    if (-not $server) { throw 'llama-server.exe arşivde bulunamadı.' }
    Copy-Item $server.FullName (Join-Path $RuntimeDir 'llama-server.exe') -Force
    Get-ChildItem $server.Directory.FullName -File | Where-Object { $_.Extension -in '.dll','.exe' -and $_.Name -ne 'llama-server.exe' } | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $RuntimeDir $_.Name) -Force
    }
    Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
} catch {
    Write-Warning "llama.cpp runtime kurulamadı: $($_.Exception.Message)"
}

# Required runtime contract: a successful Setup must leave every bundled AI component ready.
$missing = @()
if (-not (Test-Path $whisperFile)) { $missing += 'Whisper Base model' }
if (-not (Test-Path $qwenFile)) { $missing += 'Qwen local model' }
if (-not (Test-Path (Join-Path $RuntimeDir 'llama-server.exe'))) { $missing += 'llama.cpp runtime' }
if ($missing.Count -gt 0) {
    throw ('AI runtime kurulumu tamamlanamadı: ' + ($missing -join ', ') + '. İnternet bağlantısını kontrol edip Setup.exe''yi tekrar çalıştırın.')
}

# Marker is used by the app/system check and by future updates to avoid repeated work.
$marker = [ordered]@{
    installed = (Get-Date).ToString('o')
    whisper = (Test-Path $whisperFile)
    qwen = (Test-Path $qwenFile)
    llama = (Test-Path (Join-Path $RuntimeDir 'llama-server.exe'))
}
$marker | ConvertTo-Json | Set-Content (Join-Path $AppDir 'runtime\ai_runtime_status.json') -Encoding UTF8
Write-Host 'AI runtime setup complete.'
exit 0
