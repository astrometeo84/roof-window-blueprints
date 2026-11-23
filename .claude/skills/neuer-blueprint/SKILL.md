---
name: neuer-blueprint
description: Neuen Blueprint (Template oder Automation) zu roof-window-blueprints hinzufügen oder einen bestehenden um eine Eingabe erweitern. Listet jede Stelle in Blueprint, Release-Kette, Tests, CI-Fixtures und Doku, die dabei angefasst werden muss, und endet mit der Gegenprobe.
---

# Neuer Blueprint oder neue Eingabe

Ein Blueprint berührt immer dieselben Stellen. Fehlt eine, merkt man es oft erst in der CI, beim
Release oder gar nicht. Liste der Reihe nach abarbeiten. Vorlage für Aufbau und Stil ist der
Blueprint, der dem neuen am nächsten kommt. Verbindlich ist `docs/ENTWURF.md`; weicht etwas davon
ab, erst fragen, dann die Spezifikation nachziehen.

## 1. Test zuerst

In `tests/test_vorlagen.py` eine Klasse `Test<Blueprint>`. Mindestens:

- die Testwerte aus `docs/ENTWURF.md` Abschnitt 4 (einmal ausgeschrieben, als äußere Vorgabe)
- Randfälle aus dem Skill `sonnengeometrie` und `unavailable`/`unknown` je Eingabe-Entität
- Schwellen: inklusiv oder exklusiv, wie spezifiziert, beide Seiten getestet
- Standardwerte über `input_default()`, nie abschreiben

Prüfen, dass die Tests **fehlschlagen**, bevor der Blueprint fertig ist.

## 2. Blueprint-Datei

Ort: `blueprints/template/dachfenster/<name>.yaml` oder
`blueprints/automation/dachfenster/<name>.yaml`.

1. **Versionskopf** ganz oben, genau so (siehe `docs/ENTWURF.md` 6.4):
   ```yaml
   # Version: 0.0.0 # x-release-please-version
   #
   # Die Zeile darüber pflegt release-please automatisch. Die Markierung
   # "x-release-please-version" nicht entfernen; scripts/check_version.py
   # prüft beim Release, dass sie zum Tag passt.
   ```
   Bei einem neuen Blueprint die aktuelle Version aus `.release-please-manifest.json` eintragen.
2. **`blueprint:`** mit `name`, `description` (Deutsch, mit Grenzen und Stolperfallen),
   `domain`, `author`, `source_url`, `homeassistant: min_version:` nach den genutzten Funktionen.
3. **Eingaben:** jede mit `name`, `description`, `selector` und – wo sinnvoll – `default`
   (Standardwerte aus der Spezifikation). Einheiten in `selector.number.unit_of_measurement`.
   Kompass-Azimut 0–360, Neigung 0–90.
4. **Vorlagen:** Grad → Bogenmaß per `pi / 180`, Begrenzung vor `acos`, `availability` für
   fehlende Eingaben. Begründungen als Kommentar, damit niemand sie „aufräumt“.
5. Keine echten Entitäts-IDs, Koordinaten oder Anlagenwerte – nur Beispielwerte.

Neue Eingabe in einem bestehenden Blueprint: umbenennen oder entfernen bricht Einrichtungen →
`feat!:` plus `BREAKING CHANGE:`. Neue Eingaben brauchen einen Standardwert, sonst bricht es
ebenfalls.

## 3. Release-Kette (nur bei neuem Blueprint)

- `.release-please-config.json` → `extra-files`: Pfad ergänzen. **Das ist die einzige Stelle.**
  `tests/test_struktur.py::test_extra_files_nennt_genau_die_blueprints` schlägt an, wenn er fehlt.
- Nichts zu tun in `scripts/check_version.py` und im Release-Workflow: Beide nehmen alle Dateien
  unter `blueprints/` per Muster (`blueprints/**/*.yaml`). Der Workflow muss dafür **nicht**
  geändert werden.
- Dafür muss der **Dateiname** unter `blueprints/` eindeutig sein, auch über Automation und
  Template hinweg: Release-Anhänge haben keine Ordner, und `--clobber` überschriebe eine
  gleichnamige Datei still (`test_blueprint_dateinamen_sind_eindeutig`).
- Ordner nur `blueprints/automation/dachfenster/` oder `blueprints/template/dachfenster/`
  (`test_blueprint_liegt_in_bekanntem_ordner`); andere kopiert die CI nicht.

## 4. Tests nachziehen

- `tests/conftest.py`: benötigte Zustände in `FakeHass`, ggf. fehlende Jinja-Funktionen
  nachbauen (genau wie HA, mit Beleg im Skill `sonnengeometrie`).
- `tests/test_struktur.py`: Eingaben, Selektoren, Standardwerte, Versionskopf.

## 5. CI-Fixtures

- Template-Blueprint: `tests/fixtures/configuration.yaml` → `template:` → `use_blueprint:`,
  eine minimale und eine vollständig belegte Instanz. `path:` relativ zu
  `blueprints/template/`, also `dachfenster/<name>.yaml`. Achtung: Passt eine Instanz nicht zum
  Schema, bleibt die CI grün; ein falscher `path` wird nur dank `--fail-on-warnings` rot (laut Quelltext, Gegenprobe Etappe 3; Skill
  `sonnengeometrie` Abschnitt 5) – Aufbau und Optionen deshalb in `tests/test_struktur.py`
  selbst prüfen.
- Automations-Blueprint: `tests/fixtures/automations.yaml`, eine Instanz minimal, eine
  vollständig (jede Eingabe belegt).
- Referenzierte Entitäten als Template-Sensoren in `configuration.yaml` anlegen.
- Nur Eingaben, die es wirklich gibt.
- Kopierziel im Workflow (`ha/blueprints/<domain>/dachfenster/`) kopiert beide Ordner per
  Muster; nur ein neuer Ordner bräuchte eine Workflow-Änderung (dann als Text an den Nutzer).

## 6. Doku

- `README.md`: Funktionsliste, Import-Link.
- `docs/anleitung.md`: Checkliste, `use_blueprint`-Beispiel (Pfad nach dem Import:
  `blueprints/<domain>/<autor>/…`), „Gut zu wissen“, Fehlersuche.
- `docs/entwicklung.md`: Physik bzw. Logik, falls neu.

## 7. Gegenprobe und Abschluss

1. Blueprint an den wichtigen Stellen absichtlich kaputt machen (Begrenzung vor `acos` entfernt,
   Grad statt Bogenmaß, Schwelle exklusiv statt inklusiv, `availability` entfernt, W/kW-Erkennung
   wirkungslos …) und prüfen, dass `uv run pytest` anschlägt. Dafür `git stash` oder
   `git worktree`, nie `git checkout --` oder `git restore`.
2. Erkannte Fehler in die Tabelle „Taugen die Tests etwas?“ in `docs/entwicklung.md`.
3. ```bash
   uv run pytest && uv run yamllint --strict .
   ```
4. Subagent `test-manager`, bei Vorlagen/Physik/Selektoren zusätzlich `ha-experte`.
5. Commit-Vorschlag: `feat: <Blueprint> …`. Der Nutzer testet im echten HA (Skill `ha-testen`)
   vor dem Merge.
