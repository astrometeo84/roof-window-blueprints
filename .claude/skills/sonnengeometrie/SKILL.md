---
name: sonnengeometrie
description: Fachreferenz für roof-window-blueprints – Einfallswinkel der Sonne auf eine geneigte Fläche, Zählweise von Azimut und Neigung, Sonnenstand in Home Assistant, Umrechnung PV-Leistung → W/m² → lx mit Annahmen, Testwerte und Grenzen. Immer verwenden, wenn Vorlagen, Tests oder Doku zu Sonneneinfall, Helligkeit oder Beschattung geschrieben oder geprüft werden.
---

# Sonnengeometrie und Helligkeit aus der PV – Referenz

Verbindlich ist `docs/ENTWURF.md` (Abschnitt 3 und 4). Dieser Skill fasst die Fachgrundlagen
zusammen. **Jede hier genannte Eigenheit braucht einen Test** (`tests/test_vorlagen.py`).
Die Physik ist Lehrbuchwissen; **nichts aus dem Code von Solar Forecast ML (SFML) übernehmen**.

Kennzeichnung: **belegt** = in der HA-Doku nachgelesen (Stand 23.11.2026, URL dabei);
**offen** = noch zu prüfen (`docs/ENTWURF.md` Abschnitt 8), vor dem Bauen klären und hier
nachtragen.

## 1. Zählweisen

| Größe | Zählweise | Bemerkung |
|---|---|---|
| Azimut (Sonne und Fläche) | Kompass, im Uhrzeigersinn: 0 = N, 90 = O, 180 = S, 270 = W | wie HA und SFML; 0 und 360 sind dieselbe Richtung |
| Azimut der Fläche A_f | Richtung, in die die Fläche **schaut** (Normale, waagerecht projiziert) | Dachfenster nach Süden → 180 |
| Sonnenhöhe h | Winkel über dem Horizont in Grad, negativ = unter dem Horizont | |
| Neigung β | 0–90°: 0 = waagerecht, 90 = senkrecht | Dachneigung = Neigung des Fensters |
| Einfallswinkel θ | Winkel zwischen Sonnenstrahl und Flächennormale | 0 = senkrecht auf die Fläche, 90 = streifend, > 90 = Sonne hinter der Fläche |

## 2. Einfallswinkel (Baustein 4.1)

```
cos θ = sin(h) · cos(β) + cos(h) · sin(β) · cos(A_s − A_f)
θ     = acos(cos θ)
```

- h = Sonnenhöhe, A_s = Sonnenazimut, β = Neigung, A_f = Azimut der Fläche.
- **Grad → Bogenmaß:** `x * pi / 180`, zurück mit `* 180 / pi`. HA-Vorlagen kennen
  **kein** `radians`/`degrees` (belegt: Liste der Math-Funktionen unter
  https://www.home-assistant.io/template-functions/ enthält `sin`, `cos`, `acos`, `pi`, `clamp`,
  aber kein `radians`/`degrees`). `sin`/`cos` erwarten Bogenmaß, `acos` liefert Bogenmaß
  (belegt, ebenda).
