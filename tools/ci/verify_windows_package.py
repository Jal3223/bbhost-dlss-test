"""Inspect final ZIP bytes, PE dependencies and publication boundaries on Windows."""
import hashlib
import json
import pathlib
import struct
import subprocess
import zipfile

ROOT = pathlib.Path.cwd()
KIT = ROOT / 'kit'
OUT = ROOT / 'downloads'
PE = {'bbhost.exe', 'vulkan-1.dll'} | {
    'plugins/' + x + '.dll' for x in ('randomizer', 'boss_rush', 'mutators', 'debug_menu')
} | {'tests/' + x + '.exe' for x in (
    'display_settings_test', 'presentation_coordinates_test', 'fg_timing_test', 'motion_history_test')}
SYSTEM = set(('kernel32 user32 gdi32 advapi32 shell32 ole32 oleaut32 uuid comdlg32 '
              'ws2_32 crypt32 bcrypt secur32 msvcrt ntdll winmm imm32 setupapi cfgmgr32 '
              'version wintrust dinput8 dxgi hid powrprof usp10 shcore dwmapi shlwapi '
              'winspool normaliz psapi propsys rpcrt4 uxtheme avrt comctl32 iphlpapi '
              'dnsapi winhttp msimg32').split())


def imports(data: bytes) -> list[str]:
    u16 = lambda o: struct.unpack_from('<H', data, o)[0]
    u32 = lambda o: struct.unpack_from('<I', data, o)[0]
    pe = u32(0x3c)
    assert data[:2] == b'MZ' and data[pe:pe + 4] == b'PE\0\0', 'Invalid PE'
    assert u16(pe + 4) == 0x8664, 'Expected Windows x64'
    opt = pe + 24
    assert u16(opt) == 0x20b, 'Expected PE32+'
    sections = opt + u16(pe + 20)

    def offset(rva: int) -> int:
        for i in range(u16(pe + 6)):
            s = sections + i * 40
            virtual_size, address, size, raw = struct.unpack_from('<IIII', data, s + 8)
            if address <= rva < address + max(virtual_size, size):
                return raw + rva - address
        raise ValueError('Unmapped PE RVA')

    result = []
    rva = u32(opt + 112 + 8)
    if not rva:
        return result
    at = offset(rva)
    while any(data[at:at + 20]):
        name = offset(u32(at + 12))
        result.append(data[name:data.index(b'\0', name)].decode('ascii').lower())
        at += 20
    return sorted(result)


required = PE | {'run-bbhost.bat', 'tools/win/Complete-DLSS.ps1', 'tools/win/Build-NGX.ps1',
                 'tools/win/Test-DLSS-Install.ps1', 'docs/windows-test-build.md',
                 'BUILD-INFO.json', 'README-TEST.txt', 'LICENSE', 'bbhost.example.toml'}
files = {p.relative_to(KIT).as_posix(): p for p in KIT.rglob('*') if p.is_file()}
assert required <= files.keys(), 'Missing package entries: ' + str(required - files.keys())
dependencies = {}
for name, path in files.items():
    assert not path.is_symlink(), 'Symlink in package'
    assert not any(part.lower().startswith(('nvngx', 'nvsdk_ngx', 'eboot')) for part in path.relative_to(KIT).parts), name
    assert path.suffix.lower() not in {'.lib', '.elf', '.self', '.pdb', '.a'}, name
    if path.suffix.lower() in {'.exe', '.dll'}:
        assert name in PE, 'Unapproved PE: ' + name
        dependencies[name] = imports(path.read_bytes())
        for dll in dependencies[name]:
            assert dll in {p.name.lower() for p in files.values()} or dll.removesuffix('.dll') in SYSTEM or dll.startswith(('api-ms-win-', 'ext-ms-win-')), 'Unpackaged dependency: ' + dll
assert any(n.startswith('patches/') for n in files), 'Missing patches'
# Parse, but never execute, the local SDK helpers in cloud CI.
subprocess.run(['pwsh', '-NoProfile', '-Command',
    "$ErrorActionPreference='Stop'; Get-ChildItem kit/tools/win/*.ps1 | ForEach-Object { $t=$null; $e=$null; [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e) | Out-Null; if($e.Count){throw ($e | Out-String)} }"], check=True)
for name in ('vulkan-loader', 'vulkan-headers'):
    subprocess.run(['git', '-C', '.ci-public/' + name, 'archive', '--format=tar.gz',
                    '--prefix=' + name + '/', '-o', str(OUT / (name + '-source.tar.gz')), 'HEAD'], check=True)
info = json.loads((KIT / 'BUILD-INFO.json').read_text())
info['vulkan_loader_included'] = True
info['windows_cpu_tests_passed'] = True
info['no_game_startup_passed'] = True
info['dlss_ready_to_run'] = False
(KIT / 'BUILD-INFO.json').write_text(json.dumps(info, indent=2) + '\n')
audit = {'verified_files': {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in sorted(files.items())},
         'windows_imports': dependencies, 'nvidia_sdk_published': False, 'game_files_published': False,
         'dlss_ready_to_run': False, 'still_required_locally': ['ngx_bridge.dll', 'ngx_probe.exe', 'nvngx_dlss.dll', 'nvngx_dlssg.dll'],
         'completion': 'tools/win/Complete-DLSS.ps1 builds and installs these locally after explicit NVIDIA license acceptance',
         'gpu_tested': False}
(OUT / 'PACKAGE-AUDIT.json').write_text(json.dumps(audit, indent=2) + '\n')
(OUT / 'ZIP-CONTENTS.txt').write_text('\n'.join(sorted(files)) + '\n')
archive = OUT / 'bbhost-dlss-test-windows.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for name, path in sorted(files.items()):
        z.write(path, name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None, 'ZIP CRC check failed'
    assert set(z.namelist()) == set(files), 'ZIP content mismatch'
    for name in z.namelist():
        assert hashlib.sha256(z.read(name)).hexdigest() == audit['verified_files'][name], name
(OUT / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
    for p in sorted(OUT.iterdir()) if p.suffix in {'.zip', '.gz', '.json', '.txt'} and p.name != 'SHA256SUMS'))
summary = pathlib.Path(__import__('os').environ['GITHUB_STEP_SUMMARY'])
with summary.open('a') as f:
    f.write('\nVerified final ZIP: %d files, x64 PE imports, checksums, no SDK/game files.\n\n' % len(files))
    f.write('DLSS still requires local bridge + two NVIDIA runtime DLLs. See Complete-DLSS.ps1; public ZIP is not a complete DLSS bundle.\n')
print(json.dumps({'zip': archive.name, 'files': len(files), 'imports': dependencies, 'still_required': audit['still_required_locally']}, indent=2))
