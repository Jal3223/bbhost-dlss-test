#!/usr/bin/env python3
"""Allowlisted unofficial host package. Never package SDKs or NGX-linked outputs."""
import hashlib
import json
import pathlib
import shutil
import subprocess
import tarfile
import zipfile

from check_test_build import BASE, ROOT, check

check()
dist = ROOT / 'dist'
stage = ROOT / 'build' / 'test-package'
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
dist.mkdir(exist_ok=True)


def copy(source: str, destination: str | None = None) -> None:
    target = stage / (destination or source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / source, target)


subprocess.run(['llvm-objcopy', '--strip-debug', str(ROOT / 'build-win/bbhost.exe'), str(stage / 'bbhost.exe')], check=True)
for name in ['randomizer', 'boss_rush', 'mutators', 'debug_menu']:
    target = stage / 'plugins' / (name + '.dll')
    target.parent.mkdir(exist_ok=True)
    subprocess.run(['llvm-objcopy', '--strip-debug', str(ROOT / 'build-win/plugins' / target.name), str(target)], check=True)
for name in ['display_settings_test', 'presentation_coordinates_test', 'fg_timing_test', 'motion_history_test',
             'chromatic_stub_test', 'ngx_transfer_sync_test']:
    copy('build-win/' + name + '.exe', 'tests/' + name + '.exe')
for name in ['LICENSE', 'LICENSE-FSR.txt', 'bbhost.example.toml', 'docs/dlaa.md',
             'docs/dlss-development.md', 'docs/windows-test-build.md', 'docs/running.md',
             'tools/win/run-bbhost.bat', 'tools/win/Build-NGX.ps1', 'tools/win/Complete-DLSS.ps1',
             'tools/win/Test-DLSS-Install.ps1', 'tools/win/Install-FSR4.ps1',
             'tools/win/Install-FSR4.bat', 'docs/fsr.md', 'docs/reflex.md', 'tools/win/analyze_reflex.py',
             'include/bbhost_plugin.h']:
    copy(name, 'run-bbhost.bat' if name.endswith('/run-bbhost.bat') else None)
shutil.copytree(ROOT / 'patches', stage / 'patches')
# These are the project's bridge sources, not NVIDIA SDK headers/libraries.
for name in ['CMakeLists.txt', 'ngx_bridge.cpp', 'ngx_bridge.h', 'ngx_transfer_sync.h', 'ngx_transfer_sync_test.cpp',
             'ngx_probe.cpp', 'ngx_gpu_test.cpp', 'BBPORT-NOTICE.txt']:
    copy('tools/ngx_bridge/' + name)
for source in (ROOT / 'third_party').rglob('*'):
    if source.is_file() and ('license' in source.name.lower() or 'copying' in source.name.lower()):
        copy(source.relative_to(ROOT).as_posix(), 'licenses/' + source.relative_to(ROOT / 'third_party').as_posix())
for source in (ROOT / 'src/host/shaders/fsr1').rglob('*'):
    if source.is_file() and 'license' in source.name.lower():
        copy(source.relative_to(ROOT).as_posix(), 'licenses/fsr1/' + source.name)
for base, label in [(ROOT / 'build/win-deps/src', 'windows-dependencies'),
                    (ROOT / 'build-win/_deps/fsr_vulkan-src', 'fsr-vulkan')]:
    for source in base.rglob('*'):
        if source.is_file() and source.name.lower().startswith(('license', 'copying', 'copyright')) and '.git' not in source.parts:
            copy(source.relative_to(ROOT).as_posix(), 'licenses/' + label + '/' + source.relative_to(base).as_posix())

sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
manifest = {'repository': 'Jal3223/bbhost-dlss-test', 'commit': sha,
            'experimental_source': 'FIocker/bbhost:render/dlss-sr-framegen-pipeline@539d45f41e1692379a130d69ff79dca3a900513d'
                                   ' + droogie/bbhost#117, #74, #70',
            'reviewed_source_commit': BASE, 'release_build': False,
            'nvidia_sdk_included': False, 'ngx_bridge_binary_included': False,
            'gpu_tested': False}
