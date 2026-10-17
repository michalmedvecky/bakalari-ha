"""Ověří značku proti manifestu a připraví české poznámky z přehledu změn."""

import json
import re
import sys
from pathlib import Path


def release_notes(root: Path, tag: str) -> str:
    version = json.loads(
        (root / "custom_components/bakalari/manifest.json").read_text(encoding="utf-8")
    )["version"]
    if tag != f"v{version}" or not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Značka vydání neodpovídá verzi v manifestu.")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    section = re.search(
        rf"^## {re.escape(version)}(?: — [^\n]+)?\n(.*?)(?=^## |\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if not section or not section[1].strip():
        raise ValueError("V CHANGELOG.md chybí poznámky k vydávané verzi.")
    return section[1].strip() + "\n"


if __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    if len(sys.argv) != 2:
        raise SystemExit("Použití: python scripts/release_notes.py v1.0.0")
    try:
        notes = release_notes(project, sys.argv[1])
    except ValueError as error:
        raise SystemExit(str(error)) from error
    output = project / "dist/poznamky-k-vydani.md"
    output.parent.mkdir(exist_ok=True)
    output.write_text(notes, encoding="utf-8")
    print(output)
