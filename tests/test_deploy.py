"""scripts/ha_deploy.py – spielt die Blueprints zum Ausprobieren in Home Assistant.

Kein Netz: Kopiert wird in ein Temp-Verzeichnis, Home Assistant ist ein
aufgezeichneter Ersatz für ``ha_aufruf``.
"""

from __future__ import annotations

import importlib.util
import urllib.error

import pytest

from conftest import REPO

_spec = importlib.util.spec_from_file_location("ha_deploy", REPO / "scripts" / "ha_deploy.py")
ha_deploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ha_deploy)


@pytest.fixture
def quelle(tmp_path):
    """Ein Repo-Ordner blueprints/ mit je einem Blueprint beider Arten."""
    wurzel = tmp_path / "blueprints"
    for relativ in ("automation/dachfenster/warnung.yaml", "template/dachfenster/einfall.yaml"):
        datei = wurzel / relativ
        datei.parent.mkdir(parents=True)
        datei.write_text(f"# {relativ}\n", encoding="utf-8")
    return wurzel


@pytest.mark.parametrize(
    "ziel,scp",
    [
        ("root@homeassistant.local:/config/blueprints/", True),
        ("root@192.0.2.10:/homeassistant/blueprints/", True),
        (r"\\homeassistant.local\config\blueprints", False),
        (r"C:\Users\ich\ha-config\blueprints", False),
        ("/Volumes/config/blueprints", False),
    ],
)
def test_scp_ziel_wird_erkannt(ziel, scp):
    """Ein Windows-Laufwerk wie C:\\ darf nicht für ein scp-Ziel gehalten werden."""
    assert ha_deploy.ist_scp_ziel(ziel) is scp


def test_env_datei(tmp_path):
    datei = tmp_path / ".ha.env"
    datei.write_text(
        '# Kommentar\n\nHA_URL="http://ha:8123"\nHA_TOKEN = abc\nkaputt\n', encoding="utf-8"
    )
    assert ha_deploy.lies_env_datei(datei) == {"HA_URL": "http://ha:8123", "HA_TOKEN": "abc"}


def test_umgebung_hat_vorrang(tmp_path, monkeypatch):
    datei = tmp_path / ".ha.env"
    datei.write_text("HA_URL=http://alt\nHA_TOKEN=aus-datei\n", encoding="utf-8")
    monkeypatch.setattr(ha_deploy, "ENV_DATEI", datei)
    cfg = ha_deploy.einstellungen({"HA_URL": "http://neu"})
    assert cfg == {"HA_URL": "http://neu", "HA_TOKEN": "aus-datei"}


def test_kopiert_beide_arten_mit_relativem_pfad(quelle, tmp_path):
    ziel = tmp_path / "ha_blueprints"
    ziel.mkdir()
    assert ha_deploy.kopieren(str(ziel), trocken=False, quelle=quelle) == 2
    for relativ in ("automation/dachfenster/warnung.yaml", "template/dachfenster/einfall.yaml"):
        assert (ziel / relativ).read_bytes() == (quelle / relativ).read_bytes()


def test_trocken_kopiert_nichts(quelle, tmp_path, capsys):
    ziel = tmp_path / "ha_blueprints"
    ziel.mkdir()
    ha_deploy.kopieren(str(ziel), trocken=True, quelle=quelle)
    assert not list(ziel.iterdir())
    ausgabe = capsys.readouterr().out
    assert "template/dachfenster/einfall.yaml" in ausgabe.replace("\\", "/")


def test_fehlender_zielordner(quelle, tmp_path):
    with pytest.raises(SystemExit):
        ha_deploy.kopieren(str(tmp_path / "gibt_es_nicht"), trocken=False, quelle=quelle)


def test_scp_ruft_je_datei_scp_mit_schraegstrich(quelle, monkeypatch):
    aufrufe = []
    monkeypatch.setattr(ha_deploy.subprocess, "run", lambda befehl, check: aufrufe.append(befehl))
    ha_deploy.kopieren("root@ha:/config/blueprints/", trocken=False, quelle=quelle)
    assert [b[-1] for b in aufrufe] == [
        "root@ha:/config/blueprints/automation/dachfenster/warnung.yaml",
        "root@ha:/config/blueprints/template/dachfenster/einfall.yaml",
    ]


def test_scp_fehler_ohne_adresse_und_mit_hinweis(quelle, monkeypatch, capsys):
    """scp legt fehlende Ordner nicht an; die Meldung darf die Adresse nicht zeigen."""
    def scheitert(befehl, check):
        raise ha_deploy.subprocess.CalledProcessError(1, befehl)

    monkeypatch.setattr(ha_deploy.subprocess, "run", scheitert)
    with pytest.raises(SystemExit) as fehler:
        ha_deploy.kopieren("root@ha-geheim.example:/config/blueprints/", trocken=False, quelle=quelle)
    meldung = str(fehler.value) + capsys.readouterr().out
    assert "automation/dachfenster/" in meldung and "mkdir -p" in meldung
    assert "ha-geheim.example" not in meldung


def test_ohne_blueprints_wird_nichts_kopiert(tmp_path):
    leer = tmp_path / "blueprints"
    leer.mkdir()
    assert ha_deploy.kopieren(str(tmp_path), trocken=False, quelle=leer) == 0


