"""Gemeinsame Test-Hilfen.

Kernidee (wie bei wled-matrix-display): Die Tests rendern die Jinja-Vorlagen
**direkt aus den Blueprint-Dateien** statt aus Kopien. Ändert jemand einen
Blueprint, ändern sich die Tests mit.

Dafür wird die Template-Umgebung von Home Assistant so weit nachgebaut, wie die
Blueprints sie nutzen:

* ``!input`` wird beim YAML-Laden als Platzhalter ``("INPUT", name)`` eingelesen
* ``states``, ``state_attr``, ``is_state``, ``has_value`` aus einer Zustandstabelle
* Mathematik: ``sin``, ``cos``, ``acos``, ``pi``, ``clamp``
* ``float`` als Funktion und Filter **wie in HA**: Mit Standardwert liefert es
  bei unbrauchbarer Eingabe den Standardwert, ohne Standardwert ist das ein
  Fehler. (Jinja selbst liefert stattdessen still 0.0 – das würde Fehler in
  den Vorlagen verdecken.)
* HA gibt Vorlagen als native Python-Typen zurück, nicht als Zeichenkette –
  das macht ``native()`` nach.

Beleg für die nachgebauten Funktionen: Skill ``sonnengeometrie``, Abschnitt 5.
Weicht der Nachbau von HA ab, ist ein Test wertlos. Die CI fängt das NICHT ab:
``check_config`` prüft Aufbau und Schema, wertet aber keine Vorlage aus. Ob der
Nachbau stimmt, zeigen nur der Beleg in der HA-Doku und die Live-Prüfung
(docs/ENTWURF.md 7.5) bzw. der Test im echten HA (Skill ha-testen).
"""

from __future__ import annotations

import ast
import math
import re
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

REPO = Path(__file__).resolve().parent.parent
BLUEPRINT_ORDNER = REPO / "blueprints"


def blueprint_dateien() -> list[Path]:
    """Alle Blueprints per Muster – dieselbe Regel wie im Release-Workflow."""
    return sorted(BLUEPRINT_ORDNER.glob("**/*.yaml"))


# --------------------------------------------------------------------------
# YAML mit !input laden
# --------------------------------------------------------------------------
class BlueprintLoader(yaml.SafeLoader):
    """SafeLoader, der ``!input xyz`` als ``('INPUT', 'xyz')`` einliest."""


BlueprintLoader.add_constructor(
    "!input", lambda loader, node: ("INPUT", loader.construct_scalar(node))
)


def load_blueprint(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=BlueprintLoader)


def input_names(path: Path) -> set[str]:
    """Alle per ``!input`` referenzierten Namen aus dem Dateitext."""
    return set(re.findall(r"!input\s+(\w+)", path.read_text(encoding="utf-8")))


def all_inputs(blueprint: dict) -> dict:
    """Alle Eingaben flach – auch die in Abschnitten (``input: {abschnitt: {input: …}}``).

    Abschnitte sind nur zum Aufräumen der Oberfläche da. Tests sollen nicht
    umgeschrieben werden müssen, wenn ein Feld in einen anderen Abschnitt wandert.
    """
    flach: dict = {}
    for name, feld in (blueprint["blueprint"].get("input") or {}).items():
        if isinstance(feld, dict) and "input" in feld and "selector" not in feld:
            flach.update(feld["input"])
        else:
            flach[name] = feld
    return flach


def find_input(blueprint: dict, name: str) -> dict:
    try:
        return all_inputs(blueprint)[name]
    except KeyError:
        raise KeyError(f"Eingabe nicht gefunden: {name}") from None


def input_default(blueprint: dict, name: str) -> Any:
    """Standardwert einer Eingabe – damit Tests keine zweite Kopie pflegen."""
    return find_input(blueprint, name)["default"]


# --------------------------------------------------------------------------
# Zustandstabelle (das "Home Assistant" der Tests)
# --------------------------------------------------------------------------
class FakeHass:
    """Minimale Zustandstabelle: Entity -> (state, attribute)."""

    def __init__(self, states: dict[str, tuple[str, dict]] | None = None):
        self.states: dict[str, tuple[str, dict]] = states or {}

    def set(self, entity: str, state: str, **attrs: Any) -> "FakeHass":
        self.states[entity] = (state, attrs)
        return self

    # --- HA-Funktionen -------------------------------------------------
    def fn_states(self, entity: str) -> str:
        return self.states.get(entity, ("unknown", {}))[0]

    def fn_state_attr(self, entity: str, attr: str) -> Any:
        return self.states.get(entity, ("unknown", {}))[1].get(attr)

    def fn_is_state(self, entity: str, value: str) -> bool:
        return self.fn_states(entity) == value

    def fn_has_value(self, entity: str) -> bool:
        """HA: Entität existiert und ist weder ``unavailable`` noch ``unknown``."""
        return entity in self.states and self.states[entity][0] not in ("unavailable", "unknown")


# --------------------------------------------------------------------------
# Jinja-Umgebung wie in Home Assistant
# --------------------------------------------------------------------------
_KEIN_STANDARD = object()


def ha_float(value: Any, default: Any = _KEIN_STANDARD) -> Any:
    """``float`` wie in HA: Standardwert bei Fehlschlag, sonst Fehler."""
    try:
        return float(value)
    except (ValueError, TypeError):
        if default is _KEIN_STANDARD:
            raise ValueError(f"float got invalid input '{value}' and no default was specified")
        return default


def ha_clamp(value: Any, min_value: Any, max_value: Any) -> float:
    """``clamp(wert, min, max)`` wie in HA."""
    return max(float(min_value), min(float(max_value), float(value)))


def make_env(hass: FakeHass) -> Environment:
    env = Environment(undefined=StrictUndefined)
    # sin/cos/acos absichtlich OHNE Standardwert (HA kennt einen): acos(x, 0)
    # lieferte außerhalb [-1, 1] still 0 = volle Sonne und verdeckte eine
    # fehlende Begrenzung. Skill sonnengeometrie, Abschnitt 2.
    mathe = {
        "sin": lambda x: math.sin(float(x)),
        "cos": lambda x: math.cos(float(x)),
        # acos wirft außerhalb [-1, 1] einen Fehler – genau das soll ein Test
        # sehen, wenn die Begrenzung in der Vorlage fehlt.
        "acos": lambda x: math.acos(float(x)),
        "clamp": ha_clamp,
        "float": ha_float,
    }
    env.filters.update(mathe)
    env.globals.update(mathe)
    env.globals.update(
        pi=math.pi,
        states=hass.fn_states,
        state_attr=hass.fn_state_attr,
        is_state=hass.fn_is_state,
        has_value=hass.fn_has_value,
    )
    env.filters["has_value"] = hass.fn_has_value
    env.tests["is_state"] = hass.fn_is_state
    env.tests["has_value"] = hass.fn_has_value
    return env


def native(text: str) -> Any:
    """Wie HA: Ergebnis in einen Python-Typ umwandeln, sonst getrimmter Text."""
    stripped = text.strip()
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError):
        return stripped


def render(template: str, hass: FakeHass, **context: Any) -> Any:
    return native(make_env(hass).from_string(template).render(**context))
