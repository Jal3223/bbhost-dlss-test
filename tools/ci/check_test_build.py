#!/usr/bin/env python3
"""Fail before compilation if the reviewed source or publication boundary changed."""
import pathlib
import re
import subprocess

BASE = '1e82facba1a77afdf75b7cfb3aabb5bfc8c5c380'
ROOT = pathlib.Path(__file__).resolve().parents[2]


def check() -> None:
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--exit-code', BASE, 'HEAD', '--', 'src', 'include', 'cmake',
                    'CMakeLists.txt', 'tests', 'third_party', 'tools/ngx_bridge', 'tools/win_deps.sh'], cwd=ROOT, check=True)
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    forbidden = re.compile(r'(^|/)(nvngx[^/]*|nvsdk_ngx[^/]*|eboot\.bin|dvdroot_ps4)(/|$)|\.(lib|elf|self)$', re.I)
    bad = [p for p in files if p and forbidden.search(p)]
    if bad:
        raise SystemExit('Refusing SDK/game files in tracked source: ' + ', '.join(bad))
    workflows = sorted(p.name for p in (ROOT / '.github/workflows').glob('*') if p.suffix in {'.yml', '.yaml'})
    if workflows != ['windows-dlss-test.yml']:
        raise SystemExit('Only the manual test workflow may be active: ' + repr(workflows))
    print('Reviewed DLSS source is unchanged from ' + BASE + '; no SDK/game files are tracked.')


if __name__ == '__main__':
    check()