class _Ha:
    """Aufgezeichneter Ersatz für Home Assistant."""

    def __init__(self, pruefung="valid", fehler=None):
        self.pfade: list[str] = []
        self.pruefung = pruefung
        self.fehler = fehler
        self.warnungen = None

    def __call__(self, url, token, pfad):
        if self.fehler:
            raise self.fehler
        self.pfade.append(pfad)
        if pfad.endswith("check_config"):
            if self.pruefung is None:  # unerwartete Antwort statt dict
                return None
            return {"result": self.pruefung, "errors": None if self.pruefung == "valid" else "kaputt",
                    "warnings": self.warnungen}
        return []


def test_laedt_automationen_und_templates_nach_der_pruefung():
    ha = _Ha()
    assert ha_deploy.pruefen_und_neu_laden("http://ha", "geheim", False, aufruf=ha) == 0
    assert ha.pfade == [
        "/api/config/core/check_config",
        "/api/services/automation/reload",
        "/api/services/template/reload",
    ]


def test_laedt_nichts_bei_fehlerhafter_konfiguration():
    ha = _Ha(pruefung="invalid")
    assert ha_deploy.pruefen_und_neu_laden("http://ha", "geheim", False, aufruf=ha) == 1
    assert ha.pfade == ["/api/config/core/check_config"]


def test_unerwartete_antwort_der_pruefung_laedt_nichts():
    ha = _Ha(pruefung=None)
    assert ha_deploy.pruefen_und_neu_laden("http://ha", "geheim", False, aufruf=ha) == 1
    assert ha.pfade == ["/api/config/core/check_config"]


def test_trocken_ruft_ha_nicht_auf():
    ha = _Ha()
    assert ha_deploy.pruefen_und_neu_laden("http://ha", "geheim", True, aufruf=ha) == 0
    assert ha.pfade == []


def test_401_nennt_token_und_adminrechte(capsys):
    """Ohne Adminrechte antwortet HA mit 401, nicht 403 (require_admin)."""
    fehler = urllib.error.HTTPError("http://ha", 401, "nein", {}, None)
    assert ha_deploy.pruefen_und_neu_laden("http://ha", "geheim", False, aufruf=_Ha(fehler=fehler)) == 1
    ausgabe = capsys.readouterr().out
    assert "Token" in ausgabe and "Adminrechte" in ausgabe


def test_warnungen_der_pruefung_werden_gezeigt(capsys):
    """Ein falscher use_blueprint-Pfad kommt bei Template-Blueprints nur als Warnung."""
    ha = _Ha()
    ha.warnungen = "Template: Failed to load blueprint"
    assert ha_deploy.pruefen_und_neu_laden("http://ha", "geheim", False, aufruf=ha) == 0
    assert "Failed to load blueprint" in capsys.readouterr().out


def test_gibt_weder_token_noch_adresse_aus(capsys):
    """Skill security-secrets: Die Ausgabe darf man gefahrlos weitergeben."""
    url, token = "http://192.0.2.7:8123", "SEHR-GEHEIMER-TOKEN"
    ha_deploy.pruefen_und_neu_laden(url, token, False, aufruf=_Ha())
    ha_deploy.pruefen_und_neu_laden(url, token, False, aufruf=_Ha(pruefung="invalid"))
    # Echte Fehlertexte (etwa bei SSL) nennen oft den Host – genau das darf nicht durch.
    fehler = urllib.error.URLError("hostname '192.0.2.7' doesn't match certificate")
    ha_deploy.pruefen_und_neu_laden(url, token, False, aufruf=_Ha(fehler=fehler))
    ausgabe = capsys.readouterr()
    for geheim in (token, "192.0.2.7"):
        assert geheim not in ausgabe.out + ausgabe.err


@pytest.mark.parametrize(
    "cfg,anzahl,erwartet_aufrufe",
    [
        ({"HA_URL": "http://ha", "HA_TOKEN": "t"}, 2, 1),
        ({"HA_URL": "http://ha"}, 2, 0),
        ({"HA_TOKEN": "t"}, 2, 0),
        ({"HA_URL": "http://ha", "HA_TOKEN": "t"}, 0, 0),  # nichts kopiert → HA nicht stören
    ],
)
def test_main_spricht_ha_nur_mit_url_token_und_dateien_an(monkeypatch, cfg, anzahl, erwartet_aufrufe):
    aufrufe = []
    monkeypatch.setattr(ha_deploy, "einstellungen", lambda: {"HA_BLUEPRINT_ZIEL": "/x", **cfg})
    monkeypatch.setattr(ha_deploy, "kopieren", lambda ziel, trocken: anzahl)
    monkeypatch.setattr(ha_deploy, "pruefen_und_neu_laden",
                        lambda url, token, trocken: aufrufe.append(url) or 0)
    assert ha_deploy.main([]) == 0
    assert len(aufrufe) == erwartet_aufrufe


def test_ohne_ziel_abbruch(monkeypatch, tmp_path):
    monkeypatch.setattr(ha_deploy, "ENV_DATEI", tmp_path / "fehlt.env")
    monkeypatch.delenv("HA_BLUEPRINT_ZIEL", raising=False)
    assert ha_deploy.main([]) == 2
