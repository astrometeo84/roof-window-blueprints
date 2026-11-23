# roof-window-blueprints

Home-Assistant-Blueprints rund um ein Dachfenster (roof window, skylight) mit Solar-Rollladen:

- **Fläche – Sonneneinfall** (Template-Blueprint): Einfallswinkel der Sonne auf eine beliebig
  ausgerichtete und geneigte Fläche.
- **Fläche – Helligkeit aus PV** (Template-Blueprint): Einstrahlung und Helligkeit auf der Dachfläche,
  geschätzt aus der Leistung einer PV-Anlage in derselben Ebene.
- **Beschattung** (Automations-Blueprint): Rollladen bei Sonne, Helligkeit und Wärme auf
  Beschattungsposition, mit wenigen Fahrten pro Tag.
- **Dachfenster offen – Warnung** (Automations-Blueprint): Meldung bei Regen, beim Weggehen, am Abend
  und bei Wetterwarnungen, solange das Fenster offen ist.

> **Stand:** im Aufbau. Noch ist kein Blueprint veröffentlicht; die Liste oben beschreibt das Ziel
> (`docs/ENTWURF.md`).

## Installation

_Folgt mit dem ersten Blueprint._ Jede Blueprint-Datei hängt am jeweiligen
[GitHub-Release](../../releases). Automations-Blueprints lassen sich über die Oberfläche importieren;
Template-Blueprints werden in `configuration.yaml` unter `template:` mit `use_blueprint:`
eingebunden (Anleitung in `docs/anleitung.md`).

## Voraussetzungen

- Home Assistant (Mindestversion steht in jedem Blueprint unter `homeassistant: min_version`)
- Sun-Integration (Sonnenstand)
- für die Helligkeit: ein Leistungssensor der PV-Module **dieser** Dachfläche (DC-Seite)

## Mitmachen

Siehe [CONTRIBUTING.md](CONTRIBUTING.md). Kurz:

```bash
uv sync --locked
uv run pytest
uv run yamllint --strict .
```

## Lizenz

MIT, siehe [LICENSE](LICENSE).
