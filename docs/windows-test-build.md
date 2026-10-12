# Unofficial Windows DLSS / Frame Generation test build

This fork is a personal test workspace, separate from the official
`droogie/bbhost` project and from Flocker's development repository. No upstream
pull request, release, signing key, or announcement is part of this setup.

## Reviewed source

- Experimental repository: `FIocker/bbhost` (the second character is a capital I).
- Branch: `render/dlss-sr-framegen-pipeline`.
- Flocker's branch head: `539d45f41e1692379a130d69ff79dca3a900513d` (pull request droogie/bbhost#73),
  rebased onto upstream `566184a`, which includes droogie/bbhost#116.
- Added on top, unchanged except for one mechanical CMake test-registration merge:
  droogie/bbhost#117 (dispatch-trace memory growth), #74 (Windows native certificate
  trust for curl) and #70 (Windows chromatic dispersion stub).
- Reviewed integration commit: `c56fcde4af6af2f7b917b58cdec8c4d7201b91b7` (branch
  `experiment/dlss-fg-rtx40-2026-10-12`).
- Excluded: droogie/bbhost#122 (PC settings performance). It conflicts with the DLSS
  branch's settings code and needs a hand merge of the settings concurrency model.
- Earlier reviewed commits stay buildable: `1c83fde` on `claude/ngx-bridge-github-actions-0jpazr`,
  and `1e82fac` on `dlss-windows-test`.
- The fork's `dlss-windows-test` branch adds only CI, packaging, and documentation.
- The pre-build check rejects changes to reviewed host/renderer/bridge sources.

## Build configuration reviewed before the first run

| Setting | Value |
| --- | --- |
| Trigger | Manual `workflow_dispatch` only |
| Repository | Public `Jal3223/bbhost-dlss-test`; guarded against upstream execution |
| Host compilation | Standard `ubuntu-24.04` runner, official Arch Linux container, Clang/mingw-w64 |
| Windows verification | Standard `windows-2022` runner; four existing CPU tests and no-game startup |
| Vulkan loader | Open-source loader `v1.4.350`, commit `a9e72c66d5cb79911eb9a9063bf4016dd0a3a123`, MSVC static CRT |
| Build type | RelWithDebInfo; `BBHOST_RELEASE=OFF`; 2 compiler jobs |
| Permissions | `contents: read`; checkout credentials removed |
| Actions | Checkout, upload, and download pinned to full commit SHAs |
| FSR provider | Existing source pin `c64f093404125e960813f95f1996c14780f0dd69` |
| Host dependencies | zlib 1.3.1, SDL 3.4.16, curl 8.22.0, FFmpeg 7.1.1 via reviewed upstream script |
| Artifact | Allowlisted Windows host/plugins/tests/loader, public bridge source and completion helpers, corresponding host/dependency source archives, ZIP contents/import audit/checksums |
| NVIDIA publication | No SDK headers, libraries, runtime DLLs, or SDK-linked bridge binaries uploaded/cached |
| Retention / limits | Artifacts 3 days; host 90 minutes; Windows tests 15 minutes; optional NGX check 20 minutes |
| Releases / upstream | Inherited workflows archived; no release or upstream PR |

Standard hosted runner compute is free for public repositories under GitHub's
current policy. Short artifact retention limits storage use; it is not a
promise of zero artifact-storage charges. No larger, GPU, or paid runner is used.
The Arch container and distribution packages follow their maintained repositories;
record the versions from the run log rather than claiming bit-for-bit reproducibility.

## Run and download

Open this fork's Actions tab, choose **Unofficial Windows DLSS test build**, and
select **Run workflow** on `dlss-windows-test`. Leave both optional NVIDIA
checkboxes off for the normal host build. Download this run's
`unofficial-windows-test-<commit>` artifact after both host and Windows
verification succeed. The intermediate `host-components` artifact is for CI;
use the final `unofficial-windows-test` artifact. Check `SHA256SUMS`, then extract
`bbhost-dlss-test-windows.zip` directly into `F:\ShadPS4\Port3`. Files are at the
ZIP root, with no extra containing folder. Back up any existing installation
before replacing files. The host and dependency source TARs accompany the build.
`ZIP-CONTENTS.txt` lists each ZIP entry and `PACKAGE-AUDIT.json` records hashes,
x64 PE imports, and the remaining manual requirements. CI verifies ZIP CRCs and
each archived file's hash after sealing the final ZIP.

## Enable DLSS / Frame Generation locally

The host includes the experimental DLSS pipeline, but NVIDIA code is deliberately
excluded from its public download. It needs a version-2 `ngx_bridge.dll`,
`nvngx_dlss.dll` and `nvngx_dlssg.dll` beside `bbhost.exe` to run DLSS/FG.
Without them, the host renders through its ordinary fallback path.

