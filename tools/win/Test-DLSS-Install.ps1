param([switch]$Gpu)
$ErrorActionPreference = 'Stop'
$package = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
foreach ($name in @('bbhost.exe', 'vulkan-1.dll', 'ngx_bridge.dll', 'ngx_probe.exe', 'nvngx_dlss.dll', 'nvngx_dlssg.dll')) {
    if (-not (Test-Path (Join-Path $package $name))) { throw "Missing $name. Run Complete-DLSS.ps1 to build/install the NVIDIA components locally." }
}
foreach ($name in @('nvngx_dlss.dll', 'nvngx_dlssg.dll')) {
    $signature = Get-AuthenticodeSignature (Join-Path $package $name)
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'NVIDIA') { throw "Invalid NVIDIA runtime signature: $name" }
}
Push-Location $package
try {
    if ($Gpu) { & './ngx_probe.exe' gpu } else { & './ngx_probe.exe' }
    $code = $LASTEXITCODE
    if ($code -eq 77) { throw 'Probe skipped: a suitable NVIDIA Vulkan GPU/driver is unavailable.' }
    if ($code -ne 0) { throw "NGX probe failed ($code). Inspect logs/ngx and the probe output before enabling DLSS/FG." }
    Write-Output 'NGX probe passed. Restart bbhost after selecting Quality / DLSS frame generation 2x in Setup or F10.'
} finally { Pop-Location }
