"""Aufbau des Repos: Blueprints, Release-Kette, CI-Fixtures, Zugangsdaten.

Diese Tests fangen Fehler ab, die sonst erst beim Release oder in der CI auf
GitHub auffallen – oder gar nicht, weil sie lautlos passieren (etwa ein
Blueprint, dessen Versionsnummer release-please nicht anhebt).

Die Tests je Blueprint laufen über alle Dateien unter blueprints/. Solange es
noch keine gibt, werden sie als übersprungen gemeldet.
"""

from __future__ import annotations

import importlib.util
import json
import re
import tomllib
from collections import Counter

import pytest
import yaml

from conftest import REPO, BLUEPRINT_ORDNER, blueprint_dateien

CONFIG = json.loads((REPO / ".release-please-config.json").read_text(encoding="utf-8"))
PAKET = CONFIG["packages"]["."]
MANIFEST = json.loads((REPO / ".release-please-manifest.json").read_text(encoding="utf-8"))
VERSION_ZEILE = re.compile(r"^#\s*Version:\s*(\S+)\s*#\s*x-release-please-version\s*$", re.MULTILINE)
RELEASE_WORKFLOW = REPO / ".github" / "workflows" / "release-please.yml"

# Präfixe, die im CHANGELOG erscheinen und damit einen Release-PR auslösen.
# Äußere Vorgabe aus docs/ENTWURF.md 6.3 und CLAUDE.md, daher hier einmal
# ausgeschrieben.
SICHTBAR = {"feat", "fix", "perf"}
VERSTECKT = {"refactor", "docs", "test", "ci", "chore"}

_spec = importlib.util.spec_from_file_location("check_version", REPO / "scripts" / "check_version.py")
check_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_version)


def _relativ(pfad) -> str:
    return pfad.relative_to(REPO).as_posix()


def _extra_files() -> list[str]:
    return [e if isinstance(e, str) else e["path"] for e in PAKET["extra-files"]]


# ==========================================================================
# Blueprints und Versionskopf
# ==========================================================================
@pytest.mark.parametrize("datei", blueprint_dateien(), ids=_relativ)
def test_versionskopf_vorhanden(datei):
    """Ohne die Markierung hebt release-please die Version nicht an.

    Sie fehlt lautlos: Der Release entsteht trotzdem, nur trägt die
    ausgelieferte Datei dann die alte Versionsnummer.
    """
    kopf = datei.read_text(encoding="utf-8").split("blueprint:")[0]
    assert VERSION_ZEILE.search(kopf), (
        "Kopfzeile '# Version: X.Y.Z # x-release-please-version' fehlt vor 'blueprint:'"
    )


@pytest.mark.parametrize("datei", blueprint_dateien(), ids=_relativ)
def test_versionskopf_passt_zum_manifest(datei):
    """Ein neuer Blueprint muss mit der aktuellen Version starten (Skill neuer-blueprint)."""
    treffer = VERSION_ZEILE.search(datei.read_text(encoding="utf-8"))
    assert treffer and treffer.group(1) == MANIFEST["."]


@pytest.mark.parametrize("datei", blueprint_dateien(), ids=_relativ)
def test_blueprint_liegt_in_bekanntem_ordner(datei):
    """Die CI kopiert nur diese beiden Ordner nach ha/blueprints/."""
    assert datei.parent.relative_to(BLUEPRINT_ORDNER).as_posix() in (
        "automation/dachfenster",
        "template/dachfenster",
    )


def test_blueprint_dateinamen_sind_eindeutig():
    """Der Release-Workflow hängt alle Blueprints per Muster ans Release.

    Release-Anhänge haben keine Ordner. Hießen zwei Dateien gleich (etwa
    automation/…/x.yaml und template/…/x.yaml), überschriebe die eine die
    andere wegen ``--clobber`` – ohne Fehlermeldung.
    """
    doppelt = [n for n, k in Counter(p.name for p in blueprint_dateien()).items() if k > 1]
    assert not doppelt, f"Dateiname mehrfach unter blueprints/: {doppelt}"


def test_unter_blueprints_nur_yaml_dateien():
    """Tests, check_version.py, Release-Upload und CI suchen alle nur ``*.yaml``.

    Ein Blueprint ``x.yml`` fiele überall lautlos durch: nicht getestet, nicht
    versioniert, nicht hochgeladen, von der CI nicht geladen.
    """
    if not BLUEPRINT_ORDNER.is_dir():
        return
    fremd = [p.relative_to(REPO).as_posix() for p in BLUEPRINT_ORDNER.rglob("*")
             if p.is_file() and p.suffix != ".yaml"]
    assert not fremd, f"unter blueprints/ nur .yaml erlaubt: {fremd}"


