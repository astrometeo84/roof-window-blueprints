"""Logik der Vorlagen.

Zuerst die Prüfung des Nachbaus aus conftest.py: Verhält er sich nicht wie
Home Assistant, sind alle Vorlagentests wertlos. Beleg für das HA-Verhalten:
Skill ``sonnengeometrie``, Abschnitt 5. Danach je Blueprint eine Klasse.
"""

from __future__ import annotations

import math

import pytest

from conftest import (
    BLUEPRINT_ORDNER,
    FakeHass,
    all_inputs,
    blueprint_variablen,
    input_default,
    load_blueprint,
    native,
    render,
)

SONNENEINFALL = BLUEPRINT_ORDNER / "template" / "dachfenster" / "flaeche_sonneneinfall.yaml"


@pytest.fixture
def hass() -> FakeHass:
    return (
        FakeHass()
        .set("sun.sun", "above_horizon", elevation=30.0, azimuth=180.0)
        .set("sensor.weg", "unavailable")
        .set("sensor.unbekannt", "unknown")
    )


class TestNachbau:
    def test_mathe_im_bogenmass(self, hass):
        assert render("{{ sin(pi / 2) }}", hass) == pytest.approx(1.0)
        assert render("{{ (pi / 3) | cos }}", hass) == pytest.approx(0.5)
        assert render("{{ acos(0.5) * 180 / pi }}", hass) == pytest.approx(60.0)

    def test_acos_ausserhalb_wirft(self, hass):
        """Genau das muss ein Test sehen, wenn die Begrenzung vor acos fehlt."""
        with pytest.raises(ValueError):
            render("{{ acos(1.0000000002) }}", hass)

    def test_clamp(self, hass):
        assert render("{{ clamp(1.0000000002, -1, 1) }}", hass) == 1.0
        assert render("{{ clamp(-3, -1, 1) }}", hass) == -1.0
        assert render("{{ clamp(0.25, -1, 1) }}", hass) == 0.25

    def test_float_mit_standard(self, hass):
        assert render("{{ states('sensor.weg') | float(0) }}", hass) == 0
        assert render("{{ float('2.5', 0) }}", hass) == 2.5

    def test_float_ohne_standard_ist_ein_fehler(self, hass):
        """Jinja selbst gäbe still 0.0 zurück – HA nicht."""
        with pytest.raises(ValueError):
            render("{{ 'abc' | float }}", hass)

    def test_has_value(self, hass):
        assert render("{{ has_value('sun.sun') }}", hass) is True
        assert render("{{ has_value('sensor.weg') }}", hass) is False
        assert render("{{ has_value('sensor.unbekannt') }}", hass) is False
        assert render("{{ has_value('sensor.gibt_es_nicht') }}", hass) is False

    def test_state_attr(self, hass):
        assert render("{{ state_attr('sun.sun', 'elevation') }}", hass) == 30.0
        assert render("{{ state_attr('sun.sun', 'fehlt') is none }}", hass) is True

    def test_native(self):
        assert native(" 10.0 ") == 10.0
        assert native("True") is True
        assert native("unavailable") == "unavailable"

    def test_pi(self, hass):
        assert render("{{ pi }}", hass) == pytest.approx(math.pi)


def test_eingaben_auch_in_abschnitten():
    """all_inputs/input_default finden Eingaben mit und ohne Abschnitte."""
    bp = {
        "blueprint": {
            "input": {
                "flach": {"selector": {"number": {}}, "default": 1},
                "abschnitt": {"name": "A", "input": {"innen": {"selector": {}, "default": 2}}},
            }
        }
    }
    assert set(all_inputs(bp)) == {"flach", "innen"}
    assert input_default(bp, "innen") == 2


# ==========================================================================
# 4.1 Fläche – Sonneneinfall
# ==========================================================================
def _sonne(elevation, azimuth, zustand=None) -> FakeHass:
    """sun.sun wie in HA: Höhe und Azimut als Attribute (Skill sonnengeometrie, 3)."""
    if zustand is None:
        zustand = "above_horizon" if elevation > -0.833 else "below_horizon"
    return FakeHass().set("sun.sun", zustand, elevation=elevation, azimuth=azimuth)


@pytest.fixture(scope="module")
def bp():
    return load_blueprint(SONNENEINFALL)


