param(
    [switch]$AcceptNvidiaLicense,
    [string]$DlssSdkDir,
    [string]$VulkanHeadersDir
)
$ErrorActionPreference = 'Stop'
$license = 'https://github.com/NVIDIA/DLSS/blob/374959484e79a640feaba44c93ac8cfb0a03f5b5/LICENSE.txt'
if (-not $AcceptNvidiaLicense) {
    throw "Read and accept NVIDIA's RTX SDK license at $license, then rerun with -AcceptNvidiaLicense. This script makes no acceptance on your behalf."
}
if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) { throw 'Install CMake and Visual Studio 2022 C++ Build Tools (Desktop development with C++), then rerun.' }
$package = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not (Test-Path (Join-Path $package 'bbhost.exe'))) { throw 'Run this helper from the extracted Windows package.' }
$work = Join-Path $env:TEMP ('bbhost-dlss-local-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $work | Out-Null
function Get-PinnedSource([string]$Repo, [string]$Commit, [string]$Name) {
    $archive = Join-Path $work "$Name.zip"
    Invoke-WebRequest "https://github.com/$Repo/archive/$Commit.zip" -OutFile $archive
    $dest = Join-Path $work $Name
    Expand-Archive $archive -DestinationPath $dest
    $dirs = @(Get-ChildItem $dest -Directory)
    if ($dirs.Count -ne 1) { throw "Unexpected source archive layout for $Repo" }
    return $dirs[0].FullName
}
try {
    if (-not $DlssSdkDir) { $DlssSdkDir = Get-PinnedSource 'NVIDIA/DLSS' '374959484e79a640feaba44c93ac8cfb0a03f5b5' 'dlss' }
    if (-not $VulkanHeadersDir) { $VulkanHeadersDir = Get-PinnedSource 'KhronosGroup/Vulkan-Headers' '8864cdc896bbc2a9b6eb36b3218fc9ef57908d77' 'vulkan-headers' }
    $sdk = (Resolve-Path $DlssSdkDir).Path
    foreach ($runtime in @('nvngx_dlss.dll', 'nvngx_dlssg.dll')) {
        $file = Join-Path $sdk "lib/Windows_x86_64/rel/$runtime"
        if (-not (Test-Path $file)) { throw "Missing release runtime $file. Use the official SDK, not game files or debug DLLs." }
        $signature = Get-AuthenticodeSignature $file
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'NVIDIA') { throw "Runtime signature is not valid NVIDIA: $runtime" }
    }
    & (Join-Path $PSScriptRoot 'Build-NGX.ps1') -DlssSdkDir $sdk -VulkanHeadersDir $VulkanHeadersDir -OutputDir $package
    foreach ($runtime in @('nvngx_dlss.dll', 'nvngx_dlssg.dll')) {
        Copy-Item (Join-Path $sdk "lib/Windows_x86_64/rel/$runtime") $package
    }
    New-Item -ItemType Directory -Force (Join-Path $package 'licenses/nvidia-local') | Out-Null
    Copy-Item (Join-Path $sdk 'LICENSE.txt') (Join-Path $package 'licenses/nvidia-local/LICENSE.txt')
    & (Join-Path $PSScriptRoot 'Test-DLSS-Install.ps1')
    Write-Output 'Local DLSS components installed. Do not upload this completed folder or include its NVIDIA files in public artifacts.'
} finally {
    if (Test-Path $work) { Remove-Item $work -Recurse -Force }
}