# ==========================================================================
# release-please
# ==========================================================================
def test_extra_files_nennt_genau_die_blueprints():
    """Fehlt ein Blueprint in extra-files, hebt release-please seine Version nicht an.

    extra-files startet leer und wächst mit jedem Blueprint (Skill
    neuer-blueprint). Umgekehrt darf dort nichts stehen, was kein Blueprint
    ist – insbesondere nicht die pyproject.toml (Test unten).
    """
    erwartet = sorted(_relativ(p) for p in blueprint_dateien())
    assert sorted(_extra_files()) == erwartet


def test_release_please_fasst_die_pyproject_nicht_an():
    """Landet die pyproject.toml in extra-files, hebt der Bot die Version dort an
    und die uv.lock läuft weg – die CI des Release-PR scheitert an --locked."""
    assert not [p for p in _extra_files() if "pyproject.toml" in p]


def test_pyproject_version_bleibt_eingefroren():
    """Die echte Version steht allein im Kopf der Blueprints (docs/ENTWURF.md 6.4)."""
    projekt = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert projekt["project"]["version"] == "0", (
        f'pyproject.toml steht auf {projekt["project"]["version"]!r} statt "0" – '
        "vermutlich hat jemand sie „aktualisiert“. Die echte Version gehört "
        "allein in den Kopf der Blueprints."
    )


def test_uv_lock_fuehrt_projektversion_null():
    """Die uv.lock führt die Version des eigenen Projekts mit.

    Weichen pyproject.toml und uv.lock ab, bricht jeder Lauf mit ``--locked``
    ab – mit einer Meldung, die nach fehlenden Abhängigkeiten klingt statt
    nach der Versionsnummer. Dieser Test zeigt direkt auf die Ursache. Ob die
    Sperrdatei sonst aktuell ist, prüft die CI mit ``--locked``.
    """
    sperre = tomllib.loads((REPO / "uv.lock").read_text(encoding="utf-8"))
    eigene = [p for p in sperre.get("package", []) if p.get("source", {}).get("virtual") == "."]
    assert eigene, "uv.lock führt das eigene Projekt nicht – 'uv lock' erzeugt den Eintrag"
    assert eigene[0]["name"] == "roof-window-blueprints"
    assert eigene[0]["version"] == "0", (
        f'uv.lock sagt {eigene[0]["version"]}, erwartet "0". Ein "uv lock" bringt beide '
        "wieder zusammen."
    )


def test_manifest_kennt_das_wurzelpaket():
    assert re.fullmatch(r"\d+\.\d+\.\d+", MANIFEST["."])


def test_bump_minor_pre_major():
    """In der 0.x-Phase soll ein ``feat!:`` 0.x → 0.(x+1) machen, nicht sofort 1.0.0."""
    assert PAKET["bump-minor-pre-major"] is True


def test_sichtbare_changelog_abschnitte():
    """Jeder sichtbare Abschnitt löst einen Release-PR aus.

    ``refactor`` ist hier bewusst versteckt (bei wled sichtbar, obwohl dort
    CONTRIBUTING.md „keine Version“ sagt), ``perf`` bewusst sichtbar.
    """
    abschnitte = {s["type"]: s for s in PAKET["changelog-sections"]}
    assert set(abschnitte) == SICHTBAR | VERSTECKT
    sichtbar = {t for t, s in abschnitte.items() if not s.get("hidden", False)}
    assert sichtbar == SICHTBAR


def test_contributing_tabelle_passt_zur_konfiguration():
    """Die Präfix-Tabelle in CONTRIBUTING.md darf der Konfiguration nicht widersprechen."""
    text = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    zeilen = re.findall(r"^\|\s*`(\w+)!?:?`\s*\|.*\|\s*(ja|nein)\s*\|\s*$", text, re.MULTILINE)
    tabelle = dict(zeilen)
    assert set(tabelle) == SICHTBAR | VERSTECKT, f"Präfixe in CONTRIBUTING.md: {sorted(tabelle)}"
    for praefix, release in tabelle.items():
        erwartet = "ja" if praefix in SICHTBAR else "nein"
        assert release == erwartet, f"CONTRIBUTING.md: `{praefix}` löst Release aus? steht {release}"


def test_claude_md_nennt_alle_release_praefixe():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    zeile = next(z for z in text.splitlines() if "erscheinen im CHANGELOG" in z)
    for praefix in SICHTBAR:
        assert f"`{praefix}`" in zeile


