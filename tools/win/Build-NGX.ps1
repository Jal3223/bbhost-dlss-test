param(
    [Parameter(Mandatory=$true)][string]$DlssSdkDir,
    [Parameter(Mandatory=$true)][string]$VulkanHeadersDir,
    [string]$OutputDir = (Join-Path $PSScriptRoot '../..')
)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path (Join-Path $PSScriptRoot '../ngx_bridge')).Path
$sdk = (Resolve-Path $DlssSdkDir).Path
$headers = (Resolve-Path $VulkanHeadersDir).Path
if (-not (Test-Path "$sdk/include/nvsdk_ngx_helpers_dlssg_vk.h")) { throw 'This SDK lacks Vulkan DLSS frame generation headers.' }
if (-not (Test-Path "$sdk/lib/Windows_x86_64/x64/nvsdk_ngx_s.lib")) { throw 'Missing Windows x64 static NGX library.' }
$build = Join-Path $env:TEMP ('bbhost-ngx-' + [Guid]::NewGuid().ToString('N'))
cmake -S $source -B $build -G 'Visual Studio 17 2022' -A x64 "-DDLSS_SDK_DIR=$sdk" "-DVULKAN_HEADERS_DIR=$headers"
if ($LASTEXITCODE -ne 0) { throw 'Bridge configure failed.' }
cmake --build $build --config Release --parallel 2
if ($LASTEXITCODE -ne 0) { throw 'Bridge build failed.' }
New-Item -ItemType Directory -Force $OutputDir | Out-Null
Copy-Item "$build/Release/ngx_bridge.dll" $OutputDir
Copy-Item "$build/Release/ngx_probe.exe" $OutputDir
Write-Output "Bridge and probe built locally in $OutputDir. Add your licensed nvngx_dlss.dll and nvngx_dlssg.dll beside bbhost.exe."
Write-Output "Temporary build directory: $build. No SDK or runtime files were copied to the package."