NVIDIA's [RTX SDK license](https://github.com/NVIDIA/DLSS/blob/374959484e79a640feaba44c93ac8cfb0a03f5b5/LICENSE.txt)
permits conditional object-code redistribution, requires protective downstream
terms, and restricts making SDK code subject to an open-source license. This
repository's GPLv3 license has no established NVIDIA linking exception. A public
SDK-linked bridge/runtime bundle has therefore not been approved here; publishing
one requires resolving those distribution terms with the rights holders. Public
availability on GitHub is not by itself permission to relicense SDK components.

For personal local use, read NVIDIA's license first. Install CMake and Visual
Studio 2022 C++ Build Tools with **Desktop development with C++**, then run:

```powershell
cd F:\ShadPS4\Port3
./tools/win/Complete-DLSS.ps1 -AcceptNvidiaLicense
```

This downloads official pinned SDK and Vulkan headers to temporary local storage,
builds `ngx_bridge.dll` and `ngx_probe.exe`, checks the two release runtime DLLs'
NVIDIA Authenticode signatures, and copies them beside the host. It also preserves
the NVIDIA license locally, deletes downloaded temporary sources, and runs the
capability probe. No game files are downloaded. Do not upload this locally
completed folder. A modern NVIDIA driver and a GPU supporting the requested
NGX SR/FG features are still required; the probe reports actual capabilities.

You can instead use your own licensed NVIDIA DLSS SDK (pinned compile-check target NVIDIA/DLSS
commit `374959484e79a640feaba44c93ac8cfb0a03f5b5`) and Vulkan-Headers
`v1.4.350` (`8864cdc896bbc2a9b6eb36b3218fc9ef57908d77`). The public bridge
sources and `tools/win/Build-NGX.ps1` are included in the test ZIP. With CMake
and Microsoft's Visual Studio 2022 C++ Build Tools installed on Windows:

```powershell
./tools/win/Build-NGX.ps1 -DlssSdkDir C:/SDKs/DLSS -VulkanHeadersDir C:/SDKs/Vulkan-Headers
```

The lower-level script builds only the bridge and probe locally and copies them beside the
host. Obtain the two release NVIDIA runtime DLLs from your licensed SDK's
`lib/Windows_x86_64/rel` directory yourself. Do not commit or upload them.
Run `./ngx_probe.exe` and then `./ngx_probe.exe gpu` on the RTX computer to
check capability and synthetic reconstruction/interpolation.

After local completion, `./tools/win/Test-DLSS-Install.ps1 -Gpu` checks required
files, NVIDIA signatures, and runs Flocker's synthetic GPU fixture. A skip or
failure is reported as a failure, rather than claiming verified DLSS support.
Select the **DLSS** reconstruction/frame-generation backends in Setup/F10,
Quality mode, and normal 2x generation; restart after changing temporal settings.

### What you must still supply

| Component | Public ZIP | Local requirement |
| --- | --- | --- |
| Experimental host, plugins, patches, configuration example | Included | Your existing settings/game paths remain personal |
| Vulkan loader | Built and included | NVIDIA graphics driver supplies the actual GPU implementation |
| NGX bridge and probe | Matching public sources and build scripts included | CMake, VS 2022 C++ Build Tools; completion script builds binaries locally |
| DLSS SR and FG runtime DLLs | Excluded | NVIDIA license acceptance; completion script gets signed release files from official SDK |
| NVIDIA SDK headers/static library | Excluded | Temporarily downloaded locally for bridge build; no manual SDK copying required |
| Game files, decrypted executable, DLC and saves | Excluded | Supply your own lawful files through bbhost Setup; back up saves |

The optional Actions NGX job compile-checks the bridge and probe using MSVC.
It requires both explicit checkboxes, fetches pinned SDK headers and one library
only into temporary job storage, and publishes no resulting binaries. It does
not provide a downloadable bridge or run GPU tests.

Back up saves before testing. This build still uses bbhost's normal per-user
configuration/save locations even when extracted to a separate folder.
Start with Quality reconstruction and Off/2x generation, restart after changing
temporal settings, and keep simulation at 60 FPS for multiplayer compatibility.
3x/4x remain experimental and are not enabled by this workflow. Native Vulkan
Reflex (`VK_NV_low_latency2`) is integrated and defaults to On; see `docs/reflex.md`.
Cloud compilation and CPU tests do not verify gameplay, DLSS image quality,
frame pacing on your monitor, or input latency. See `docs/dlss-development.md`.