@pytest.mark.skipif(not RELEASE_WORKFLOW.is_file(), reason="Workflow legt der Nutzer an")
def test_release_workflow_haengt_alle_blueprints_per_muster_an():
    """Keine feste Liste im Workflow: neue Blueprints kommen ohne Workflow-Änderung mit."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "blueprints/**/*.yaml" in text
    assert "globstar" in text, "ohne 'shopt -s globstar' passt ** nur auf eine Ordnerebene"
    assert not re.search(r"blueprints/(automation|template)/\S+\.yaml", text), "feste Liste gefunden"


# ==========================================================================
# scripts/check_version.py
# ==========================================================================
def _blueprint(ordner, name, version):
    datei = ordner / "blueprints" / "template" / "dachfenster" / name
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(f"# Version: {version} # x-release-please-version\nblueprint: {{}}\n",
                     encoding="utf-8")
    return datei


def test_check_version_passt(tmp_path, capsys):
    _blueprint(tmp_path, "a.yaml", "0.2.0")
    _blueprint(tmp_path, "b.yaml", "0.2.0")
    assert check_version.main(["x", "0.2.0"], wurzel=tmp_path) == 0
    assert "2 Blueprints" in capsys.readouterr().out


def test_check_version_findet_den_abweichenden(tmp_path, capsys):
    _blueprint(tmp_path, "a.yaml", "0.2.0")
    _blueprint(tmp_path, "b.yaml", "0.1.0")
    assert check_version.main(["x", "0.2.0"], wurzel=tmp_path) == 1
    fehler = capsys.readouterr().err
    assert "b.yaml" in fehler and "a.yaml" not in fehler


def test_check_version_ohne_kopfzeile(tmp_path):
    datei = _blueprint(tmp_path, "a.yaml", "0.2.0")
    datei.write_text("blueprint: {}\n", encoding="utf-8")
    assert check_version.main(["x", "0.2.0"], wurzel=tmp_path) == 1


def test_check_version_ohne_blueprints_schlaegt_fehl(tmp_path):
    """Ein Release ohne eine einzige Datei wäre ein Konfigurationsfehler."""
    assert check_version.main(["x", "0.2.0"], wurzel=tmp_path) == 1


def test_check_version_falscher_aufruf():
    assert check_version.main(["x"]) == 2


# ==========================================================================
# Die Testkonfiguration für den Home-Assistant-Job in der CI
# ==========================================================================
class _HaLoader(yaml.SafeLoader):
    """Kennt die HA-Tags der Fixtures, ohne sie aufzulösen."""


for _tag in ("!include", "!secret", "!input"):
    _HaLoader.add_constructor(_tag, lambda loader, node: (node.tag, loader.construct_scalar(node)))


def _fixture(name):
    return yaml.load((REPO / "tests" / "fixtures" / name).read_text(encoding="utf-8"), Loader=_HaLoader)


def test_fixture_configuration_bindet_automationen_ein():
    cfg = _fixture("configuration.yaml")
    assert cfg["automation"] == ("!include", "automations.yaml")
    assert isinstance(cfg.get("template", []), list)


def test_fixture_automations_ist_eine_liste():
    assert isinstance(_fixture("automations.yaml"), list)


def test_fixture_secrets_ist_nur_platzhalter():
    werte = _fixture("secrets.yaml")
    assert werte == {"platzhalter": "unbenutzt"}


# ==========================================================================
# Zugangsdaten und Dateien
# ==========================================================================
def test_ha_env_ist_ignoriert():
    """Die Datei enthält den Zugriffstoken und darf nie eingecheckt werden."""
    zeilen = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".ha.env" in zeilen
    assert "ha/" in zeilen
    assert "uv.lock" not in zeilen, "uv.lock gehört ins Repo"


def test_ha_env_vorlage_ohne_token():
    werte = {}
    for zeile in (REPO / ".ha.env.example").read_text(encoding="utf-8").splitlines():
        if "=" in zeile and not zeile.lstrip().startswith("#"):
            schluessel, wert = zeile.split("=", 1)
            werte[schluessel.strip()] = wert.strip()
    assert werte.get("HA_TOKEN") == "", "In der Vorlage darf kein Token stehen"
    assert set(werte) == {"HA_BLUEPRINT_ZIEL", "HA_URL", "HA_TOKEN"}


def test_gitattributes_zeilenenden():
    text = (REPO / ".gitattributes").read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in text
    assert "*.ps1 text eol=crlf" in text
