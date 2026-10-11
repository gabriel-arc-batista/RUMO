"""Smoke-test setup/uninstall in a checked workspace target, with no study data."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
import winreg

project = Path(__file__).resolve().parents[1]
registry = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{96028A65-51CB-4DA7-B623-512B6896BA09}_is1"
try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry)
    key.Close()
except FileNotFoundError:
    pass
else:
    print("Skipped: an existing user installation must be preserved.")
    sys.exit(0)

target = (project / "validation/install-smoke").resolve()
if not target.is_relative_to(project):
    raise ValueError("Installer test target escaped the workspace.")
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
installed = subprocess.run(
    [
        str(project / "dist/Rumo-Instalar-Windows.exe"),
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOICONS",
        "/TASKS=",
        f"/DIR={target}",
    ],
    startupinfo=startup,
    timeout=90,
)
exe = target / "RUMO.exe"
uninstaller = (target / "unins000.exe").resolve()
if (
    not exe.exists()
    or not uninstaller.is_relative_to(target)
    or not uninstaller.exists()
):
    raise ValueError("Installer output is incomplete or outside its checked target.")
hashes_match = (
    hashlib.sha256(exe.read_bytes()).digest()
    == hashlib.sha256((project / "dist/RUMO/RUMO.exe").read_bytes()).digest()
)
license_exists = (target / "licenses/Python-LICENSE.txt").is_file()
uninstalled = subprocess.run(
    [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
    startupinfo=startup,
    timeout=90,
)
report = {
    "installer_exit": installed.returncode,
    "exe_present": True,
    "exe_hash_matches": hashes_match,
    "license_present": license_exists,
    "uninstaller_exit": uninstalled.returncode,
    "per_user": True,
    "test_target": str(target),
    "production_data_touched": False,
}
(project / "validation/installer-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(report, ensure_ascii=False))
assert (
    installed.returncode == 0
    and uninstalled.returncode == 0
    and hashes_match
    and license_exists
)
