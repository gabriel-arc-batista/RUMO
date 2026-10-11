"""Package documentation and component notices with the portable runtime."""

import hashlib
import os
import shutil
import sys
import zipfile
from importlib.metadata import distribution
from pathlib import Path

project = Path(__file__).resolve().parents[1]
bundle = project / "dist/RUMO"
notices = bundle / "licenses"
notices.mkdir(exist_ok=True)
for name in [
    "README.md",
    "CHECKLIST.md",
    "THIRD_PARTY.md",
    "FONTES.md",
    "SECURITY_REVIEW.md",
]:
    shutil.copy2(project / name, bundle / name)
# Keep README links to progression and validation usable in the portable folder.
(bundle / "docs").mkdir(exist_ok=True)
for source in (project / "docs").glob("*.md"):
    shutil.copy2(source, bundle / "docs" / source.name)
prefix = Path(sys.base_prefix)
font_license = project / "assets/fonts/OFL.txt"
if font_license.exists():
    shutil.copy2(font_license, notices / "Poppins-OFL.txt")
inter_license = project / "assets/fonts/LICENSE.txt"
if inter_license.exists():
    shutil.copy2(inter_license, notices / "Inter-OFL.txt")
python_license = prefix / "LICENSE.txt"
if not python_license.exists():
    python_license = (
        prefix
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "LICENSE.txt"
    )
shutil.copy2(python_license, notices / "Python-LICENSE.txt")
lucide_license = project / "assets/fonts/LUCIDE-LICENSE.txt"
if lucide_license.exists():
    shutil.copy2(lucide_license, notices / "Lucide-LICENSE.txt")
for name in ["tk8.6", "tcl8.6"]:
    source = prefix / "tcl" / name / "license.terms"
    if source.exists():
        shutil.copy2(source, notices / (name + "-license.terms"))
    elif sys.platform.startswith("linux"):
        library = os.environ.get(
            "TK_LIBRARY" if name.startswith("tk") else "TCL_LIBRARY"
        )
        if library:
            source = (
                Path(library).parents[2] / "share/doc" / ("lib" + name) / "copyright"
            )
            if source.is_file():
                shutil.copy2(source, notices / (name + "-copyright.txt"))
for package in ["tzdata", "pyinstaller"]:
    dist = distribution(package)
    for entry in dist.files:
        label = str(entry).replace("\\", "/")
        if "/licenses/" not in label:
            continue
        source = Path(dist.locate_file(entry))
        if source.is_file():
            target = notices / package / label.split("/licenses/", 1)[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
if sys.platform == "win32":
    output = project / "dist/RUMO-Windows-Portatil.zip"
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for source in sorted(bundle.rglob("*")):
            if source.is_file():
                archive.write(source, Path("RUMO") / source.relative_to(bundle))
    print("Portable ZIP:", output, "bytes:", output.stat().st_size)
