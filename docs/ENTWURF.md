# ENTWURF – roof-window-blueprints

Stand: 21.11.2026 · Status: verbindliche Spezifikation, Änderungen nur per PR

Vorbilder: [`wled-matrix-display`](https://github.com/astrometeo84/wled-matrix-display) für Aufbau,
Tests und den automatischen Release-Workflow; [`aiocontrome`](https://github.com/astrometeo84/aiocontrome)
und `ha-controme-insights` für die Regeln und Rechte von Claude Code. Beide nur lesen.

## 1. Ziel

Home-Assistant-Blueprints rund um ein manuelles Dachfenster mit Solar-Rollladen:

1. **Sonneneinfall auf einer Fläche** berechnen (Einfallswinkel aus Sonnenstand, Ausrichtung und Neigung).
2. **Helligkeit auf einer Dachfläche** aus der Leistung einer PV-Anlage ableiten, die in derselben Ebene liegt.
3. **Beschattung** (Hitzeschutz) über den Rollladen steuern.
4. **Warnen**, wenn das Dachfenster offen ist (Regen, Weggehen, Abend, Wetterwarnung).

Vorbild für Aufbau, Werkzeuge und Doku:
[`astrometeo84/wled-matrix-display`](https://github.com/astrometeo84/wled-matrix-display) (öffentlich, nur lesen).

## 2. Hintergrund

Anlage, für die das Projekt entsteht (nur zur Orientierung, **keine echten Werte ins Repo**):

- Klapp-Schwingfenster VELUX GPU, **manuell**, ohne Motor und ohne Regensensor
  → nur warnen, nicht automatisch schließen.
- Solar-Außenrollladen VELUX SSL (io-homecontrol), in HA über VELUX KIG 300 und HomeKit-Controller.
  Der Rollladen sitzt auf dem Flügel, das Fenster lässt sich auch bei geschlossenem Rollladen öffnen
  → **keine Kollisionslogik**. Akku über Solarzelle → **wenige Fahrten** (2–4 pro Tag unkritisch).
- Fensterkontakt (Zigbee, Reedkontakt): `binary_sensor`, `on` = offen.
- PV-Anlage auf derselben Dachfläche wie das Fenster. Ausrichtung, Neigung und kWp sind in
  Solar Forecast ML (SFML) hinterlegt. SFML zählt den Azimut wie HA.
- Raumtemperatursensor, Wetter über Met.no, amtliche Warnungen über DWD-Warnwetter.

## 3. Entscheidungen

| Thema | Entscheidung | Begründung |
|---|---|---|
| Sonnengeometrie | Einfallswinkel auf die Fläche statt Azimut-/Höhenfenster | exakt für jede Ausrichtung und Neigung |
| Helligkeit | absolut (lx bzw. W/m²) aus PV-Leistung und kWp | Der Wärmeeintrag hängt von der Einstrahlung auf der Scheibe ab. Die PV liegt in derselben Ebene und misst genau diese. |
| Relative „sonnig“-Quote (Ansatz Smart Cover Automation) | nicht verwendet | sagt nur „sonnig ja/nein“, nicht wie stark; kennt die Ebene nicht |
| Raumtemperatur | nur Freigabe, kein Auslöser | läuft der Aufheizung hinterher, die Beschattung muss vorher greifen |
| Sensoren | Template-Blueprints | Automations-Blueprints können keine Entitäten anlegen |
| Stellschrauben (Schwellen, Position, Verzögerungen) | Eingaben im Automations-Blueprint | in der Oberfläche änderbar, keine Helfer nötig |
| Azimut-Zählweise | Kompass: 0 = N, 90 = O, 180 = S, 270 = W | wie HA und SFML |
| SFML | keinen Code übernehmen | proprietäre Lizenz, teils verschleiert; die Physik hier ist Lehrbuchwissen |
| Lizenz | MIT | wie wled-matrix-display |
| Release | automatisch mit release-please wie wled-matrix-display | Version, CHANGELOG, Tag und Release entstehen aus den Commits; der Release-PR ist eine Vorschau |
| Versionsnummer | nur im Kopf jeder Blueprint-Datei; `pyproject.toml` bleibt bei `version = "0"` | sonst läuft `uv.lock` weg und die CI ausgerechnet des Release-PR scheitert an `--locked` (Erfahrung aus wled-matrix-display) |
| Sprache | Doku, Blueprint-Texte, Commits und PRs auf Deutsch | wie wled-matrix-display; Zielgruppe deutschsprachig |
| Rechte von Claude Code | wie bei aiocontrome: Feature-Branches, PRs, keine Tags, keine Workflows | die GitHub App hat nur Contents und Pull requests |
| Prüf-Agenten | zwei schreibgeschützte Subagents nach dem Vorbild von aiocontrome: `test-manager` und `ha-experte`, vor jedem Push | unabhängige Gegenprüfung: wer den Code schreibt, prüft ihn nicht selbst |
| Live-Prüfung | optionale Tests gegen das echte HA, nur vom PC des Nutzers, nie in CI oder Container | macht die Prüfung im Winter wiederholbar; Muster aus aiocontrome |

## 4. Bausteine

### 4.1 Template-Blueprint „Fläche – Sonneneinfall“ (`sensor`)

**Eingaben**

- `azimut`: Ausrichtung der Fläche, 0–360° (Kompass)
- `neigung`: 0–90° (0 = waagerecht, 90 = senkrecht)

**Berechnung**

```
cos θ = sin(h) · cos(β) + cos(h) · sin(β) · cos(A_s − A_f)
θ     = acos(cos θ)
```

- h = Sonnenhöhe, A_s = Sonnenazimut (beide aus HA), β = Neigung, A_f = Azimut der Fläche
- Grad in Bogenmaß umrechnen; cos θ vor `acos` auf [−1, 1] begrenzen (Rundungsfehler)

**Ausgabe**

- Zustand: Einfallswinkel θ in ° mit einer Nachkommastelle
  (0 = Sonne senkrecht auf der Fläche, 90 = streifend, > 90 = Sonne hinter der Fläche)
- Attribute: `cos_einfall`, `sonne_trifft_flaeche` (wahr, wenn h > 0 und cos θ > 0),
  `azimut`, `neigung` (die eingetragenen Werte; zur Kontrolle und für die Live-Prüfung in 7.5)

**Testwerte**

| Fläche A_f / β | Sonne A_s / h | erwartetes θ |
|---|---|---|
| 180 / 40 | 180 / 60 | 10,0° |
| 180 / 40 | 0 / 10 | 120,0° (Sonne hinter der Fläche) |
| beliebig / 0 | beliebig / 30 | 60,0° |
| 90 / 90 | 90 / 10 | 10,0° |

Der Baustein gilt für jede Fläche, auch ohne PV (weitere Fenster, Fassaden).

### 4.2 Template-Blueprint „Fläche – Helligkeit aus PV“ (`sensor`)

**Eingaben**

- `pv_leistung`: Leistungssensor der Module **dieser** Fläche, DC-Seite; W oder kW, Einheit automatisch erkennen
- `kwp`: Spitzenleistung genau dieser Module
- `performance_ratio`: Standard 0,8 (Verluste durch Wechselrichter, Wärme, Leitungen)
- `lux_pro_w_m2`: Standard 110

**Berechnung**

```
G  = P[kW] / (kWp · PR) · 1000      # Einstrahlung auf die Fläche in W/m²
lx = G · lux_pro_w_m2
```

Negative Werte (Rauschen in der Nacht) auf 0 setzen.

**Ausgabe**

- Zustand: Helligkeit in lx (Vorgabe des Nutzers: Schwellen in Helligkeit, nicht in Watt)
- Attribute: `einstrahlung_w_m2`, `pv_leistung_kw` (der verwendete Wert), `kwp`,
  `performance_ratio` (für die Live-Prüfung in 7.5)
- `unavailable`, wenn der PV-Sensor nicht verfügbar ist

**Testwerte**

| P | kWp | PR | erwartet |
|---|---|---|---|
| 4 kW bzw. 4000 W | 10 | 0,8 | 500 W/m², 55 000 lx |
| 0 W | 10 | 0,8 | 0 lx |
| −15 W | 10 | 0,8 | 0 lx |
| unavailable | 10 | 0,8 | unavailable |

**Größenordnung** (für Doku und Standardwerte): bedeckter Himmel grob unter 20 000 lx, direkte Sonne
auf der Fläche ab etwa 40 000 lx. Die Umrechnung ist eine Schätzung (etwa ±15 %).

**Grenzen (gehören in die Doku)**

- nur Module derselben Ebene; bei mehreren Dachseiten den Sensor der passenden Gruppe bzw. des MPP-Trackers
- DC-Leistung verwenden, nicht Einspeisung oder Wechselrichter-Ausgang
- bei Nulleinspeisung mit vollem Akku regelt der Wechselrichter ab → Wert zu niedrig
- Schnee oder Teilverschattung der Module verfälschen den Wert

### 4.3 Automations-Blueprint „Beschattung“

**Eingaben** (Standardwerte sind Startwerte)

- Sensor aus 4.1, Sensor aus 4.2, Raumtemperatur, Rollladen (`cover`)
- `max_einfallswinkel`: 60°
- `helligkeit_schwelle`: 40 000 lx
- `temperatur_schwelle`: 23 °C
- `position_beschattung`: 20 % (HA: 0 = zu, 100 = offen)
- `position_offen`: 100 %
- `verzoegerung_ein`: 10 min, `verzoegerung_aus`: 30 min
- `nach_sonnenuntergang_nicht_oeffnen`: an

**Beschatten**, wenn alle Bedingungen erfüllt sind:

- θ < `max_einfallswinkel`
- Helligkeit seit `verzoegerung_ein` über `helligkeit_schwelle`
- Raumtemperatur über `temperatur_schwelle` (nur Freigabe)
- Rollladen steht weiter offen als `position_beschattung`
  (einen von Hand weiter geschlossenen Rollladen nie hochfahren)

**Zurückfahren**, wenn die Helligkeit seit `verzoegerung_aus` unter der Schwelle liegt oder
θ ≥ `max_einfallswinkel` ist – und nur, wenn der Rollladen noch auf `position_beschattung` steht
(kleine Toleranz). Hat jemand von Hand verstellt, bleibt der Rollladen, wo er ist.

Ziel: wenige Fahrten pro Tag (Solar-Akku).

**Prüfen, sobald der KIG 300 eingebunden ist:** Positionswerte und `cover.set_cover_position`
über HomeKit-Controller.

### 4.4 Automations-Blueprint „Dachfenster offen – Warnung“

Grundlage ist die bestehende Automation in Anhang A. Daraus einen Blueprint machen, beide Teile
(Warnen und Meldung entfernen) in einem.

**Eingaben**

- Fensterkontakt (`binary_sensor`, `on` = offen)
- Person(en): Auslöser, wenn eine das Zuhause verlässt (Variante „letzte Person geht“ über `zone.home` prüfen)
- Wetter-Entität mit stündlicher Vorhersage (Met.no); Vorhersagezeitraum 2 h, Regenschwelle 0,1 mm
- DWD-Warnstufe (optional). Achtung: reagiert auf jede Warnung, auch Frost und Hitze → optionaler Filter nach Warnart
- Uhrzeit Abendkontrolle (22:30), Prüfintervall Regen (15 min)
- Benachrichtigungsziel (Companion-App)

**Verhalten**

- Bedingung für jede Meldung: Kontakt offen
- Meldungen mit `tag`, Priorität hoch, iOS `time-sensitive`
- Kontakt geht auf `off` → `clear_notification` mit demselben `tag`

**Offene Entscheidung:** Bisher wiederholt sich nur die Regenprüfung alle 15 min; Weggehen, Abend und
DWD melden je einmal. Soll die Wiederholung für alle Auslöser gelten, solange das Fenster offen ist?

## 5. Repo-Aufbau

Analog zu wled-matrix-display, ergänzt um die Claude-Code-Dateien aus aiocontrome:

```
.claude/
  settings.json                  # Rechte für Claude Code (Abschnitt 7.2)
  agents/
    test-manager.md              # prüft, ob die Tests das Verhalten wirklich beweisen (7.4)
    ha-experte.md                # trennt Belegtes von Annahmen: HA-Verhalten und Physik (7.4)
  skills/
    sonnengeometrie/SKILL.md     # Fachreferenz: Formeln, Zählweisen, Testwerte, Grenzen
    neuer-blueprint/SKILL.md     # alle Stellen, die ein neuer Blueprint / eine neue Eingabe berührt
    ha-testen/SKILL.md           # Blueprints vor dem Commit im echten HA ausprobieren
    security-secrets/SKILL.md    # HA-Token, GitHub-App-Schlüssel, private Hausdaten
.github/
  ISSUE_TEMPLATE/fehler.yml      # HA-Version, Blueprint-Version, Trace
  workflows/validate.yml         # legt der Nutzer an (Abschnitt 6)
  workflows/release-please.yml   # legt der Nutzer an (Abschnitt 6)
blueprints/
  template/dachfenster/flaeche_sonneneinfall.yaml
  template/dachfenster/flaeche_helligkeit_pv.yaml
  automation/dachfenster/beschattung.yaml
  automation/dachfenster/dachfenster_offen_warnung.yaml
docs/
  ENTWURF.md                     # diese Datei, verbindlich
  anleitung.md                   # Checkliste in Teilen, use_blueprint-Beispiele, Gut zu wissen, Fehlersuche
  entwicklung.md                 # Physik, Testaufbau, „Taugen die Tests etwas?“, Workflows, Versionen
  LIVE_TESTS.md                  # optionale Live-Prüfung gegen das echte HA (7.5)
scripts/
  check_version.py               # Version im Kopf jedes Blueprints gegen den Tag prüfen
  ha_deploy.py                   # Blueprints aus dem Arbeitsverzeichnis ins echte HA spielen
  run-live-tests.ps1             # startet die Live-Prüfung auf dem Windows-PC (Token per Read-Host)
tests/
  conftest.py                    # HA-Template-Umgebung nachgebaut, Vorlagen direkt aus den Blueprints
  test_struktur.py               # Aufbau: Eingaben, Selektoren, Standardwerte, Versionen, Fixtures
  test_vorlagen.py               # Logik: Einfallswinkel, Helligkeit, Bedingungen
  test_deploy.py                 # scripts/ha_deploy.py
  live/                          # Marker „live“, läuft nur auf ausdrücklichen Wunsch (7.5)
  fixtures/configuration.yaml    # HA-Testkonfiguration für die CI, inkl. template: use_blueprint
  fixtures/automations.yaml      # je Automations-Blueprint eine Instanz minimal, eine vollständig
  fixtures/secrets.yaml          # Platzhalter
CLAUDE.md                        # Projektregeln für Claude Code (Abschnitt 7.1)
README.md                        # Funktionen, Installation, Voraussetzungen, Mitmachen, Lizenz
CONTRIBUTING.md                  # Ablauf, Commit-Präfixe, wie ein Release entsteht, GitHub-Einstellungen
CHANGELOG.md                     # pflegt release-please
LICENSE                          # MIT
.release-please-config.json
.release-please-manifest.json
.yamllint                        # aus wled übernehmen (ignoriert .github/, .venv/, venv/, ha/)
.gitattributes                   # * text=auto eol=lf (yamllint), *.ps1 text eol=crlf (PowerShell)
.gitignore                       # .venv/, ha/, .ha.env, Caches; uv.lock gehört ins Repo
.ha.env.example                  # Vorlage für scripts/ha_deploy.py
pyproject.toml
uv.lock
```

**`pyproject.toml`** wie bei wled: Das Projekt liefert kein Python-Paket aus, uv verwaltet nur die
Werkzeuge. `[tool.uv] package = false`, `version = "0"` (eingefroren, mit Kommentar warum),
`[dependency-groups] dev` mit pytest, PyYAML, Jinja2, yamllint; pytest mit `testpaths`/`pythonpath = tests`.

**Testaufbau** wie bei wled (`tests/conftest.py`):

- Die Tests rendern die Jinja-Vorlagen **direkt aus den Blueprint-Dateien**, nie aus Kopien.
- YAML-Loader, der `!input` als Platzhalter einliest; `FakeHass` als Zustandstabelle für `states`,
  `state_attr`, `is_state`; Filter wie in HA; `native()` wandelt das Ergebnis wie HA in Python-Typen.
- Für dieses Projekt zusätzlich nachbauen, was die Vorlagen nutzen: `sin`, `cos`, `acos`, `pi`,
  `float()` als Funktion, ggf. `has_value`.
- Standardwerte in Tests über `input_default()` aus dem Blueprint lesen, nicht abschreiben.
- Werte, die im Blueprint stehen, nur an **einer** Stelle im Test ausgeschrieben, wenn sie eine
  äußere Vorgabe dokumentieren (hier: die Testwerte aus Abschnitt 4).

## 6. Automatischer Workflow

Übernommen von wled-matrix-display. Die Workflow-Dateien legt der **Nutzer** an; Claude Code liefert
den Inhalt als Text (die GitHub App darf `.github/workflows/` nicht ändern).

### 6.1 `validate.yml` – bei Push auf `main`, jedem Pull Request und von Hand

`permissions: contents: read`. Die Job-Namen sind zugleich die erforderlichen Prüfungen im Ruleset:

| Job-Name | Inhalt |
|---|---|
| `YAML-Stil` | `uv run --locked yamllint --strict .` |
| `Tests (Python …)` | Matrix 3.13 und 3.14 (entschieden 23.11.2026), `uv sync --locked`, `uv run pytest -v` |
| `Home Assistant lädt die Blueprints` | HA-Konfiguration aus `tests/fixtures/` bauen, Automations-Blueprints nach `ha/blueprints/automation/dachfenster/`, Template-Blueprints nach `ha/blueprints/template/dachfenster/` kopieren, dann `frenck/action-home-assistant@v1` mit `version: stable` |

Der dritte Job lässt Home Assistant selbst die Konfiguration laden; was er erkennt, steht unter
„Grenze“. Die Fixtures enthalten je Blueprint eine minimale und eine vollständig belegte Instanz,
die Template-Blueprints über `template:` → `use_blueprint:` in `configuration.yaml`.
Grenze (geklärt in Etappe 2, Skill `sonnengeometrie` Abschnitt 5): Bei Template-Blueprints
liefert dieser Job **kein rotes Signal**. Schemafehler einer Instanz verwirft HA still,
Ladefehler (falscher `path`, fehlende Pflichteingabe) zählen nur als Warnung, und die Action
ruft `check_config` ohne `--fail-on-warnings` auf. Bei Automations-Blueprints ist es nach dem
Quelltext vermutlich ähnlich (Annahme, Gegenprobe in Etappe 6). Vorlagen wertet `check_config`
gar nicht aus. Die eigentliche Sicherung sind deshalb die Tests (`tests/test_struktur.py`,
`tests/test_vorlagen.py`); der Job fängt vor allem kaputtes YAML und fehlende `!include`-Dateien; unbekannte Integrationen
sind nur Warnungen.
Ob der Job mit `--fail-on-warnings` laufen soll, entscheidet der Nutzer (offen, Abschnitt 8).

### 6.2 `release-please.yml` – bei Push auf `main` und von Hand

`permissions: contents: write, pull-requests: write`. Zwei Jobs:

1. `googleapis/release-please-action@v5` mit `config-file` und `manifest-file`. Pflegt den
   Release-PR; wird er gemergt, entstehen Tag und GitHub-Release.
2. Nur wenn ein Release entstanden ist (`needs` + `if: release_created == 'true'`): auschecken,
   `scripts/check_version.py` gegen den Tag laufen lassen (Sicherheitsnetz), dann **alle
   Blueprint-Dateien unter `blueprints/`** per Muster (`shopt -s globstar nullglob`,
   `blueprints/**/*.yaml`) mit `gh release upload "$TAG" … --clobber` ans Release hängen. Keine
   feste Liste: Ein neuer Blueprint braucht keine Workflow-Änderung. Voraussetzung: Die
   Dateinamen sind eindeutig, weil Release-Anhänge keine Ordner haben (Test in 6.4). Findet das
   Muster nichts, bricht der Schritt ab.

Der zweite Job steht bewusst im selben Workflow: Was der Bot mit dem Standard-Token anlegt (Tag,
Release, PR), startet keine anderen Workflows. Ein eigener Workflow auf `release: published` liefe nie.

### 6.3 release-please-Konfiguration

- `.release-please-config.json`: `release-type: simple`, `package-name: roof-window-blueprints`,
  `changelog-path: CHANGELOG.md`, `include-component-in-tag: false`, `draft: false`,
  `prerelease: false`, `extra-files`: die Blueprint-Dateien. Startet leer (Etappe 2, noch keine
  Blueprints) und wächst mit jedem Blueprint; das ist die einzige Stelle der Release-Kette, die
  ein neuer Blueprint berührt (Skill `neuer-blueprint`).
- `changelog-sections` deutsch wie bei wled: `feat` → Hinzugefügt, `fix` → Behoben,
  `perf` → Geändert; `docs`, `test`, `ci`, `chore` versteckt (`hidden: true`).
- Jeder **sichtbare** Abschnitt löst einen Release-PR aus. Bei wled ist `refactor` sichtbar,
  CONTRIBUTING.md sagt aber „keine Version“. Hier einheitlich: `refactor` ebenfalls verstecken,
  und die Tabelle in CONTRIBUTING.md muss zur Konfiguration passen.
- `.release-please-manifest.json` startet mit `{".": "0.0.0"}`; das erste `feat:` ergibt 0.1.0.
- `bump-minor-pre-major: true` (entschieden 23.11.2026): In der 0.x-Phase hebt ein `feat!:` die
  zweite Stelle an statt sofort 1.0.0 (wled nutzt `false`, startete aber bei 1.0.0).

### 6.4 Versionsnummer

Steht nur im Kopf jeder Blueprint-Datei, weil das Blueprint-Schema kein Versionsfeld kennt:

```yaml
# Version: 0.0.0 # x-release-please-version
#
# Die Zeile darüber pflegt release-please automatisch. Die Markierung
# "x-release-please-version" nicht entfernen; scripts/check_version.py
# prüft beim Release, dass sie zum Tag passt.
```

Tests halten fest: Markierung in jedem Blueprint vorhanden und gleich der Version im Manifest;
`pyproject.toml` bleibt bei `"0"` und steht nicht in `extra-files`; `uv.lock` führt die
Projektversion `"0"` (Datei lesen wie bei wled; ob sie sonst aktuell ist, prüft die CI mit
`--locked`); `extra-files` nennt genau die Dateien unter `blueprints/`; die Dateinamen unter
`blueprints/` sind eindeutig; der Release-Workflow hängt per Muster an statt per Liste (Test
läuft, sobald die Datei im Repo liegt).

### 6.5 Festgenagelte Versionen (jeweils mit Begründung als Kommentar)

- Runner `ubuntu-26.04` statt `ubuntu-latest`: ein Wechsel der Ubuntu-Version kommt als eigener
  Commit mit eigener CI, nicht unbemerkt zwischen zwei Läufen.
- `actions/checkout@v7`, `astral-sh/setup-uv@v7`, `googleapis/release-please-action@v5`,
  `frenck/action-home-assistant@v1`.
- `setup-uv` mit fester `version:` gleich der lokalen uv (wled: 0.12.18, aiocontrome: 0.13.8 – die
  im Container nehmen). Ohne Angabe installiert die Action eine ältere uv, die das Format der
  `uv.lock` nicht kennt, und `--locked` scheitert, obwohl lokal alles stimmt.
- Überall `--locked`: fällt auf, wenn `uv.lock` und `pyproject.toml` auseinanderlaufen.

### 6.6 Wie ein Release entsteht (gehört in CONTRIBUTING.md)

1. PR nach `main` mergen.
2. Der Bot legt den PR `chore(main): release X.Y.Z` an oder aktualisiert ihn: CHANGELOG und
   Version in den Blueprints.
3. Weitere Merges sammeln sich im selben Release-PR.
4. Zum Veröffentlichen den Release-PR mergen → Tag, GitHub-Release, Blueprint-Dateien angehängt.

Keine Version von Hand, kein Tag, `CHANGELOG.md` nicht anfassen. Zurücknehmen:
`gh release delete vX.Y.Z --yes`, Tag löschen, Version in `.release-please-manifest.json`
zurücksetzen.

### 6.7 GitHub-Einstellungen (einmalig, Nutzer)

- Ruleset für `main`: Löschen und Force-Push sperren, PR erforderlich, Approvals 0 (allein
  gearbeitet), erforderliche Prüfungen = die drei Job-Namen aus 6.1. Die Namen erscheinen in der
  Auswahl erst nach dem ersten Lauf.
- Settings → Actions → General: „Allow GitHub Actions to create and approve pull requests“ an,
  sonst darf der Bot den Release-PR nicht anlegen.
- Secret Scanning und Push Protection an (wie bei den Controme-Repos).
- Beschreibung: „Home-Assistant-Blueprints fürs Dachfenster (roof window, skylight): Sonneneinfall,
  Helligkeit aus der PV, Beschattung, Warnung bei offenem Fenster“. Topics: `home-assistant`,
  `home-assistant-blueprint`, `roof-window`, `skylight`, `sun-position`, `shading`. „skylight“
  steht dort, damit das Repo auch unter dem gängigeren Wort gefunden wird.
- Das Ruleset `release-tags` der Controme-Repos **nicht unverändert** übernehmen: Dort setzt der
  Nutzer Tags selbst, hier legt release-please den Tag an. Verbietet das Ruleset das Anlegen von
  `v*`-Tags, scheitert das Release.
- **Entschieden (23.11.2026):** Ein Release-PR, den release-please mit dem Standard-Token öffnet,
  startet keine Workflows; mit Pflichtprüfungen bliebe er blockiert. Der Nutzer schließt den
  Release-PR vor dem Merge einmal und öffnet ihn wieder, dann laufen die Prüfungen (Schritt in
  CONTRIBUTING.md). Verworfen: eigenes App-Token für release-please, Ausnahme der
  Release-Branches von den Pflichtprüfungen.

## 7. Claude Code im Repo

### 7.1 `CLAUDE.md`

Zusammengesetzt aus den CLAUDE.md von wled-matrix-display, aiocontrome und ha-controme-insights:

- **Projekt** in drei Zeilen; „Die verbindliche Spezifikation ist `docs/ENTWURF.md`.“
- **Sprache:** mit dem Nutzer Deutsch; Doku, Blueprint-Texte, Commits und PRs Deutsch.
  Befehle für den Nutzer einzeln und mit erwarteter Ausgabe.
- **Vor jeder Änderung lesen:** `README.md`, `CONTRIBUTING.md`, `docs/entwicklung.md` und die
  Kommentare in den Blueprints. Was dort begründet ist, nicht „aufräumen“.
- **Sicherheitsregeln (nicht verhandelbar)**
  1. Keine Geräte im Heimnetz ansprechen; der Container hat absichtlich keinen Weg dorthin.
     Live-Tests macht der Nutzer (Skill `ha-testen`, `docs/LIVE_TESTS.md`).
  2. Keine Zugangsdaten anlegen, erfragen, speichern oder ausgeben (Skill `security-secrets`).
  3. Keine echten Daten aus dem Haus des Nutzers ins Repo: keine Koordinaten, Adressen,
     Entitäts-IDs oder Anlagenwerte, nur Beispielwerte.
  4. GitHub: nur Feature-Branches (`feat/…`, `fix/…`, `docs/…`, `chore/…`, `ci/…`), Pushes nur
     nach Rückfrage, PRs mit `ghb pr create`. Nie direkt nach `main`, nie Force-Push, nie Tags,
     nie Releases.
  5. `.github/workflows/` nicht ändern; Vorschläge als Text an den Nutzer.
  6. Neue Abhängigkeiten nur nach Rückfrage.
  7. Nichts aus dem Code von SFML übernehmen.
- **Releases:** release-please erzeugt Version, CHANGELOG und Release-PR. Keine Version von Hand,
  keinen Tag, `CHANGELOG.md` nicht anfassen. Commits nach Conventional Commits, so formuliert, dass
  sie im CHANGELOG verständlich sind. Bricht eine Änderung bestehende Einrichtungen (Eingabe
  umbenannt oder entfernt): `feat!:` plus `BREAKING CHANGE:` im Rumpf.
- **Tests:** Vorlagen direkt aus den Blueprints lesen, keine Kopien. Neue Logik: erst der Test,
  dann prüfen, dass er ohne die Funktion fehlschlägt (Blueprint absichtlich kaputt machen);
  erkannte Fehler in die Tabelle „Taugen die Tests etwas?“ in `docs/entwicklung.md`.
- **Prüf-Agenten:** vor jedem Push den Subagent `test-manager` aufrufen, bei Änderungen an
  Vorlagen, Physik, Selektoren oder HA-Verhalten zusätzlich `ha-experte`. Befunde unter
  BLOCKIERT beheben, die Berichte im PR-Text kurz zusammenfassen. Gegenproben (läuft der Test
  ohne die Änderung rot?) mit `git stash` oder `git worktree`, nie mit `git checkout --` oder
  `git restore`.
- **Arbeitsweise:** vor größeren Schritten einen kurzen Plan zeigen und auf Freigabe warten.
  Spezifikation nur nach Rückfrage ändern, Abweichungen in `docs/ENTWURF.md` nachziehen.
  Unklarheiten: erst Doku und Skill prüfen, dann fragen, nicht raten. Verhalten von Home Assistant
  in der aktuellen Doku prüfen, HA kündigt regelmäßig Muster ab.
- **Befehle:** `uv sync --locked`, `uv run pytest`, `uv run yamllint --strict .`

### 7.2 `.claude/settings.json`

Wie bei aiocontrome:

- erlaubt: `uv run pytest`, `uv run yamllint`, `git status`, `git diff`, `git log`, `git branch`,
  `git show`, `git stash list` (braucht der `test-manager`, 7.4)
- verboten: `curl`, `wget`, `nc`, `ssh`, `scp`, `git push --force`, `git push -f`,
  `git push origin main`, `git tag`, Lesen von `.env`, `.env.*` und `.ha.env`
- zusätzlich verboten (neu gegenüber aiocontrome): Push-Varianten auf `main`
  (`git push origin HEAD:main`, `git push origin main:main`, `git push origin +main` u. Ä.)
  und das Lesen von `.ha.env` per Bash (`cat`, `head`, `tail`, `less`, `grep`).
- zusätzlich erlaubt (neu gegenüber aiocontrome): `WebFetch` nur für `www.home-assistant.io`,
  `developers.home-assistant.io` und `github.com` – Home Assistant dokumentiert sein Verhalten
  online, Controme nicht.

Die Verbote in `settings.json` sind nur eine **zusätzliche Hürde**: Muster auf Befehlszeilen
lassen sich umgehen (andere Schreibweise, anderes Programm). Die eigentliche Sicherung ist
das Ruleset auf GitHub (kein direkter Push nach `main`, kein Bypass, 6.7), und `.ha.env` liegt
nur auf dem PC des Nutzers, nie im Container.

### 7.3 Skills

| Skill | Vorbild | Inhalt |
|---|---|---|
| `sonnengeometrie` | `controme-api` (aiocontrome) | Fachreferenz: Formeln, Zählweise von Azimut und Neigung, Quelle des Sonnenstands in HA, Umrechnung PV → W/m² → lx mit Annahmen, Testwerte, Grenzen. Jede dort genannte Eigenheit braucht einen Test. |
| `neuer-blueprint` | `neue-app` (wled) | Checkliste aller Stellen bei einem neuen Blueprint oder einer neuen Eingabe: Versionskopf, `extra-files`, `check_version.py`, Upload-Liste im Release-Workflow (als Text an den Nutzer), Tests, CI-Fixtures (minimal und vollständig), README, `anleitung.md`. Am Ende die Gegenprobe. |
| `ha-testen` | `ha-testen` (wled) | Ablauf auf dem PC des Nutzers: Tests, `ha_deploy.py --trocken`, kopieren, Konfiguration prüfen, Automationen und Template-Entitäten neu laden; was der Nutzer prüft (Entwicklerwerkzeuge → Zustände, Traces). Der Container erreicht HA nicht: Der Nutzer checkt den Feature-Branch auf seinem PC aus, führt die Befehle aus, die Claude Code nennt, und merged den PR erst nach dem Test. |
| `security-secrets` | `security-secrets` (aiocontrome) | gekürzt: HA-Token nur in `.ha.env` auf dem PC des Nutzers (in `.gitignore`, nie ausgeben), GitHub-App-Schlüssel, keine privaten Hausdaten, Prüfliste vor jedem Commit (`git diff --cached`). |

Ein Skill `release` wie bei aiocontrome entfällt, das übernimmt release-please.

`scripts/ha_deploy.py` aus wled erweitern: beide Blueprint-Arten kopieren
(`blueprints/automation/dachfenster/`, `blueprints/template/dachfenster/`), Konfiguration prüfen,
Automationen **und** Template-Entitäten neu laden. Einstellungen in `.ha.env` (Vorlage
`.ha.env.example`, Ziel per Samba-Freigabe oder `scp`).

### 7.4 Prüf-Agenten (`.claude/agents/`)

Nach dem Vorbild von `test-manager` und `api-expert` in aiocontrome und ha-controme-insights.
Beide sind **schreibgeschützt** (Werkzeuge `Read, Grep, Glob, Bash`, beim `ha-experte` zusätzlich
`WebFetch` für die HA-Doku; nichts bearbeiten, nicht committen, nicht pushen), antworten auf Deutsch, erfinden keine Befunde und schließen mit
„merge-fähig“ oder „nicht merge-fähig“. Die Dateien sind projekteigen; der Satz „Keep this file
identical in both repositories“ aus den Vorbildern entfällt.

**`test-manager`** – skeptischer Testprüfer, schreibt keinen Produktivcode.

- Erlaubt: `uv run pytest …`, `uv run yamllint …`, `git status`, `git diff …`, `git log …`,
  `git show …`, `git stash list`. Kein Netz, kein `git checkout`, kein `git restore`.
- Liest zuerst `CLAUDE.md`, die Skills `sonnengeometrie` und `security-secrets`,
  `docs/ENTWURF.md`, dann `git diff origin/main...HEAD` und die zugehörigen Tests.
- Prüft:
  1. Jede Eigenheit aus `sonnengeometrie` und jeder Testwert aus Abschnitt 4 ist durch einen
     Test belegt.
  2. Randfälle: Sonne unter dem Horizont, θ genau 90°, cos θ durch Rundung außerhalb [−1, 1],
     Neigung 0 und 90, Azimut 0 und 360, negative PV-Leistung, W und kW, `unavailable` und
     `unknown`, fehlende Attribute beim Sonnenstand.
  3. Asserts, die beißen: exakte Werte mit Toleranz statt „ist eine Zahl“.
  4. Gegenprobe: Würde der Test ohne die Änderung rot? Wenn unklar, sagen, wie man es prüft
     (`git stash` oder `git worktree`), nicht selbst ausführen.
  5. Vorlagen kommen aus den Blueprint-Dateien, keine Kopien; Standardwerte über `input_default()`.
  6. CI-Fixtures: nur echte Eingaben, jede Eingabe in der vollständigen Instanz belegt, ein
     Minimalfall vorhanden.
  7. Release-Kette stimmig: Versionsmarkierung in jedem Blueprint, `extra-files`, Upload-Liste im
     Release-Workflow, `check_version.py`.
  8. Keine privaten Daten in Tests und Fixtures.
  9. `yamllint --strict` sauber, alle Tests grün.
- Bericht: `Testlauf` · `BLOCKIERT` · `SOLLTE` · `HINWEIS` · `Fazit`

**`ha-experte`** – skeptischer Experte für Blueprints, Vorlagen und Sonnengeometrie
(Gegenstück zu `api-expert`).

- Vertraut in dieser Reihenfolge: Tests und CI-Lauf (Home Assistant prüft die Blueprints), Skill
  `sonnengeometrie`, aktuelle HA-Doku. Alles andere ist eine Annahme und wird so benannt.
- Erlaubt: `git status`, `git diff …`, `git log …`, `git show …`, lesendes `grep`/`head`. Keine
  Tests ausführen, das ist Aufgabe des `test-manager`. Anders als `api-expert` darf er die HA-Doku
  lesen (`WebFetch` nur für die Domains aus 7.2), weil HA sein Verhalten dort dokumentiert. Nie
  etwas im Heimnetz.
- Prüft:
  1. Beleg für jedes HA-Verhalten, auf das sich die Änderung stützt: Selektor, Template-Funktion,
     Blueprint-Funktion, `device_class` und Einheit, Dienstaufruf. Ohne Beleg: im Code als Annahme
     kennzeichnen, Test- oder Live-Test-Plan.
  2. Mindestversion: alles Genutzte gibt es ab `min_version`, nichts davon ist abgekündigt.
  3. Physik: Formeln, Zählweisen (Kompass-Azimut, Neigung 0–90), Umrechnung Grad/Bogenmaß und
     Begrenzung vor `acos` wie im Skill.
  4. Grenzen dokumentiert, z. B. bei der PV-Umrechnung: DC-Seite, gleiche Ebene, Nulleinspeisung,
     Schnee.
  5. Robustheit: nicht verfügbare Eingaben, fehlender Sonnenstand, Verhalten nach einem
     HA-Neustart, kein Flattern (Verzögerungen).
  6. Bestehende Einrichtungen: umbenannte oder entfernte Eingaben sind ein Bruch → `feat!:` und
     `BREAKING CHANGE:`.
  7. Rollladen: nie einen von Hand weiter geschlossenen Rollladen hochfahren; wenige Fahrten pro Tag.
- Live-Test-Plan für den Windows-PC des Nutzers: ein Befehl je Schritt mit erwarteter Ausgabe,
  HA-Token nur per `Read-Host`, nur lesend, sofern nichts anderes abgesprochen ist.
- Bericht: `BELEGT` · `UNBELEGT (Annahme)` · `VERSTÖSSE` · `LIVE-TEST-PLAN` · `Fazit`

### 7.5 Live-Prüfung (optional, nur vom PC des Nutzers)

Nach dem Muster der Live-Tests von aiocontrome (`docs/LIVE_TESTS.md`, `tests/live/`,
`scripts/run-live-tests.ps1`):

- Marker `live` in `pyproject.toml`; der normale Lauf schließt ihn aus (`addopts = '-m "not live"'`),
  ohne Konfiguration werden die Tests übersprungen. Nie in CI, nie im Container.
- Start über `scripts/run-live-tests.ps1`: HA-Adresse und Token per `Read-Host` (Token mit
  `-AsSecureString`), also nie auf der Kommandozeile oder in der PowerShell-Historie. Token eines
  eigenen HA-Benutzers ohne Adminrechte.
- Nur lesend über die REST-API von HA (Zustände abfragen).
- Prüft mit Toleranz: Der Sonneneinfall-Sensor stimmt mit einer unabhängigen Python-Rechnung aus
  dem aktuellen Sonnenstand und seinen Attributen `azimut`/`neigung` überein; der
  Helligkeits-Sensor passt zu seinen Attributen nach der Formel aus 4.2; der Sonnenstand liefert,
  was die Vorlagen erwarten.
- Gibt nur Zahlen, Zustände und Schlüsselnamen aus, nie Adresse, Token oder Koordinaten. Ein Test
  belegt, dass der Bericht Adresse und Token nicht enthält.

## 8. Vor dem Bauen prüfen (nicht annehmen)

- Template-Blueprints: eine Entität je Blueprint, Anlegen nur per YAML (Stand 2026); welche Optionen
  gehen (Attribute, `availability`, Einheit, `device_class`, `delay_on`/`delay_off`); ab welcher
  HA-Version. Der Nutzer betreibt HA 2026.11.x; `min_version` nach den genutzten Funktionen setzen.
- Sonnenstand: Attribute von `sun.sun` oder Sensoren der Sun-Integration (Sonnenhöhe,
  Sonnenazimut); wie oft aktualisiert wird und ob etwas abgekündigt ist
- Jinja in HA: `sin`, `cos`, `acos`, `pi`
- ~~Pfad nach dem Import~~ geklärt: `use_blueprint: path:` relativ zu `blueprints/template/`
  (Skill `sonnengeometrie` Abschnitt 5)
- Benachrichtigungsziel für die Companion-App im Blueprint: gängiges Muster
- `device_class` und Einheiten: `illuminance` (lx), `irradiance` (W/m²)
- ~~Prüft `frenck/action-home-assistant` auch Template-Blueprints mit?~~ geklärt: Sie lädt sie,
  macht aber nie rot – Schemafehler werden still verworfen, Ladefehler sind nur Warnungen (6.1,
  Skill `sonnengeometrie` Abschnitt 5). Gegenprobe in der CI mit dem ersten Template-Blueprint.
- **Offen (Nutzer):** HA-Job mit `--fail-on-warnings` (direkter `docker run` statt der Action,
  die den Schalter nicht durchreicht)? Dann würden Ladefehler rot, Schemafehler weiterhin nicht.
- ~~Lädt `template.reload` geänderte Template-Blueprints neu?~~ geklärt: ja, der Dienst leert
  vorher den Blueprint-Zwischenspeicher (Quelltext); Live-Bestätigung beim ersten Deploy.
- ~~Erforderliche Prüfungen auf dem Release-PR~~ entschieden: schließen und wieder öffnen (6.7)
- ~~`bump-minor-pre-major`~~ entschieden: `true` (6.3)

## 9. Etappen

0. **Nutzer, einmalig:** Repo `roof-window-blueprints` mit MIT-Lizenz anlegen, GitHub App freigeben, Einstellungen aus 6.7
   (die Pflichtprüfungen erst nach dem ersten CI-Lauf eintragen).
1. **Regeln zuerst (Claude Code, eigener PR):** `docs/ENTWURF.md`, `CLAUDE.md`,
   `.claude/settings.json`, die zwei Agenten, die vier Skills. Danach Claude Code neu starten,
   damit Regeln, Rechte und Agenten greifen.
2. **Grundgerüst:** `pyproject.toml` + `uv.lock`, `.yamllint`, `.gitattributes`, `.gitignore`,
   `.ha.env.example`, release-please-Konfiguration und Manifest, `scripts/check_version.py` und
   `scripts/ha_deploy.py`, `tests/conftest.py` mit den Grundprüfungen in `test_struktur.py`,
   Gerüste für README und CONTRIBUTING, Issue-Vorlage. Workflow-Inhalte als Text an den Nutzer,
   der sie anlegt.
3. Template-Blueprint 4.1 mit Tests
4. Template-Blueprint 4.2 mit Tests
5. Live-Prüfung (optional, 7.5)
6. Automations-Blueprint 4.4 (Warnung)
7. Automations-Blueprint 4.3 (Beschattung)
8. `docs/anleitung.md` und `docs/entwicklung.md`
9. Release 0.1.0: Release-PR mergen

Parallel beim Nutzer: Sensoren aus 4.1 und 4.2 über den Winter mit echten Werten laufen lassen und
prüfen – Uhrzeit, ab der die Sonne ins Fenster scheint; Abgleich der Umrechnung an einem klaren Tag.

## Anhang A: Bestehende Warn-Automation

Platzhalter: `binary_sensor.dachfenster_kontakt`, `person.DEIN_NAME`, `notify.mobile_app_DEIN_HANDY`,
`sensor.DEINE_REGION_current_warning_level`, `weather.forecast_home`

```yaml
alias: Dachfenster offen – Warnung
mode: single
max_exceeded: silent
triggers:
  - trigger: state
    entity_id: person.DEIN_NAME
    from: home
    id: weg
  - trigger: time
    at: "22:30:00"
    id: abend
  - trigger: numeric_state
    entity_id: sensor.DEINE_REGION_current_warning_level
    above: 0
    id: dwd
  - trigger: time_pattern
    minutes: /15
    id: regencheck
conditions:
  - condition: state
    entity_id: binary_sensor.dachfenster_kontakt
    state: "on"
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: regencheck
        sequence:
          - action: weather.get_forecasts
            target:
              entity_id: weather.forecast_home
            data:
              type: hourly
            response_variable: vorhersage
          - variables:
              naechste: "{{ vorhersage['weather.forecast_home'].forecast[:2] }}"
              regen_kommt: >-
                {% set mm = (naechste | map(attribute='precipitation', default=0)
                             | map('float', 0) | list) + [0] %}
                {% set nass = naechste | map(attribute='condition')
                             | select('in', ['rainy', 'pouring', 'lightning-rainy',
                                             'hail', 'snowy-rainy'])
                             | list | count %}
                {{ (mm | max) > 0.1 or nass > 0 }}
          - condition: template
            value_template: "{{ regen_kommt }}"
          - action: notify.mobile_app_DEIN_HANDY
            data:
              title: "☔ Dachfenster ist offen"
              message: "In den nächsten zwei Stunden ist Regen angesagt."
              data:
                tag: dachfenster
                priority: high
                ttl: 0
                push:
                  interruption-level: time-sensitive
    default:
      - action: notify.mobile_app_DEIN_HANDY
        data:
          title: "🪟 Dachfenster ist offen"
          message: >-
            {% if trigger.id == 'weg' %}
              Du bist losgegangen, das Dachfenster steht noch offen.
            {% elif trigger.id == 'dwd' %}
              DWD: {{ state_attr(trigger.entity_id, 'warning_1_name') or 'Wetterwarnung' }}
              – und das Dachfenster ist offen.
            {% else %}
              Es ist spät und das Dachfenster ist noch offen.
            {% endif %}
          data:
            tag: dachfenster
            priority: high
            ttl: 0
            push:
              interruption-level: time-sensitive
```

```yaml
alias: Dachfenster zu – Meldung entfernen
mode: single
triggers:
  - trigger: state
    entity_id: binary_sensor.dachfenster_kontakt
    to: "off"
actions:
  - action: notify.mobile_app_DEIN_HANDY
    data:
      message: clear_notification
      data:
        tag: dachfenster
```
