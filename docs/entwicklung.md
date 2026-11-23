# Entwicklung

Gerüst aus Etappe 2; ausgebaut wird diese Datei in Etappe 8 (`docs/ENTWURF.md` Abschnitt 9).
Verbindlich ist `docs/ENTWURF.md`, die Fachgrundlagen stehen im Skill
`.claude/skills/sonnengeometrie/SKILL.md`.

## Physik

### Fläche – Sonneneinfall (4.1)

```
cos θ = sin(h) · cos(β) + cos(h) · sin(β) · cos(A_s − A_f)
θ     = acos(cos θ)
```

h und A_s aus den Attributen `elevation`/`azimuth` von `sun.sun`, β und A_f aus den Eingaben;
alles in Grad, in der Vorlage mit `pi / 180` ins Bogenmaß. cos θ wird vor `acos` mit `clamp`
auf [−1, 1] begrenzt. Eigenheiten (Rundungsrauschen bei 90°, h > 0, Formel dreimal im
Blueprint, Verhalten ohne Sonnenstand) und Belege: Skill `sonnengeometrie`, Abschnitte 2 und 3.

_Helligkeit aus PV (4.2) folgt in Etappe 4._

## Testaufbau

- Die Tests lesen die Jinja-Vorlagen direkt aus den Blueprint-Dateien (`tests/conftest.py`), keine
  Kopien. Standardwerte über `input_default()`.
- `conftest.py` baut nach, was die Vorlagen von Home Assistant nutzen: `states`, `state_attr`,
  `is_state`, `has_value`, `sin`, `cos`, `acos`, `pi`, `clamp`, `float` (mit HA-Verhalten: ohne
  Standardwert ist eine unbrauchbare Eingabe ein Fehler). `tests/test_vorlagen.py::TestNachbau`
  prüft den Nachbau selbst.
- `conftest.py::blueprint_variablen` löst den Abschnitt `variables:` eines Blueprints auf wie
  HA (`!input` → Wert der Eingabe, sonst Standardwert, sonst Fehler wie `MissingInput`).
- `tests/test_struktur.py`: Versionskopf, Release-Kette, eindeutige Dateinamen, nur `.yaml`
  unter `blueprints/`, Kopfdaten und `min_version`, jede Eingabe deklariert und benutzt, eine
  Entität je Template-Blueprint, Eingaben und Sensor-Optionen je Blueprint; CI-Fixtures: nur
  erlaubte Schlüssel, `use_blueprint`-Pfad vorhanden, nur echte Eingaben, Pflichteingaben
  belegt, je Template-Blueprint eine minimale und eine vollständige Instanz; Zugangsdaten.
- `tests/test_vorlagen.py`: je Blueprint eine Klasse, die Zustand, Attribute und
  `availability` aus der Blueprint-Datei rendert.
