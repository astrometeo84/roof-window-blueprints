#!/usr/bin/env python3
"""Prüft, ob die Version im Kopf jedes Blueprints zum Git-Tag passt.

Aufruf:  python3 scripts/check_version.py 0.1.0

Jeder Blueprint trägt die Version als Kommentarzeile im Kopf, weil das
Blueprint-Schema von Home Assistant kein eigenes Versionsfeld kennt.
release-please hebt sie über die Markierung x-release-please-version an.

Die Blueprints werden per Muster unter blueprints/ gesucht, nicht aus einer
festen Liste. So muss bei einem neuen Blueprint niemand dieses Skript
anpassen; vergessen kann man dann nur noch extra-files in
.release-please-config.json, und das fängt tests/test_struktur.py ab.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
# Hinter der Version darf die Markierung von release-please stehen.
MUSTER = re.compile(r"^#\s*Version:\s*(\S+)", re.MULTILINE)


def blueprint_dateien(wurzel: Path = WURZEL) -> list[Path]:
    return sorted((wurzel / "blueprints").glob("**/*.yaml"))


def pruefe(erwartet: str, dateien: list[Path]) -> list[str]:
    """Liefert die Fehlermeldungen; leer heißt: alles passt."""
    if not dateien:
        return ["keine Blueprint-Dateien unter blueprints/ gefunden"]
    fehler = []
    for datei in dateien:
        treffer = MUSTER.search(datei.read_text(encoding="utf-8"))
        if not treffer:
            fehler.append(f"{datei.name}: keine Zeile '# Version: ...'")
        elif treffer.group(1) != erwartet:
            fehler.append(f"{datei.name}: Tag sagt {erwartet}, Blueprint sagt {treffer.group(1)}")
    return fehler


def main(argv: list[str], wurzel: Path = WURZEL) -> int:
    if len(argv) != 2:
        print("Aufruf: check_version.py <version-ohne-v>", file=sys.stderr)
        return 2

    dateien = blueprint_dateien(wurzel)
    fehler = pruefe(argv[1], dateien)
    if fehler:
        for zeile in fehler:
            print(f"FEHLER: {zeile}", file=sys.stderr)
        print("Steht der Blueprint in extra-files von .release-please-config.json?", file=sys.stderr)
        return 1

    print(f"Version {argv[1]} passt zum Tag ({len(dateien)} Blueprints).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
