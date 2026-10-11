"""Build native Windows executable or Linux equivalent on its target OS."""

import os
import subprocess
import sys
from pathlib import Path

project = Path(__file__).resolve().parents[1]
os.chdir(project)
subprocess.run([sys.executable, "scripts/prepare_icon.py"], check=True)
subprocess.run([sys.executable, "scripts/prepare_character.py"], check=True)
subprocess.run([sys.executable, "scripts/prepare_avatar.py"], check=True)
subprocess.run([sys.executable, "scripts/prepare_rpg_equipment.py"], check=True)
subprocess.run([sys.executable, "scripts/prepare_study_guide.py"], check=True)
subprocess.run([sys.executable, "scripts/prepare_quotes.py"], check=True)
subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], check=True
)
subprocess.run(
    [
        sys.executable,
        "-m",
        "PyInstaller",
        "--log-level",
        "WARN",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        "RUMO",
        "--icon",
        "assets/RUMO.ico",
        "--add-data",
        "assets:assets",
        "--collect-data",
        "tzdata",
        "--exclude-module",
        "PIL",
        "--exclude-module",
        "psutil",
        "--exclude-module",
        "pypdf",
        "--noupx",
        "app.py",
    ],
    check=True,
)
subprocess.run([sys.executable, "scripts/package_portable.py"], check=True)
if os.name == "nt":
    compiler = project / "tools/inno/ISCC.exe"
    if not compiler.exists():
        compiler = Path(
            os.environ.get("ISCC", r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")
        )
    if compiler.exists():
        subprocess.run([str(compiler), "/Q", "scripts/installer.iss"], check=True)
    else:
        print(
            "Executable built. Install Inno Setup 6 to compile scripts/installer.iss."
        )
else:
    import tarfile

    with tarfile.open(project / "dist/RUMO-linux-portatil.tar.gz", "w:gz") as archive:
        archive.add(project / "dist/RUMO", arcname="RUMO")
    print("Linux portable bundle built; launch RUMO/RUMO.")