- `tests/test_deploy.py`: `scripts/ha_deploy.py` ohne Netz.
- Die CI lässt zusätzlich echtes Home Assistant die Konfiguration prüfen, mit
  `--fail-on-warnings`. Grenze: Schemafehler einer Template-Instanz verwirft HA still, die CI
  bleibt grün; Ladefehler (falscher `path`, fehlende Pflichteingabe) werden erst durch
  `--fail-on-warnings` rot – laut Quelltext, Gegenprobe in Etappe 3 (Skill `sonnengeometrie`, Abschnitt 5); bei Automations-Blueprints
  vermutlich ähnlich (Gegenprobe in Etappe 6). Vorlagen wertet `check_config` gar nicht aus; ob der Nachbau
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
| 2 | `ha_deploy.py`: Warnungen der Prüfung verschluckt | `test_warnungen_der_pruefung_werden_gezeigt` |
| 2 | `ha_deploy.py`: 401 ohne Hinweis auf Adminrechte | `test_401_nennt_token_und_adminrechte` |
| 2 | Blueprint mit Endung `.yml` | `test_unter_blueprints_nur_yaml_dateien` |
| 2 | Netzfehler-Text mit Hostnamen ausgegeben – **erst nicht erkannt** (Test nutzte Fehler ohne Host), Test nachgeschärft | `test_gibt_weder_token_noch_adresse_aus` |
| 2 | HA-Job ohne `--fail-on-warnings` / ohne Kopie der `secrets.yaml` / wieder mit `frenck/action-home-assistant` (Probe mit dem Workflow-Entwurf) | `test_ha_job_prueft_mit_fail_on_warnings` |
| 2 | `--entrypoint ""` entfernt – **erst nicht erkannt** (Test fand den Begriff im Kommentar, dann nur in einem der zwei `docker run`), Test nachgeschärft: nur Befehlszeilen, jeder Aufruf einzeln | `test_ha_job_prueft_mit_fail_on_warnings` |
| 2 | `setup-uv@v10` bzw. `@v7` statt vollständiger Version | `test_setup_uv_mit_vollstaendiger_version` |
| 2 | Exit-Code verschluckt (`--fail-on-warnings \|\| true`, `continue-on-error: true`), `--entrypoint` nur im Kommentar am Zeilenende – **erst nicht erkannt** (Befund `test-manager`), Test nachgeschärft | `test_ha_job_prueft_mit_fail_on_warnings` |
| 2 | `secrets.yaml` in falsches Ziel kopiert | `test_ha_job_prueft_mit_fail_on_warnings` |
| 2 | Release-Workflow als `.yaml` mit `setup-uv@v10` – **erst nicht erkannt** (feste Dateinamen, still übersprungen), jetzt per Muster | `test_setup_uv_mit_vollstaendiger_version` |
| 3 | Sonneneinfall: Begrenzung vor `acos` im Zustand entfernt | `test_cos_knapp_ueber_eins`, `test_cos_knapp_unter_minus_eins` |
| 3 | Sonneneinfall: Begrenzung in `cos_einfall` entfernt – **nicht erkennbar**: `round(4)` macht aus 1.0000000000000002 ohnehin 1.0; die Begrenzung bleibt, damit die drei Vorlagen gleich rechnen (Kommentar im Blueprint) | – |
| 3 | Sonneneinfall: Grad statt Bogenmaß | `test_testwerte_aus_dem_entwurf` und 14 weitere |
| 3 | Sonneneinfall: Prüfung h > 0 entfernt | `test_nachts_trifft_keine_sonne_auch_wenn_cos_positiv`, `test_hoehe_genau_null_trifft_nicht`, `test_zustand_und_attribute_stimmen_ueberein` |
| 3 | Sonneneinfall: h ≥ 0 statt h > 0 | `test_hoehe_genau_null_trifft_nicht` |
| 3 | Sonneneinfall: cos θ vor dem Vergleich nicht gerundet | `test_rundungsrauschen_bei_90_grad_trifft_nicht` |
| 3 | Sonneneinfall: `availability` immer wahr | `test_ohne_sonnenstand_nicht_verfuegbar_und_kein_fehler` |
| 3 | Sonneneinfall: Prüfung auf Zahl im Zustand entfernt (Vorlagenfehler ohne Sonnenstand) | `test_ohne_sonnenstand_nicht_verfuegbar_und_kein_fehler` |
| 3 | Sonneneinfall: im Zustand A_s + A_f statt A_s − A_f | `test_testwerte_aus_dem_entwurf`, `test_kompass_im_uhrzeigersinn`, `test_zustand_und_attribute_stimmen_ueberein` |
| 3 | Sonneneinfall: Zustand nicht auf eine Stelle gerundet | `test_eine_nachkommastelle`, `test_neigung_90_senkrechte_fassade`, `test_azimut_0_und_360_sind_gleich` |
| 3 | Sonneneinfall: Neigung und Azimut vertauscht | `test_testwerte_aus_dem_entwurf` und 9 weitere |
| 3 | Sonneneinfall: Standardwert für `azimut` | `test_azimut_und_neigung_sind_pflicht`, `test_sonneneinfall_eingaben`, `test_fixture_je_template_blueprint_minimal_und_vollstaendig` |
| 3 | `min_version` 2025.3.0 trotz `clamp` | `test_min_version_reicht_fuer_clamp` |
| 3 | Attribut `azimut` zeigt die Neigung | `test_attribute_zeigen_die_eingaben` |
| 3 | Fixture: falscher `path`, unbekannter Schlüssel, unbekannte Eingabe, fehlende Pflichteingabe | `test_fixture_template_instanzen_passen_zum_blueprint`, `test_fixture_je_template_blueprint_minimal_und_vollstaendig` |

## Workflows

Die Dateien unter `.github/workflows/` legt der Repo-Inhaber an (die GitHub App von Claude Code darf
sie nicht ändern). Inhalt und Begründungen: `docs/ENTWURF.md` Abschnitt 6.

## Versionen

Die Version steht nur im Kopf jeder Blueprint-Datei; release-please hebt sie an. Die
Release-Kette (Markierung, `extra-files`, Upload per Muster, `scripts/check_version.py`) prüft
`tests/test_struktur.py`.