class TestFlaecheSonneneinfall:
    """Baustein 4.1. Die Vorlagen kommen direkt aus der Blueprint-Datei."""

    def _rechne(self, bp, hass, azimut, neigung):
        """Zustand, Attribute und Verfügbarkeit, wie HA sie aus dem Blueprint rendert."""
        kontext = blueprint_variablen(bp, {"azimut": azimut, "neigung": neigung})
        sensor = bp["sensor"]
        return {
            "state": render(sensor["state"], hass, **kontext),
            "availability": render(sensor["availability"], hass, **kontext),
            **{name: render(vorlage, hass, **kontext)
               for name, vorlage in sensor["attributes"].items()},
        }

    # --- Testwerte aus docs/ENTWURF.md 4.1 (äußere Vorgabe) --------------
    @pytest.mark.parametrize(
        ("a_f", "beta", "a_s", "h", "theta"),
        [
            (180, 40, 180, 60, 10.0),
            (180, 40, 0, 10, 120.0),   # Sonne hinter der Fläche
            (0, 0, 0, 30, 60.0),       # Neigung 0: Azimute egal …
            (270, 0, 123, 30, 60.0),   # … auch andere
            (90, 90, 90, 10, 10.0),
        ],
    )
    def test_testwerte_aus_dem_entwurf(self, bp, a_f, beta, a_s, h, theta):
        werte = self._rechne(bp, _sonne(h, a_s), a_f, beta)
        assert werte["state"] == pytest.approx(theta, abs=1e-9)
        assert werte["cos_einfall"] == pytest.approx(math.cos(math.radians(theta)), abs=1e-4)
        assert werte["availability"] is True

    def test_eine_nachkommastelle(self, bp):
        # cos θ = sin 30° · cos 40° + cos 30° · sin 40° · cos 37°: θ = 32,4…°
        werte = self._rechne(bp, _sonne(30, 217), 180, 40)
        assert werte["state"] == round(werte["state"], 1)
        erwartet = math.degrees(math.acos(
            math.sin(math.radians(30)) * math.cos(math.radians(40))
            + math.cos(math.radians(30)) * math.sin(math.radians(40)) * math.cos(math.radians(37))))
        assert werte["state"] == round(erwartet, 1)
        assert werte["state"] != pytest.approx(erwartet, abs=1e-6), "nicht gerundet"

    # --- Begrenzung vor acos (Skill sonnengeometrie, 2) ------------------
    # Diese Werte ergeben in Gleitkomma-Rechnung cos θ = 1.0000000000000002
    # bzw. -1.0000000000000002 (gesucht mit derselben Rechenreihenfolge wie die
    # Vorlage). Ohne Begrenzung wirft acos.
    def test_cos_knapp_ueber_eins(self, bp):
        werte = self._rechne(bp, _sonne(82, 180), 180, 8)
        assert werte["state"] == 0.0
        assert werte["cos_einfall"] == 1.0

    def test_cos_knapp_unter_minus_eins(self, bp):
        werte = self._rechne(bp, _sonne(-82, 0), 180, 8)
        assert werte["state"] == 180.0
        assert werte["cos_einfall"] == -1.0
        assert werte["sonne_trifft_flaeche"] is False

    # --- Zählweise --------------------------------------------------------
    @pytest.mark.parametrize("a_s", [0, 45, 135, 200, 359])
    def test_azimut_0_und_360_sind_gleich(self, bp, a_s):
        a = self._rechne(bp, _sonne(25, a_s), 0, 50)
        b = self._rechne(bp, _sonne(25, a_s), 360, 50)
        assert a["state"] == b["state"]
        assert a["cos_einfall"] == b["cos_einfall"]

    @pytest.mark.parametrize(("a_s", "h"), [(0, 5), (90, 30), (180, 60), (300, 45)])
    def test_neigung_0_ist_90_minus_hoehe(self, bp, a_s, h):
        for a_f in (0, 90, 180, 270):
            assert self._rechne(bp, _sonne(h, a_s), a_f, 0)["state"] == pytest.approx(90 - h)

    def test_neigung_90_senkrechte_fassade(self, bp):
        # cos θ = cos h · cos(A_s − A_f) = cos 20° · cos 60°
        werte = self._rechne(bp, _sonne(20, 120), 180, 90)
        erwartet = math.degrees(math.acos(math.cos(math.radians(20)) * math.cos(math.radians(60))))
        assert werte["state"] == round(erwartet, 1)

    def test_kompass_im_uhrzeigersinn(self, bp):
        """Ostfläche: Morgensonne (Osten) trifft, Abendsonne (Westen) nicht."""
        morgen = self._rechne(bp, _sonne(20, 90), 90, 60)
        abend = self._rechne(bp, _sonne(20, 270), 90, 60)
        assert morgen["sonne_trifft_flaeche"] is True
        assert abend["sonne_trifft_flaeche"] is False
        assert morgen["state"] < 90 < abend["state"]

    # --- sonne_trifft_flaeche --------------------------------------------
    def test_sonne_trifft_flaeche_bei_sonne_vor_der_flaeche(self, bp):
        assert self._rechne(bp, _sonne(60, 180), 180, 40)["sonne_trifft_flaeche"] is True

    def test_nachts_trifft_keine_sonne_auch_wenn_cos_positiv(self, bp):
        """Sonne unter dem Horizont, aber „vor“ einer steilen Fläche: cos θ > 0."""
        werte = self._rechne(bp, _sonne(-5, 180), 180, 90)
        assert werte["cos_einfall"] > 0
        assert werte["sonne_trifft_flaeche"] is False

    def test_hoehe_genau_null_trifft_nicht(self, bp):
        werte = self._rechne(bp, _sonne(0, 180), 180, 90)
        assert werte["cos_einfall"] == pytest.approx(1.0)
        assert werte["sonne_trifft_flaeche"] is False

    def test_theta_genau_90_trifft_nicht(self, bp):
        # Sonne 40° hoch, genau gegenüber einer 40°-Fläche: cos θ = 0 exakt.
        werte = self._rechne(bp, _sonne(40, 0), 180, 40)
        assert werte["state"] == 90.0
        assert werte["cos_einfall"] == 0
        assert werte["sonne_trifft_flaeche"] is False

    def test_rundungsrauschen_bei_90_grad_trifft_nicht(self, bp):
        """cos 90° ist in Gleitkomma 6e-17, nicht 0 (Skill sonnengeometrie, 2).

        Senkrechte Südfassade, Sonne genau im Osten: streifend, θ = 90°. Ohne
        Rundung von cos θ vor dem Vergleich wäre „trifft“ wahr.
        """
        werte = self._rechne(bp, _sonne(10, 90), 180, 90)
        assert werte["state"] == 90.0
        assert werte["sonne_trifft_flaeche"] is False

    def test_cos_einfall_auf_vier_stellen(self, bp):
        werte = self._rechne(bp, _sonne(30, 217), 180, 40)
        assert werte["cos_einfall"] == round(werte["cos_einfall"], 4)
        assert werte["cos_einfall"] == pytest.approx(math.cos(math.radians(werte["state"])), abs=2e-3)

    # --- Zustand, Attribute und Verfügbarkeit passen zusammen ------------
    @pytest.mark.parametrize("a_s", range(0, 360, 45))
    @pytest.mark.parametrize("h", [-30, -1, 1, 15, 45, 89])
    def test_zustand_und_attribute_stimmen_ueberein(self, bp, a_s, h):
        """Die Formel steht in Zustand und Attributen; alle drei müssen gleich rechnen."""
        werte = self._rechne(bp, _sonne(h, a_s), 200, 35)
        assert math.cos(math.radians(werte["state"])) == pytest.approx(werte["cos_einfall"], abs=2e-3)
        assert werte["sonne_trifft_flaeche"] is (h > 0 and werte["cos_einfall"] > 0)

    def test_attribute_zeigen_die_eingaben(self, bp):
        werte = self._rechne(bp, _sonne(30, 180), 135, 22.5)
        assert werte["azimut"] == 135
        assert werte["neigung"] == 22.5

    # --- fehlender Sonnenstand (Skill sonnengeometrie, 3) ----------------
    @pytest.mark.parametrize(
        "hass",
        [
            FakeHass(),                                                        # sun.sun fehlt
            FakeHass().set("sun.sun", "unavailable"),                          # ohne Attribute
            FakeHass().set("sun.sun", "unknown"),
            FakeHass().set("sun.sun", "above_horizon", azimuth=180.0),         # Höhe fehlt
            FakeHass().set("sun.sun", "above_horizon", elevation=30.0),        # Azimut fehlt
            FakeHass().set("sun.sun", "above_horizon", elevation="x", azimuth=180.0),
        ],
        ids=["fehlt", "unavailable", "unknown", "ohne_hoehe", "ohne_azimut", "kein_zahlwert"],
    )
    def test_ohne_sonnenstand_nicht_verfuegbar_und_kein_fehler(self, bp, hass):
        """Kein Fantasiewert und keine Fehlermeldung, sondern nicht verfügbar."""
        werte = self._rechne(bp, hass, 180, 40)
        assert werte["availability"] is False
        assert werte["state"] in (None, "None", "")
        assert werte["cos_einfall"] in (None, "None", "")
        assert werte["sonne_trifft_flaeche"] is False

    # --- Eingaben ----------------------------------------------------------
    def test_azimut_und_neigung_sind_pflicht(self, bp):
        """Kein Standardwert: Jede Fläche ist anders, ein Standard gäbe still falsche Winkel."""
        assert set(all_inputs(bp)) == {"azimut", "neigung"}
        for name in ("azimut", "neigung"):
            assert "default" not in all_inputs(bp)[name]
            ohne = {k: v for k, v in {"azimut": 180, "neigung": 40}.items() if k != name}
            with pytest.raises(KeyError):
                blueprint_variablen(bp, ohne)
