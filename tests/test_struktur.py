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

from conftest import REPO, BLUEPRINT_ORDNER, all_inputs, blueprint_dateien, input_names, load_blueprint

CONFIG = json.loads((REPO / ".release-please-config.json").read_text(encoding="utf-8"))
PAKET = CONFIG["packages"]["."]
MANIFEST = json.loads((REPO / ".release-please-manifest.json").read_text(encoding="utf-8"))
VERSION_ZEILE = re.compile(r"^#\s*Version:\s*(\S+)\s*#\s*x-release-please-version\s*$", re.MULTILINE)
RELEASE_WORKFLOW = REPO / ".github" / "workflows" / "release-please.yml"
VALIDATE_WORKFLOW = REPO / ".github" / "workflows" / "validate.yml"

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


TEMPLATE_BLUEPRINTS = [p for p in blueprint_dateien() if p.parent.parent.name == "template"]
# Plattformen, die ein Template-Blueprint beschreiben kann (eine je Blueprint).
TEMPLATE_PLATTFORMEN = {"sensor", "binary_sensor", "number", "select", "button", "image",
                        "weather", "switch", "light", "cover", "fan", "lock", "vacuum",
                        "alarm_control_panel", "event", "update"}
SONNENEINFALL = BLUEPRINT_ORDNER / "template" / "dachfenster" / "flaeche_sonneneinfall.yaml"


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(t) for t in text.split("."))


@pytest.mark.parametrize("datei", blueprint_dateien(), ids=_relativ)
def test_eingaben_deklariert_und_benutzt(datei):
    """Jedes ``!input x`` braucht eine Eingabe x – und jede Eingabe wird benutzt.

    Ein Tippfehler im Namen fiele sonst erst in HA auf, bei Template-Blueprints
    nur als Warnung beim Laden.
    """
    deklariert = set(all_inputs(load_blueprint(datei)))
    assert input_names(datei) == deklariert


@pytest.mark.parametrize("datei", blueprint_dateien(), ids=_relativ)
def test_kopfdaten(datei):
    bp = load_blueprint(datei)["blueprint"]
    assert bp["name"] and bp["description"] and bp["author"]
    assert bp["domain"] == datei.parent.parent.name
    assert bp["source_url"] == (
        "https://github.com/astrometeo84/roof-window-blueprints/blob/main/" + _relativ(datei))
    # Format laut HA: major.minor.patch, alle drei Teile Pflicht.
    assert re.fullmatch(r"\d{4}\.\d{1,2}\.\d+", bp["homeassistant"]["min_version"])


@pytest.mark.parametrize("datei", blueprint_dateien(), ids=_relativ)
def test_min_version_reicht_fuer_clamp(datei):
    """``clamp`` gibt es erst seit HA 2025.4 (Skill sonnengeometrie, 2)."""
    if "clamp(" not in datei.read_text(encoding="utf-8"):
        pytest.skip("nutzt clamp nicht")
    min_version = load_blueprint(datei)["blueprint"]["homeassistant"]["min_version"]
    assert _version(min_version) >= (2025, 4, 0)


@pytest.mark.parametrize("datei", TEMPLATE_BLUEPRINTS, ids=_relativ)
def test_template_blueprint_beschreibt_genau_eine_entitaet(datei):
    """HA lehnt mehr als eine Entität je Template-Blueprint ab (template/config.py)."""
    bp = load_blueprint(datei)
    plattformen = set(bp) - {"blueprint", "variables"}
    assert len(plattformen) == 1 and plattformen <= TEMPLATE_PLATTFORMEN, plattformen
    # Eingaben kommen über variables in die Vorlagen, nicht direkt als !input
    # in einer Vorlage (dort wäre es ein Text, keine Variable).
    for name in all_inputs(bp):
        assert bp["variables"][name] == ("INPUT", name)


def test_sonneneinfall_eingaben():
    """Azimut als Kompass 0–360, Neigung 0–90, beide in Grad (docs/ENTWURF.md 4.1)."""
    bp = load_blueprint(SONNENEINFALL)
    eingaben = all_inputs(bp)
    for name, (lo, hi) in {"azimut": (0, 360), "neigung": (0, 90)}.items():
        zahl = eingaben[name]["selector"]["number"]
        assert (zahl["min"], zahl["max"]) == (lo, hi), name
        assert zahl["unit_of_measurement"] == "°", name
        assert "default" not in eingaben[name], f"{name}: Pflicht, ohne Standardwert"


def test_sonneneinfall_sensor():
    sensor = load_blueprint(SONNENEINFALL)["sensor"]
    assert sensor["unit_of_measurement"] == "°"
    assert sensor["state_class"] == "measurement"
    assert "device_class" not in sensor, "für Winkel gibt es keine device_class"
    assert set(sensor["attributes"]) == {"cos_einfall", "sonne_trifft_flaeche", "azimut", "neigung"}
    assert "availability" in sensor
    # Die Schlüssel, die wir nutzen wollen – eine Teilmenge des Sensor-Schemas
    # (template/sensor.py, schemas.py; Skill sonnengeometrie, 5). Ein Tippfehler
    # wie "unit_of_measurment" verwürfe HA still.
    assert set(sensor) <= {"state", "availability", "attributes", "unit_of_measurement",
                           "state_class", "device_class", "icon", "picture", "name"}


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