(stage / 'BUILD-INFO.json').write_text(json.dumps(manifest, indent=2) + '\n')
(stage / 'README-TEST.txt').write_text(
    'UNOFFICIAL BBHOST DLSS / FRAME GENERATION WINDOWS TEST\n'
    'Source fork: https://github.com/Jal3223/bbhost-dlss-test\n'
    'Build commit: ' + sha + '\n'
    'Experimental source commit: ' + BASE + '\n\n'
    'This package includes the experimental host, unsigned plugin builds, CPU tests, and public bridge sources.\n'
    'NVIDIA SDK files, NVIDIA runtime DLLs, and ngx_bridge.dll are deliberately absent.\n'
    'Without a matching version-2 ngx_bridge.dll and NVIDIA runtimes, DLSS/FG remains unavailable.\n'
    'Extract this ZIP directly into F:\\ShadPS4\\Port3 (back up an existing installation first).\n'
    'After reading/accepting NVIDIA terms, tools/win/Complete-DLSS.ps1 downloads official pinned dependencies,\n'
    'builds the bridge/probe and installs the signed release runtime DLLs locally. CMake + VS 2022 C++ Build Tools are required.\n'
    'See docs/windows-test-build.md for the exact command and missing-component checklist.\n'
    'Use a separate folder and back up your saves before gameplay testing.\n'
    'Double-click run-bbhost.bat to set up your own game files. No game files are included.\n'
    'Standard cloud runners validate CPU tests/startup, not DLSS pixels, performance, or latency.\n'
    'Native Vulkan Reflex (VK_NV_low_latency2) is built in: Off / On / On + Boost in Setup or F10, default On.\n'
    'Frame generation offers Off/2x/3x/4x; the driver-reported GPU maximum applies, so RTX 40 runs 2x. See docs/reflex.md.\n')

# The expected PE filenames are explicit; no glob can pick up NVIDIA DLLs.
allowed_pe = {'bbhost.exe'} | {'plugins/' + n + '.dll' for n in ['randomizer', 'boss_rush', 'mutators', 'debug_menu']} | {
    'tests/' + n + '.exe' for n in ['display_settings_test', 'presentation_coordinates_test', 'fg_timing_test', 'motion_history_test',
                                    'chromatic_stub_test', 'ngx_transfer_sync_test']}
for path in stage.rglob('*'):
    if path.is_symlink():
        raise SystemExit('No symlinks may enter the package: ' + str(path))
    if path.is_file():
        rel = path.relative_to(stage).as_posix()
        if path.suffix.lower() in {'.dll', '.exe', '.lib'} and rel not in allowed_pe:
            raise SystemExit('Unapproved binary: ' + rel)
        if path.name.lower().startswith(('nvngx', 'nvsdk_ngx', 'eboot')):
            raise SystemExit('SDK/game file in package: ' + rel)

archive = dist / 'bbhost-dlss-test-windows.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
    for path in sorted(stage.rglob('*')):
        if path.is_file():
            out.write(path, path.relative_to(stage).as_posix())
source_archive = dist / 'bbhost-dlss-test-source.tar.gz'
subprocess.run(['git', 'archive', '--format=tar.gz', '--prefix=bbhost-dlss-test-source/',
                '-o', str(source_archive), 'HEAD'], cwd=ROOT, check=True)
with tarfile.open(source_archive) as source:
    if any(p.name.lower().split('/')[-1].startswith(('nvngx', 'nvsdk_ngx')) or p.name.lower().endswith(('eboot.bin', '.elf', '.self', '.lib')) for p in source.getmembers()):
        raise SystemExit('Source archive contains an SDK/game file')
# Include the preferred source of the libraries linked into the host, rather
# than relying on an external source offer or merely listing version numbers.
fsr_source = dist / 'fsr-vulkan-source.tar.gz'
subprocess.run(['git', '-C', str(ROOT / 'build-win/_deps/fsr_vulkan-src'), 'archive',
                '--format=tar.gz', '--prefix=fsr-vulkan/', '-o', str(fsr_source), 'HEAD'], check=True)
dependency_archive = dist / 'bbhost-dlss-test-dependencies.tar.gz'
with tarfile.open(dependency_archive, 'w:gz') as out:
    for source in sorted((ROOT / 'build/win-deps/src').iterdir()):
        if source.is_file() and source.name.endswith(('.tar.gz', '.tar.xz')):
            out.add(source, arcname=source.name)
    out.add(fsr_source, arcname=fsr_source.name)
fsr_source.unlink()
(dist / 'SHA256SUMS').write_text(''.join(
    hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
    for p in [archive, source_archive, dependency_archive]))
print('Packaged unofficial Windows host and corresponding public source; no NVIDIA binaries.')
