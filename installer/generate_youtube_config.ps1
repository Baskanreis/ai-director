$ErrorActionPreference = 'Stop'
$path = Join-Path (Split-Path -Parent $PSScriptRoot) 'app\youtube\build_config.py'
$key = [string]$env:YOUTUBE_API_KEY
$b64 = [string]$env:YOUTUBE_OAUTH_CLIENT_JSON_B64
$json = ''
if ($b64) {
  $json = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
  $null = ConvertFrom-Json $json
}
function PyQuote([string]$x) { return '"' + $x.Replace('\\','\\').Replace('"','\"').Replace("`r",'').Replace("`n",'\n') + '"' }
$content = @"
# Generated at build time. Do not commit this file or its secrets.
YOUTUBE_API_KEY = $(PyQuote $key)
OAUTH_CLIENT_JSON = $(PyQuote $json)
"@
Set-Content -Path $path -Value $content -Encoding UTF8
