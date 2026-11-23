"""Logik der Vorlagen.

Bis die Blueprints kommen (Etappen 3 ff.), steht hier nur die Prüfung des
Nachbaus aus conftest.py: Verhält er sich nicht wie Home Assistant, sind alle
späteren Vorlagentests wertlos. Beleg für das HA-Verhalten: Skill
``sonnengeometrie``, Abschnitt 5.
"""

from __future__ import annotations

import math

import pytest

from conftest import FakeHass, all_inputs, input_default, native, render


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