- **cos θ vor `acos` auf [−1, 1] begrenzen.** Rundungsfehler können z. B. 1.0000000002 ergeben;
  `acos` wirft dann einen Fehler. Begrenzt wird mit `clamp(c, -1, 1)` (entschieden in Etappe 3;
  der Test prüft beide Grenzen mit echten Ausreißern, siehe Testwerte). `clamp` gibt es
  erst **seit HA 2025.4** (https://www.home-assistant.io/template-functions/clamp/) → mit
  `clamp` mindestens `min_version: 2025.4.0`.
- **`acos` nie mit Standardwert** (`acos(x, 0)`): HA liefert dann außerhalb [−1, 1] still den
  Standardwert, also θ = 0° = volle Sonne, und verdeckt eine fehlende Begrenzung. Der Nachbau in
  `tests/conftest.py` kennt deshalb absichtlich keinen Standardwert bei `sin`/`cos`/`acos`.
- **Azimut 0/360:** Die Differenz A_s − A_f geht nur über `cos` ein, daher ist keine
  Normalisierung nötig. Test: A_f = 0 und A_f = 360 liefern dasselbe θ.
- **Neigung 0:** cos θ = sin(h), θ = 90° − h, unabhängig von beiden Azimuten.
- **Neigung 90:** cos θ = cos(h) · cos(A_s − A_f) (senkrechte Fassade).
- **`sonne_trifft_flaeche`:** wahr genau dann, wenn h > 0 **und** cos θ > 0. Bei θ = 90° genau
  (cos θ = 0) ist es falsch. Nachts kann cos θ > 0 sein (Sonne unter dem Horizont, aber „vor“ der
  Fläche), deshalb gehört die Prüfung h > 0 dazu. Bei h = 0 genau ist es falsch.
- **Rundungsrauschen bei 90°:** cos 90° ergibt in Gleitkomma etwa 6e-17, nicht 0 (z. B.
  senkrechte Südfassade, Sonne genau im Osten). Deshalb vergleicht `sonne_trifft_flaeche`
  cos θ **auf vier Stellen gerundet** mit 0 – wie das Attribut `cos_einfall` es zeigt. Folge:
  Streifendes Licht mit θ über etwa 89,997° zählt nicht als „trifft“.
- Ausgabe: θ in ° mit **einer** Nachkommastelle; Attribute `cos_einfall` (vier
  Nachkommastellen), `sonne_trifft_flaeche`, `azimut`, `neigung`.
- **Die Formel steht dreimal** im Blueprint (Zustand, `cos_einfall`, `sonne_trifft_flaeche`):
  Eine Vorlage kann das Ergebnis einer anderen nicht lesen, und Blueprint-`variables` werden bei
  zustandsbasierten Template-Entitäten nur beim Laden ausgewertet (HA-Doku, Template-Integration:
  „only resolved when the configuration is loaded or reloaded“). Ein Test prüft über viele
  Sonnenstände, dass alle drei gleich rechnen.

### Testwerte 4.1 (äußere Vorgabe, einmal im Test ausgeschrieben)

| Fläche A_f / β | Sonne A_s / h | θ | Kontrolle |
|---|---|---|---|
| 180 / 40 | 180 / 60 | 10,0° | cos θ = sin(60° + 40°) = sin 100° |
| 180 / 40 | 0 / 10 | 120,0° | cos θ = sin(10° − 40°) = −0,5 → Sonne hinter der Fläche |
| beliebig / 0 | beliebig / 30 | 60,0° | cos θ = sin 30° = 0,5 |
| 90 / 90 | 90 / 10 | 10,0° | cos θ = cos 10° |

Zusätzliche Randfälle für Tests: h ≤ 0, θ genau 90°, cos θ minimal über 1 bzw. unter −1,
Neigung 0 und 90, Azimut 0 und 360, fehlende Attribute beim Sonnenstand.

Werte, die in Gleitkomma-Rechnung (Reihenfolge wie in der Vorlage) cos θ außerhalb [−1, 1]
ergeben: A_f 180 / β 8 / A_s 180 / h 82 → 1.0000000000000002; A_f 180 / β 8 / A_s 0 / h −82 →
−1.0000000000000002. Damit prüft der Test die Begrenzung wirklich.

## 3. Sonnenstand in Home Assistant

„Quelltext“ = HA-Core, Branch `dev`, gelesen am 23.11.2026 (`components/sun/const.py`,
`entity.py`, `sensor.py`).

- **Entschieden (23.11.2026): Die Vorlagen lesen die Attribute `elevation` und `azimuth` von
  `sun.sun`**, nicht die Sensoren. Begründung: Die Attribute sind immer da, die Sensoren muss der
  Nutzer erst aktivieren (siehe unten).
- **Attribute – belegt im Quelltext.** `sun.sun` hat die Attribute `elevation` und `azimuth`
  (`const.py`: `ELEVATION = "elevation"`, `AZIMUTH = "azimuth"`), Gleitkommazahlen, auf **zwei
  Nachkommastellen** gerundet (`entity.py`: `round(…, 2)`). `extra_state_attributes` liefert sie
  immer, nicht bedingt. Weitere Attribute: `rising`, `next_dawn`, `next_dusk`, `next_midnight`,
  `next_noon`, `next_rising`, `next_setting`. Die Attribute stehen in `_unrecorded_attributes`
  (nicht in der Historie).
- **Zustand** von `sun.sun`: `above_horizon` / `below_horizon`; Grenze im Quelltext
  `ELEVATION_HORIZON = -0.833` (Refraktion und Sonnenradius). Unsere Prüfung `h > 0` ist
  absichtlich strenger und unabhängig davon.
- **Sensoren – belegt im Quelltext.** `sensor.sun_solar_elevation` und `sensor.sun_solar_azimuth`
  (`ENTITY_ID_SENSOR_FORMAT = "sensor.sun_{}"`), Einheit Grad, `state_class: measurement`,
  Kategorie Diagnose, **standardmäßig deaktiviert** (`entity_registry_enabled_default=False`).
- **Doku – belegt** (https://www.home-assistant.io/integrations/sun/): Elevation „Negative values
  mean the sun is below the horizon.“, Azimuth „The angle is shown clockwise from north.“ (also
  Kompass wie bei uns). „The sensors are also available as attributes on the `sun.sun` entity
  for backward compatibility.“ **Kein Abkündigungshinweis** in Doku und Quelltext. Restrisiko:
  „backward compatibility“ klingt nach einem Weg, den HA irgendwann entfernen könnte – bei einem
  Hinweis in den Release-Notes auf die Sensoren umstellen.
- **Aktualisierung – belegt im Quelltext** (`entity.py`, `_PHASE_UPDATES`): Höhe und Azimut
  werden je nach Phase neu berechnet – Tag (h > 10°) alle 4 min, „small day“ (0–10°) und
  bürgerliche Dämmerung alle 2 min, nautische Dämmerung 4 min, astronomische 8 min, Nacht 20 min
  (Kommentar dort: „4 mins is one degree of arc change of the sun“). Liegt der nächste Termin zu
  nah an einem Phasenwechsel, entfällt er.
- **Neu rechnen der Vorlage bei reiner Attributänderung – belegt im Quelltext** (Befund
  `ha-experte`): `core.py` (`StateMachine`) feuert `EVENT_STATE_REPORTED` nur, wenn Zustand
  **und** Attribute gleich bleiben, sonst `EVENT_STATE_CHANGED`; darauf hört die Verfolgung der
  Vorlagen (`helpers/event.py`, `async_track_state_change_event`). Doku: „Template entities by
  default update as soon as any of the referenced data in the template updates.“
  Live-Bestätigung: Der Sensor ändert sich am Tag alle paar Minuten (Skill `ha-testen`). Eine Begrenzung auf einmal pro Minute gilt nur für Vorlagen, die über
  **alle** Zustände iterieren (`states` ohne Entität), nicht für uns.
- Die Doku nennt keine Einheit für h; „Grad“ ergibt sich aus dem Beispiel „0 degrees and -6
  degrees“ (Dämmerung) und der Einheit der Sensoren.
- **Fehlt der Sonnenstand** (`sun.sun` fehlt, `unavailable`/`unknown` ohne Attribute, Attribut
  fehlt oder ist keine Zahl), liefert die Vorlage keinen Fantasiewert und keinen
  Vorlagenfehler: `availability` ist falsch, Zustand und `cos_einfall` sind `none`,
  `sonne_trifft_flaeche` ist falsch. Geprüft wird mit `is number`: dem eingebauten Jinja-Test
  (`isinstance(value, Number)`), **nicht** HAs `is_number`, das auch Zahlen-Texte wie „21.5“
  durchlässt (https://www.home-assistant.io/template-functions/is_number/). Dass HAs
  Vorlagen-Umgebung den Jinja-Test behält, ist gestützt (sie erbt von
  `ImmutableSandboxedEnvironment`), aber erst mit dem Live-Test bestätigt.
- **`availability` falsch → HA rendert Zustand und Attribute gar nicht** (belegt im Quelltext,
  Befund `ha-experte`: `template_entity.py` setzt `availability` als „super template“ an den
  Anfang; `helpers/event.py`: „If the super template did not render to True, don't update other
  templates“). Die `is number`-Abfragen in Zustand und Attributen sind damit zusätzlicher Schutz
  und halten die Einzeltests aussagekräftig.
- **Achtung: Wirft die `availability`-Vorlage selbst einen Fehler, gilt der Sensor als
  verfügbar** (`_update_available`: `self._attr_available = True` bei `TemplateError`). In
  `availability` deshalb nie etwas, das werfen kann (z. B. `| float` ohne Standardwert).
- `{{ none }}` ist als Zustand eines Sensors mit `state_class` bzw. Einheit erlaubt (Doku: „must
  render to a number or to `none`“).

## 4. Helligkeit aus der PV (Baustein 4.2)

```
G  = P[kW] / (kWp · PR) · 1000      # Einstrahlung auf die Fläche in W/m²
lx = G · lux_pro_w_m2
```

- Annahme dahinter: Unter Standardbedingungen (1000 W/m²) liefert die Anlage kWp; die
  Performance Ratio PR (Standard 0,8) fasst Verluste durch Wechselrichter, Wärme und Leitungen
  zusammen. Die Leistung ist näherungsweise proportional zur Einstrahlung auf die Modulebene.
- `lux_pro_w_m2`, Standard 110: Lichtausbeute des Sonnenlichts, grob 100–120 lm/W je nach
  Himmel. Das Ergebnis ist eine **Schätzung (etwa ±15 %)**.
- **Einheit W oder kW automatisch erkennen**, über `unit_of_measurement` des Sensors.
  Offen: Verhalten bei fehlender oder unbekannter Einheit – in der Umsetzung festlegen,
  dokumentieren und testen.
- **Negative Werte** (Rauschen in der Nacht) auf 0 setzen.
- PV-Sensor `unavailable` (und `unknown`) → Sensor nicht verfügbar.
- Ausgabe: Zustand in lx; Attribute `einstrahlung_w_m2`, `pv_leistung_kw` (der verwendete Wert),
  `kwp`, `performance_ratio`.
- `device_class`: `illuminance` mit lx, `irradiance` mit W/m² (belegt:
  https://developers.home-assistant.io/docs/core/entity/sensor/, Tabelle der Device Classes).

### Testwerte 4.2 (äußere Vorgabe)

| P | kWp | PR | erwartet |
|---|---|---|---|
| 4 kW bzw. 4000 W | 10 | 0,8 | 500 W/m², 55 000 lx |
| 0 W | 10 | 0,8 | 0 lx |
| −15 W | 10 | 0,8 | 0 lx |
| unavailable | 10 | 0,8 | unavailable |

Größenordnung für Doku und Standardwerte: bedeckter Himmel grob unter 20 000 lx, direkte Sonne
auf der Fläche ab etwa 40 000 lx (daher `helligkeit_schwelle` 40 000 lx in 4.3).

### Grenzen (gehören in die Doku)

- Nur Module **derselben Ebene**; bei mehreren Dachseiten den Sensor der passenden Gruppe bzw.
  des MPP-Trackers.
- **DC-Leistung** verwenden, nicht Einspeisung oder Wechselrichter-Ausgang.
- Bei Nulleinspeisung mit vollem Akku regelt der Wechselrichter ab → Wert zu niedrig.
- Schnee oder Teilverschattung der Module verfälschen den Wert.

## 5. Vorlagen-Werkzeuge in HA

Belegt (https://www.home-assistant.io/template-functions/):

- `sin`, `cos`, `acos`, `pi`, `clamp` (Math).
- `float` mit optionalem Standardwert, wenn die Umwandlung scheitert.
- `has_value`: Entität existiert und ist nicht `unavailable`/`unknown`.

### Template-Blueprints (geklärt am 23.11.2026 für Etappe 2)

„Quelltext“ = HA-Core, Branch `dev` am 23.11.2026; gilt als belegt für das Verhalten, nicht als
Zusage für ältere Versionen.

- **Pfad – belegt.** `use_blueprint: path:` ist relativ zu `config/blueprints/template/`; das
  Beispiel der Doku: `path: homeassistant/inverted_binary_sensor.yaml` für die Datei
  `config/blueprints/template/homeassistant/inverted_binary_sensor.yaml`
  (https://www.home-assistant.io/integrations/template/, Abschnitt „Using blueprints“). Im
  Quelltext: `BLUEPRINT_FOLDER = "blueprints"` (`components/blueprint/const.py`), Ordner
  `hass.config.path(BLUEPRINT_FOLDER, self.domain)` (`components/blueprint/models.py`), Domain
  `template` (`components/template/const.py`). Für die Beispiele in `docs/anleitung.md` also
  `path: <autor>/flaeche_sonneneinfall.yaml`.
- **Nur YAML – belegt.** Die Doku beschreibt Template-Blueprints nur über `configuration.yaml`,
  nicht über die Oberfläche (ebenda).
- **Mehrere Instanzen – belegt.** Aus einem Blueprint lassen sich mehrere Template-Entitäten
  anlegen (ebenda). Ein Blueprint beschreibt dabei eine Entität.
- **`frenck/action-home-assistant` liefert bei Template-Blueprints kein rotes Signal – belegt im
  Quelltext.** Die Action führt im offiziellen Image
  `python -m homeassistant --config … --script check_config` aus, **ohne**
  `--fail-on-warnings` (https://github.com/frenck/action-home-assistant/blob/main/action.yaml,
  neueste Version v1.4.1, kein v2). `check_config` ruft `async_validate_config` der
  Template-Integration auf (`helpers/check_config.py`); die löst `use_blueprint` auf und setzt
  die Eingaben ein (`components/template/config.py`: `async_inputs_from_config`,
  `async_substitute`). Dann gibt es zwei Fälle, beide ohne roten Lauf:
  1. **Schemafehler** (`probatio.Invalid`, früher `vol.Invalid`): fängt die Template-Integration
     selbst ab, schreibt ins Protokoll, legt eine Benachrichtigung an und verwirft den Abschnitt
     mit `continue`. `check_config` sieht nichts.
  2. **Ladefehler** (falscher `path`, YAML kaputt, fehlende Pflichteingabe: `FailedToLoad`,
     `MissingInput`, Unterklassen von `HomeAssistantError`, `components/blueprint/errors.py`):
     landen in `_comp_error`. Ein Fehler wird daraus nur, wenn die Domain zu
     `frontend_dependencies` gehört; `template` gehört nicht dazu → nur **Warnung**. Das Skript
     endet mit `return 1 if res["except"] or (args.fail_on_warnings and res["warn"]) else 0`
     (`scripts/check_config.py`), also mit 0.
  Folge: Aufbau, Eingaben und Optionen der Template-Blueprints sichern die Tests
  (`tests/test_struktur.py`), nicht die CI. Deshalb ruft unser HA-Job `check_config` selbst per
  `docker run` **mit** `--fail-on-warnings` auf (entschieden 23.11.2026, `docs/ENTWURF.md` 6.1;
  im Quelltext: „Exit non-zero if warnings are present“): Fall 2 wird damit rot, Fall 1 bleibt
  unsichtbar.
- **Gegenprobe in der CI – belegt (PR #3, 23.11.2026, HA 2026.11.2).** Je ein eigener Commit
  mit absichtlich kaputter Fixture, danach per Revert zurückgenommen:
  1. **Falscher `path`** (Fall 2): HA-Job **rot**, Exit-Code 1. Meldung unter „Incorrect
     config“ (gelb, also Warnung): „Invalid config for 'template' at configuration.yaml, line 27:
     Failed to load blueprint: Unable to find dachfenster/gibt_es_nicht.yaml“. Unter
     „Successful config (partial)“ blieb `template:` **leer**: Ein Ladefehler einer einzigen
     Instanz kostet in der Prüfung den ganzen `template:`-Abschnitt, auch die intakte zweite
     Instanz. **Im laufenden HA ebenso – belegt im Quelltext** (2026.11.2, Befund
     `ha-experte`): `BlueprintException` erbt von `HomeAssistantError`
     (`blueprint/errors.py`); `template/config.py` fängt je Abschnitt nur `probatio.Invalid`;
     `config.py` (`async_process_component_config`) gibt bei `HomeAssistantError` keine
     Konfiguration zurück; `setup.py`: „Invalid config.“ → `return False`, die Integration
     `template` startet nicht. Beim Neuladen bleibt der alte Stand (`template/services.py`:
     „if conf is None: return“). Gilt laut Quelltext ebenso für eine fehlende Pflichteingabe
     (`MissingInput`) und einen unbekannten Schlüssel unter `use_blueprint:`
     (`InvalidBlueprintInputs`). Ob dann auch über die Oberfläche angelegte Template-Helfer
     fehlen, ist nicht nachgelesen. Warnung in `docs/anleitung.md`.
  2. **Unbekannter Schlüssel** auf Ebene der Instanz (`unbekannt: 1`, Fall 1): HA-Job **grün**,
     Exit-Code 0, obwohl HA ins Log schreibt: „ERROR:homeassistant.config:Invalid config for
     'template' at configuration.yaml, line 42: 'unbekannt' is an invalid option for 'template',
     check: unbekannt“. Der Schlüssel wird also abgelehnt und die Instanz verworfen, nicht
     geduldet. Gefangen haben es nur die Tests (`test_fixture_template_instanzen_passen_zum_blueprint`).
  Laut Quelltext (Befund `ha-experte`, nicht gegengeprüft) ebenfalls **rot**: unbekannter
  Schlüssel **innerhalb** von `use_blueprint:` (`InvalidBlueprintInputs`). Still **grün ohne
  jede Meldung**, Sensor trotzdem angelegt: unbekannter Eingabename unter `input:` und Werte
  außerhalb des Selektors – HA prüft beides bei YAML-Instanzen nicht.
- **Automations-Blueprints – Annahme, noch nicht gegengeprüft.** Laut Quelltext-Auszug
  validiert `components/automation/config.py` mit `raise_on_errors=False`: Blueprint- und
  Schemafehler werden nur protokolliert, die Automation bleibt mit Status `FAILED_BLUEPRINT`
  bzw. `FAILED_SCHEMA` erhalten, `check_config` sieht nichts. Gegenprobe mit dem ersten
  Automations-Blueprint (Etappe 6): absichtlich falsche Eingabe in
  `tests/fixtures/automations.yaml`, CI-Ergebnis hier nachtragen.
- **`template.reload` lädt geänderte Blueprint-Dateien neu – belegt im Quelltext.** Der
  Reload-Dienst leert zuerst den Blueprint-Zwischenspeicher:
  `await async_get_blueprints(hass).async_reset_cache()` (`components/template/services.py`),
  danach liest er `configuration.yaml` neu. Ebenso `automation.reload`
  (`components/automation/services.py`). Die Doku sagt für Automations-Blueprints dasselbe
  („all automations using it pick up the change the next time Home Assistant reloads them“,
  https://www.home-assistant.io/docs/blueprint/), für Template-Blueprints nichts. Live-Bestätigung
  beim ersten `ha_deploy.py`-Lauf (Skill `ha-testen`).
- **Aufbau – belegt** (mitgeliefertes Beispiel
  `components/template/blueprints/inverted_binary_sensor.yaml`, `components/template/config.py`):
  Die Entität steht oben im Blueprint unter dem Plattformschlüssel (`sensor:`), Eingaben kommen
  über `variables: x: !input x` in die Vorlagen. `name` und `unique_id` stehen in der Instanz
  neben `use_blueprint` und werden in die Entität übernommen; mehr als eine Entität je Blueprint
  lehnt HA ab („more than one … entity defined in blueprint“).
- **Optionen – belegt im Quelltext** (`components/template/sensor.py`, `schemas.py`): Der
  Sensor kennt `state` (Pflicht), `device_class`, `state_class`, `unit_of_measurement`,
  `last_reset` (nur mit `state_class: total`) und die gemeinsamen Schlüssel `availability`,
  `attributes`, `icon`, `picture`, `name`, `unique_id`, `variables`, `default_entity_id`,
  `conditions`. Keine Kreuzprüfung von `state_class` und Einheit. `tests/test_struktur.py`
  prüft, dass unser Sensor nur diese Schlüssel nutzt.
- **Mindestversion.** Seit wann es Template-Blueprints gibt, ist nicht genau belegt; spätestens
  seit 2024.4 (Glossar in den Release-Notes 2024.4: „A blueprint is a script, automation, or
  template entity configuration …“). Maßgeblich ist bei uns `clamp` (seit 2025.4) →
  `min_version: 2025.4.0`; `test_min_version_reicht_fuer_clamp` hält das fest.
  `min_version` hat das Format `major.minor.patch`, alle drei Teile Pflicht, z. B. `2022.4.0`
  (https://www.home-assistant.io/docs/blueprint/schema/).
- **`default_config` bringt in der CI keine eigenen Warnungen – belegt.** Der erste Lauf des
  HA-Jobs mit `--fail-on-warnings` (PR #2, 23.11.2026) war grün. Die Fixture behält deshalb
  `default_config:`; sie bringt auch die Sun-Integration (`sun.sun`) mit.

Die Tests bauen diese Funktionen in `tests/conftest.py` nach. Weicht der Nachbau von HA ab
(z. B. Fehler statt Standardwert), ist der Test wertlos. **Die CI fängt das nicht ab:**
`check_config` prüft Aufbau und Schema, wertet aber keine Vorlage aus. Den Nachbau sichern nur
der Beleg in der HA-Doku (hier) und der Vergleich im echten HA (Live-Prüfung, Skill `ha-testen`).
