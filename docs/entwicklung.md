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
- `tests/test_struktur.py`: Versionskopf, Release-Kette, eindeutige Dateinamen, nur `.yaml`
  unter `blueprints/`, Form der CI-Fixtures (die Prüfung der Eingaben je Blueprint – nur echte
  Eingaben, vollständige und minimale Instanz, `use_blueprint`-Pfad – kommt mit dem ersten
  Blueprint in Etappe 3), Zugangsdaten.
- `tests/test_deploy.py`: `scripts/ha_deploy.py` ohne Netz.
- Die CI lässt zusätzlich echtes Home Assistant die Konfiguration prüfen. Grenze: Bei
  Template-Blueprints wird dieser Job nie rot – Schemafehler verwirft HA still, Ladefehler sind
  nur Warnungen (Skill `sonnengeometrie`, Abschnitt 5); bei Automations-Blueprints vermutlich
  ähnlich (Gegenprobe in Etappe 6). Vorlagen wertet `check_config` gar nicht aus; ob der Nachbau
  in `conftest.py` zu HA passt, zeigt nur das echte HA. Die Tests sind die eigentliche Sicherung.

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
| 2 | `ha_deploy.py`: gescheitertes scp nicht abgefangen (Traceback mit Adresse) | `test_scp_fehler_ohne_adresse_und_mit_hinweis` |
| 2 | `ha_deploy.py`: Antwort der Prüfung ohne dict gilt als gültig | `test_unerwartete_antwort_der_pruefung_laedt_nichts` |
| 2 | `ha_deploy.py`: Neuladen schon mit `HA_URL` ohne `HA_TOKEN` | `test_main_spricht_ha_nur_mit_url_token_und_dateien_an` |
| 2 | Blueprint mit Endung `.yml` | `test_unter_blueprints_nur_yaml_dateien` |
| 2 | Netzfehler-Text mit Hostnamen ausgegeben – **erst nicht erkannt** (Test nutzte Fehler ohne Host), Test nachgeschärft | `test_gibt_weder_token_noch_adresse_aus` |

## Workflows

Die Dateien unter `.github/workflows/` legt der Repo-Inhaber an (die GitHub App von Claude Code darf
sie nicht ändern). Inhalt und Begründungen: `docs/ENTWURF.md` Abschnitt 6.

## Versionen

Die Version steht nur im Kopf jeder Blueprint-Datei; release-please hebt sie an. Die
Release-Kette (Markierung, `extra-files`, Upload per Muster, `scripts/check_version.py`) prüft
`tests/test_struktur.py`.
