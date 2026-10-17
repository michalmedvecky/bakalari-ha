"""Sestaví přenositelný instalační archiv bez mezipaměti a přihlašovacích údajů."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
component = root / "custom_components" / "bakalari"
version = json.loads((component / "manifest.json").read_text())["version"]
output = root / "dist" / f"bakalari-{version}.zip"
output.parent.mkdir(exist_ok=True)
with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for path in sorted(component.rglob("*")):
        if path.is_file() and path.suffix in (".py", ".json", ".yaml"):
            archive.write(path, path.relative_to(root))
    for path in [
        *sorted(root.glob("*.md")),
        root / "hacs.json",
        root / "LICENSE",
        *sorted((root / "docs").glob("*.md")),
    ]:
        archive.write(path, path.relative_to(root))
print(output)
