# Private DLSS package (cloud-built, personal use)

The public test workflow (`.github/workflows/windows-dlss-test.yml`) builds an
NVIDIA-free host ZIP. Its `tools/win/Complete-DLSS.ps1` finishes DLSS locally,
which needs CMake and Visual Studio 2022 C++ Build Tools. This note describes
the alternative that needs neither: a separate **private** repository,
`Jal3223/bbhost-dlss-nvidia-addon`, builds the NGX bridge on a standard
GitHub-hosted `windows-2022` runner and returns a complete package that only
its owner can download.

The public workflow, its packaging allowlist and its reviewed sources are
unchanged. This file is not part of the public ZIP.

## Licensing boundary

| Component | Contains NVIDIA code | Public repository | Private repository |
| --- | --- | --- | --- |
| Host, plugins, Vulkan loader, bridge sources | No | Built and published | Downloaded from the public run, verified |
| `ngx_bridge.dll`, `ngx_probe.exe` | Yes, statically links `nvsdk_ngx_s.lib` | Compile-check only, never uploaded | Built, private artifact |
| `nvngx_dlss.dll`, `nvngx_dlssg.dll` | NVIDIA binaries | Never fetched | Signature-checked, private artifact |

Relevant terms of NVIDIA's
[RTX SDK license](https://github.com/NVIDIA/DLSS/blob/374959484e79a640feaba44c93ac8cfb0a03f5b5/LICENSE.txt)
(v. March 14, 2024):

- §1a grants the right to install and use the SDK. A private build for the
  licensee's own PC uses that grant and distributes nothing.
- §1c and §2 allow distribution only inside an application, under terms at
  least as protective as NVIDIA's. §4e forbids making the SDK subject to an
  open-source license. bbhost is GPLv3 without an NVIDIA linking exception, so
  NVIDIA-linked files are never published from either repository.
- Artifacts of a public repository are downloadable by any signed-in GitHub
  user, so a public upload would be distribution. Private-repository artifacts
  are limited to accounts with access to that repository. Keep it private and
  without collaborators. GPLv3 §2 likewise permits making and running copies
  that are not conveyed.
- Supplement §1 limits the DLSS/NGX SDKs to systems with NVIDIA GPUs.
- Supplement §3 places "cloud service use of such SDKs or their functionality"
  outside the license, defining cloud services as hosting or providing services
  to others. This setup reads it as covering DLSS running as a hosted service.
  Compiling on a CI runner for one's own PC is a different activity, and the
  public compile-check job already relies on the same reading. For written
  confirmation, NVIDIA's license contact is nvidia-rtx-license-questions@nvidia.com.

This is a project policy, not legal advice.

## Using it

1. Run the public **Unofficial Windows DLSS test build**. The NVIDIA checkboxes
   are optional.
2. In the private repository, run **Private DLSS complete package (personal use
   only)** with the license box ticked.
3. Download `bbhost-dlss-complete-<commit>` and extract it into the game folder.
   Double-click `Test-DLSS.bat`.

The private workflow checks out this repository at the public run's commit. It
refuses to build unless `tools/ngx_bridge` matches one of its reviewed bridge
commits (`1e82fac`, `1c83fde`). `tools/win/Build-NGX.ps1`,
`tools/win/Test-DLSS-Install.ps1`, `tools/win/Install-FSR4.ps1` and
`tools/ci/check_test_build.py` must match one of its reviewed script commits
(`4e465ff`, `08c1c89`). A deliberate change to those files therefore also needs a
reviewed commit added in the private workflow. It also preinstalls AMD's
MIT-licensed FSR 4 v07 INT8 assets, checked against their published SHA-256
manifests. It requires every bridge function the host source resolves, and runs
the bridge's GPU-free transfer-dependency contract test.
