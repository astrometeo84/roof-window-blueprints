#!/usr/bin/env python3
"""Blueprints aus dem Arbeitsverzeichnis in ein laufendes Home Assistant spielen.

Gedacht zum Ausprobieren vor dem Merge, nur vom PC des Nutzers (der Container
erreicht Home Assistant absichtlich nicht). Die Dateien werden so kopiert, wie
sie gerade auf der Platte liegen, auch mit ungespeicherten oder nur gestagten
Änderungen – beide Arten: blueprints/automation/… und blueprints/template/….
Danach lässt Home Assistant die Konfiguration prüfen und lädt Automationen
**und** Template-Entitäten neu.

Beide Neulade-Aktionen leeren vorher den Blueprint-Zwischenspeicher ihrer
Domain; geänderte Blueprint-Dateien werden also ohne Neustart neu eingelesen
(belegt im Quelltext von HA, siehe Skill sonnengeometrie, Abschnitt 5).

Achtung: Die Konfigurationsprüfung meldet Fehler in Template-Blueprints NICHT
als Fehler. Ein falscher Pfad oder eine fehlende Pflichteingabe kommt nur als
Warnung (das Skript zeigt sie an); passen die Eingaben nicht zum Schema,
verwirft HA den Abschnitt still und schreibt nur ins Protokoll bzw. eine
Benachrichtigung. Nach dem Neuladen deshalb immer Protokoll und
Benachrichtigungen ansehen.

Aufruf:
    uv run scripts/ha_deploy.py            # kopieren, prüfen, neu laden
    uv run scripts/ha_deploy.py --trocken  # nur anzeigen, was passieren würde

Einstellungen kommen aus Umgebungsvariablen oder aus der Datei ``.ha.env``
im Wurzelverzeichnis (steht in .gitignore, der Token gehört nicht ins Repo):

    HA_BLUEPRINT_ZIEL  Ordner "blueprints" der HA-Konfiguration. Entweder die
                       Samba-Freigabe:
                         \\\\homeassistant.local\\config\\blueprints
                         /Volumes/config/blueprints
                       oder ein scp-Ziel über das SSH-Add-on:
                         root@homeassistant.local:/config/blueprints/
                       Darunter landen die Dateien mit demselben relativen Pfad
                       wie im Repo, z. B. automation/dachfenster/….
    HA_URL             optional, z. B. http://homeassistant.local:8123
    HA_TOKEN           optional, langlebiger Zugriffstoken (Profil → Sicherheit)

Ohne HA_URL und HA_TOKEN wird nur kopiert. Dann in Home Assistant unter
Entwicklerwerkzeuge → YAML Automationen und Template-Entitäten von Hand neu laden.

Das Skript gibt weder Token noch Adresse aus (Skill security-secrets).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

WURZEL = Path(__file__).resolve().parent.parent
QUELLE = WURZEL / "blueprints"
ENV_DATEI = WURZEL / ".ha.env"

# benutzer@host:pfad – aber kein Windows-Laufwerk wie C:\...
SCP_MUSTER = re.compile(r"^[^\\/:@\s]+@[^\\/:\s]+:")

# Reihenfolge ist Absicht: erst prüfen, dann neu laden.
NEU_LADEN = (
    "/api/services/automation/reload",
    "/api/services/template/reload",
)


def lies_env_datei(pfad: Path) -> dict[str, str]:
    """KEY=VALUE-Zeilen lesen. Leerzeilen, Kommentare und Anführungszeichen erlaubt."""
    werte: dict[str, str] = {}
    if not pfad.is_file():
        return werte
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        schluessel, wert = zeile.split("=", 1)
        werte[schluessel.strip()] = wert.strip().strip('"').strip("'")
    return werte


def einstellungen(env: dict[str, str] | None = None) -> dict[str, str]:
    """Umgebungsvariablen haben Vorrang vor der Datei."""
    werte = lies_env_datei(ENV_DATEI)
    quelle = os.environ if env is None else env
    for schluessel in ("HA_BLUEPRINT_ZIEL", "HA_URL", "HA_TOKEN"):
        if quelle.get(schluessel):
            werte[schluessel] = quelle[schluessel]
    return werte


def ist_scp_ziel(ziel: str) -> bool:
    return bool(SCP_MUSTER.match(ziel))


def blueprint_dateien(quelle: Path | None = None) -> list[Path]:
    """Alle Blueprints, relativ zu blueprints/ (z. B. automation/dachfenster/x.yaml)."""
    quelle = QUELLE if quelle is None else quelle
    return sorted(p.relative_to(quelle) for p in quelle.glob("**/*.yaml"))


def kopieren(ziel: str, trocken: bool, quelle: Path | None = None) -> int:
    """Kopiert jede Datei an denselben relativen Pfad unter ``ziel``; liefert die Anzahl."""
    quelle = QUELLE if quelle is None else quelle
    dateien = blueprint_dateien(quelle)
    if not dateien:
        print("keine Blueprint-Dateien unter blueprints/ – nichts zu kopieren")
        return 0
    scp = ist_scp_ziel(ziel)
    for relativ in dateien:
        if scp:
            # scp braucht "/" auch dann, wenn das Skript unter Windows läuft.
            entfernt = ziel.rstrip("/") + "/" + str(PurePosixPath(*relativ.parts))
            print("scp  ->", relativ)
            if not trocken:
                try:
                    subprocess.run(["scp", "-q", str(quelle / relativ), entfernt], check=True)
                except subprocess.CalledProcessError as fehler:
                    # Eigene Meldung statt Traceback: Der Traceback zeigte die
                    # Befehlszeile samt Adresse. scp legt fehlende Ordner nicht an.
                    raise SystemExit(
                        f"scp fehlgeschlagen (Rückgabe {fehler.returncode}) bei {relativ}.\n"
                        f"Gibt es den Ordner {PurePosixPath(*relativ.parent.parts)}/ unter "
                        "HA_BLUEPRINT_ZIEL? Einmalig anlegen, z. B. im Terminal des SSH-Add-ons "
                        "mit mkdir -p."
                    ) from None
            continue
        datei = Path(ziel) / relativ
        print("copy ->", relativ)
        if trocken:
            continue
        if not Path(ziel).is_dir():
            raise SystemExit("Zielordner nicht gefunden (HA_BLUEPRINT_ZIEL).\n"
                             "Ist die Samba-Freigabe verbunden?")
        datei.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle / relativ, datei)
    return len(dateien)


def ha_aufruf(url: str, token: str, pfad: str) -> object:
    anfrage = urllib.request.Request(
        url.rstrip("/") + pfad,
        data=b"{}",
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(anfrage, timeout=120) as antwort:
        text = antwort.read().decode("utf-8") or "null"
    return json.loads(text)


def pruefen_und_neu_laden(url: str, token: str, trocken: bool, aufruf=ha_aufruf) -> int:
    print("prüfe Konfiguration, lade Automationen und Template-Entitäten neu")
    if trocken:
        return 0
    try:
        ergebnis = aufruf(url, token, "/api/config/core/check_config")
        # Nur ein ausdrückliches "valid" gilt; eine unerwartete Antwort ist ein Fehler.
        if not isinstance(ergebnis, dict) or ergebnis.get("result") != "valid":
            print("Home Assistant meldet Fehler, NICHTS neu geladen:")
            print(ergebnis.get("errors") if isinstance(ergebnis, dict) else ergebnis)
            return 1
        # Warnungen ausgeben: Genau hier meldet HA einen falschen use_blueprint-Pfad
        # oder eine fehlende Pflichteingabe eines Template-Blueprints – als Warnung,
        # nicht als Fehler (Skill sonnengeometrie, Abschnitt 5).
        if ergebnis.get("warnings"):
            print("Home Assistant meldet Warnungen (trotzdem neu geladen):")
            print(ergebnis["warnings"])
        for pfad in NEU_LADEN:
            aufruf(url, token, pfad)
    except urllib.error.HTTPError as fehler:
        # Prüfung und Neuladen verlangen Adminrechte; ohne sie antwortet HA mit 401
        # (nicht 403): require_admin bzw. async_register_admin_service.
        hinweis = {401: " (Token falsch, abgelaufen oder Benutzer ohne Adminrechte?)"}.get(
            fehler.code, "")
        print(f"Home Assistant antwortet mit {fehler.code}{hinweis}")
        return 1
    except urllib.error.URLError as fehler:
        # Nur die Art des Fehlers: Der Text (fehler.reason) kann den Hostnamen enthalten.
        print(f"Home Assistant nicht erreichbar ({type(fehler.reason).__name__})")
        return 1
    print("fertig – jetzt Einstellungen → System → Protokolle und die Benachrichtigungen ansehen:\n"
          "ein Template-Blueprint mit falschen Eingaben fällt bei der Prüfung nicht auf.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--trocken", action="store_true", help="nichts ändern, nur anzeigen")
    args = parser.parse_args(argv)

    cfg = einstellungen()
    ziel = cfg.get("HA_BLUEPRINT_ZIEL")
    if not ziel:
        print("HA_BLUEPRINT_ZIEL fehlt – siehe Kopf von scripts/ha_deploy.py", file=sys.stderr)
        return 2

    if not kopieren(ziel, args.trocken):
        return 0

    if cfg.get("HA_URL") and cfg.get("HA_TOKEN"):
        return pruefen_und_neu_laden(cfg["HA_URL"], cfg["HA_TOKEN"], args.trocken)
    print("Kein HA_URL/HA_TOKEN: Automationen und Template-Entitäten von Hand neu laden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