def _ohne_kommentare(text):
    """Nur Befehle zählen: Die Kommentare im Workflow nennen dieselben Begriffe.

    Entfernt ganze Kommentarzeilen und Kommentare am Zeilenende (" #…"; unsere
    Workflows haben kein "#" in Anführungszeichen) und fügt mit "\\"
    fortgesetzte Shell-Zeilen zusammen, damit ein Befehl eine Zeile ist.
    """
    zeilen = [re.sub(r"\s+#.*$", "", z) for z in text.splitlines() if not z.lstrip().startswith("#")]
    return re.sub(r"\\\n\s*", " ", "\n".join(zeilen))


@pytest.mark.skipif(not VALIDATE_WORKFLOW.is_file(), reason="Workflow legt der Nutzer an")
def test_ha_job_prueft_mit_fail_on_warnings():
    """Ohne den Schalter bleibt der HA-Job bei Ladefehlern grün (docs/ENTWURF.md 6.1)."""
    text = _ohne_kommentare(VALIDATE_WORKFLOW.read_text(encoding="utf-8"))
    pruefung = re.findall(r"[^\n]*--script\s+check_config\s+--fail-on-warnings[^\n]*", text)
    assert len(pruefung) == 1, pruefung
    # Der Schalter nützt nichts, wenn der Exit-Code verschluckt wird.
    assert "||" not in pruefung[0], pruefung[0]
    assert "continue-on-error" not in text
    aufrufe = re.findall(r"docker run[^\n]*", text)
    assert aufrufe
    for aufruf in aufrufe:
        assert re.search(r"--entrypoint[ =](\"\"|'')", aufruf), \
            f"ohne leeren Entrypoint startet das Image HA selbst: {aufruf}"
    assert re.search(r"cp\s+tests/fixtures/secrets\.yaml\s+ha/secrets\.yaml", text), \
        "secrets.yaml hat früher die Action kopiert"
    assert not re.search(r"uses:\s*frenck/action-home-assistant", text), \
        "die Action reicht --fail-on-warnings nicht durch"


# Per Muster statt fester Namen: Auch ein dritter Workflow oder eine Datei
# mit Endung .yaml wird erfasst statt still übersprungen.
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.y*ml"))


@pytest.mark.skipif(not WORKFLOWS, reason="Workflows legt der Nutzer an")
@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda w: w.name)
def test_setup_uv_mit_vollstaendiger_version(workflow):
    """setup-uv hat seit v8 keine Major-Tags mehr; @v10 gäbe es nicht (docs/ENTWURF.md 6.5)."""
    text = workflow.read_text(encoding="utf-8")
    aufrufe = re.findall(r"astral-sh/setup-uv@(\S+)", text)
    assert aufrufe
    for ref in aufrufe:
        assert re.fullmatch(r"v\d+\.\d+\.\d+", ref), ref


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


INSTANZ_SCHLUESSEL = {"use_blueprint", "name", "unique_id"}


def _template_instanzen():
    return [e for e in _fixture("configuration.yaml").get("template", []) if "use_blueprint" in e]


def test_fixture_template_instanzen_passen_zum_blueprint():
    """Ladefehler wie ein falscher path kommen in HA nur als Warnung, Schemafehler
    gar nicht (Skill sonnengeometrie, 5). Deshalb prüfen wir die Instanzen hier."""
    for instanz in _template_instanzen():
        assert set(instanz) <= INSTANZ_SCHLUESSEL, f"unbekannte Schlüssel: {set(instanz) - INSTANZ_SCHLUESSEL}"
        ub = instanz["use_blueprint"]
        assert set(ub) == {"path", "input"}
        datei = BLUEPRINT_ORDNER / "template" / ub["path"]
        assert datei.is_file(), f"path zeigt ins Leere: {ub['path']}"
        eingaben = all_inputs(load_blueprint(datei))
        assert set(ub["input"]) <= set(eingaben), f"keine echte Eingabe: {set(ub['input']) - set(eingaben)}"
        pflicht = {n for n, e in eingaben.items() if "default" not in e}
        assert pflicht <= set(ub["input"]), f"Pflichteingabe fehlt: {pflicht - set(ub['input'])}"


@pytest.mark.parametrize("datei", TEMPLATE_BLUEPRINTS, ids=_relativ)
def test_fixture_je_template_blueprint_minimal_und_vollstaendig(datei):
    """Skill neuer-blueprint, 5: eine minimale und eine vollständig belegte Instanz."""
    pfad = datei.relative_to(BLUEPRINT_ORDNER / "template").as_posix()
    eingaben = all_inputs(load_blueprint(datei))
    pflicht = {n for n, e in eingaben.items() if "default" not in e}
    instanzen = [i for i in _template_instanzen() if i["use_blueprint"]["path"] == pfad]
    minimal = [i for i in instanzen
               if set(i) == {"use_blueprint"} and set(i["use_blueprint"]["input"]) == pflicht]
    vollstaendig = [i for i in instanzen
                    if set(i) == INSTANZ_SCHLUESSEL and set(i["use_blueprint"]["input"]) == set(eingaben)]
    assert minimal, f"keine minimale Instanz für {pfad}"
    assert vollstaendig, f"keine vollständige Instanz für {pfad}"


def test_fixture_unique_ids_eindeutig():
    ids = [i["unique_id"] for i in _template_instanzen() if "unique_id" in i]
    assert len(ids) == len(set(ids))


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
