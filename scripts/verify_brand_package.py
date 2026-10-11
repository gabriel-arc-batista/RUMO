"""Check the packaged executable, directory names and distributable hashes."""

import hashlib
import zipfile
from pathlib import Path

project = Path(__file__).resolve().parents[1]
dist = project / "dist"
assert (dist / "RUMO/RUMO.exe").is_file()
assert (dist / "RUMO/_internal/assets/RUMO.ico").is_file()
assert (dist / "RUMO/_internal/assets/RUMO.png").is_file()
with zipfile.ZipFile(dist / "RUMO-Windows-Portatil.zip") as archive:
    names = archive.namelist()
    assert "RUMO/RUMO.exe" in names
    assert all(name.startswith("RUMO/") for name in names)
    assert archive.testzip() is None
files = [dist / "RUMO-Instalar-Windows.exe", dist / "RUMO-Windows-Portatil.zip"]
assert all(path.is_file() for path in files)
(dist / "SHA256SUMS.txt").write_text(
    "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in files
    ),
    encoding="utf-8",
)
print("RUMO executable, icons, portable archive and checksums verified.")
