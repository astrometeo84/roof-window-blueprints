# Entwicklung

Gerüst aus Etappe 2; ausgebaut wird diese Datei in Etappe 8 (`docs/ENTWURF.md` Abschnitt 9).
Verbindlich ist `docs/ENTWURF.md`, die Fachgrundlagen stehen im Skill
`.claude/skills/sonnengeometrie/SKILL.md`.

## Physik

_Folgt mit den Template-Blueprints (Etappen 3 und 4)._

## Testaufbau

- Die Tests lesen die Jinja-Vorlagen direkt aus den Blueprint-Dateien (`tests/conftest.py`), keine
  Kopien. Standardwerte über `input_default()`.
- `conftest.py` baut nach, was die Vorlagen von Home Assistant nutzen: `states`, `state_attr`,
  `is_state`, `has_value`, `sin`, `cos`, `acos`, `pi`, `clamp`, `float` (mit HA-Verhalten: ohne
  Standardwert ist eine unbrauchbare Eingabe ein Fehler). `tests/test_vorlagen.py::TestNachbau`
  prüft den Nachbau selbst.
- `tests/test_struktur.py`: Versionskopf, Release-Kette, eindeutige Dateinamen, CI-Fixtures,
  Zugangsdaten.
- `tests/test_deploy.py`: `scripts/ha_deploy.py` ohne Netz.
- Die CI lässt zusätzlich echtes Home Assistant die Konfiguration prüfen. Grenze: Eine
  Template-Blueprint-Instanz mit unpassenden Eingaben verwirft HA still, ohne dass `check_config`
  einen Fehler meldet (Skill `sonnengeometrie`, Abschnitt 5).

## Taugen die Tests etwas?

Gegenproben: Code absichtlich kaputt gemacht (per `git stash` bzw. `git worktree`, nie
`git checkout --`/`git restore`) und geprüft, ob die Tests anschlagen.

| Etappe | Absichtlich eingebauter Fehler | Test, der anschlägt |
|---|---|---|
| 2 | Release-Workflow mit fester Dateiliste statt Muster | `test_release_workflow_haengt_alle_blueprints_per_muster_an` |
| 2 | `refactor` im CHANGELOG sichtbar | `test_sichtbare_changelog_abschnitte` |
| 2 | Blueprint fehlt in `extra-files` | `test_extra_files_nennt_genau_die_blueprints` |
| 2 | zwei Blueprints mit gleichem Dateinamen (automation/template) | `test_blueprint_dateinamen_sind_eindeutig` |
| 2 | Markierung `x-release-please-version` entfernt | `test_versionskopf_vorhanden`, `test_versionskopf_passt_zum_manifest` |
| 2 | `pyproject.toml` auf `version = "0.1.0"` | `test_pyproject_version_bleibt_eingefroren` |
| 2 | Projektversion in `uv.lock` auf `0.1.0` | `test_uv_lock_fuehrt_projektversion_null` |
| 2 | CONTRIBUTING: `perf` löst kein Release aus | `test_contributing_tabelle_passt_zur_konfiguration` |
| 2 | `ha_deploy.py` ohne `template/reload` | `test_laedt_automationen_und_templates_nach_der_pruefung` |
| 2 | Nachbau `float` ohne Standardwert liefert still 0.0 (wie Jinja) | `TestNachbau::test_float_ohne_standard_ist_ein_fehler` |

## Workflows

Die Dateien unter `.github/workflows/` legt der Repo-Inhaber an (die GitHub App von Claude Code darf
sie nicht ändern). Inhalt und Begründungen: `docs/ENTWURF.md` Abschnitt 6.

## Versionen

Die Version steht nur im Kopf jeder Blueprint-Datei; release-please hebt sie an. Die
Release-Kette (Markierung, `extra-files`, Upload per Muster, `scripts/check_version.py`) prüft
`tests/test_struktur.py`.
