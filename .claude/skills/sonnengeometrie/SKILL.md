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
  `acos` wirft dann einen Fehler. Begrenzen mit `[[x, -1] | max, 1] | min` oder `clamp`
  (welche Variante, entscheidet die Umsetzung; im Test beide Grenzen prüfen).
- **Azimut 0/360:** Die Differenz A_s − A_f geht nur über `cos` ein, daher ist keine
  Normalisierung nötig. Test: A_f = 0 und A_f = 360 liefern dasselbe θ.
- **Neigung 0:** cos θ = sin(h), θ = 90° − h, unabhängig von beiden Azimuten.
- **Neigung 90:** cos θ = cos(h) · cos(A_s − A_f) (senkrechte Fassade).
- **`sonne_trifft_flaeche`:** wahr genau dann, wenn h > 0 **und** cos θ > 0. Bei θ = 90° genau
  (cos θ = 0) ist es falsch. Nachts kann cos θ > 0 sein (Sonne unter dem Horizont, aber „vor“ der
  Fläche), deshalb gehört die Prüfung h > 0 dazu.
- Ausgabe: θ in ° mit **einer** Nachkommastelle; Attribute `cos_einfall`,
  `sonne_trifft_flaeche`, `azimut`, `neigung`.

### Testwerte 4.1 (äußere Vorgabe, einmal im Test ausgeschrieben)

| Fläche A_f / β | Sonne A_s / h | θ | Kontrolle |
|---|---|---|---|
| 180 / 40 | 180 / 60 | 10,0° | cos θ = sin(60° + 40°) = sin 100° |
| 180 / 40 | 0 / 10 | 120,0° | cos θ = sin(10° − 40°) = −0,5 → Sonne hinter der Fläche |
| beliebig / 0 | beliebig / 30 | 60,0° | cos θ = sin 30° = 0,5 |
| 90 / 90 | 90 / 10 | 10,0° | cos θ = cos 10° |

Zusätzliche Randfälle für Tests: h ≤ 0, θ genau 90°, cos θ minimal über 1 bzw. unter −1,
Neigung 0 und 90, Azimut 0 und 360, fehlende Attribute beim Sonnenstand.

## 3. Sonnenstand in Home Assistant

- Die Sun-Integration bietet Sensoren **Elevation** („Negative values mean the sun is below the
  horizon.“) und **Azimuth** („The angle is shown clockwise from north.“). Dieselben Werte stehen
  „for backward compatibility“ als Attribute an `sun.sun` (belegt:
  https://www.home-assistant.io/integrations/sun/). Ein Abkündigungshinweis steht dort nicht.
- **Offen:** genaue Attributnamen an `sun.sun` (erwartet `elevation`, `azimuth`) und
  Entitäts-IDs der Sensoren; ob die Sensoren standardmäßig aktiviert sind; wie oft aktualisiert
  wird. Entscheidung, ob die Vorlage `sun.sun`-Attribute oder die Sensoren nutzt, mit Beleg hier
  nachtragen. Die Doku nennt keine Einheit für h; „Grad“ ergibt sich aus dem Beispiel
  „0 degrees and -6 degrees“ (Dämmerung).
- Fehlt der Sonnenstand (Attribut fehlt, `unavailable`), liefert die Vorlage keinen Fantasiewert,
  sondern ist nicht verfügbar (`availability`). Test dafür.

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
- **`frenck/action-home-assistant` prüft mit – mit Lücke, belegt im Quelltext.** Die Action
  führt im offiziellen Image `python -m homeassistant --config … --script check_config` aus
  (https://github.com/frenck/action-home-assistant/blob/main/action.yaml, neueste Version
  v1.4.1, kein v2). `check_config` ruft `async_validate_config` der Template-Integration auf
  (`helpers/check_config.py`), und die löst `use_blueprint` auf und setzt die Eingaben ein
  (`components/template/config.py`: `async_inputs_from_config`, `async_substitute`).
  **Lücke:** Scheitert danach das Schema (`vol.Invalid`), fängt die Template-Integration das
  selbst ab, schreibt ins Protokoll, legt eine Benachrichtigung an und verwirft den Abschnitt
  mit `continue`. `check_config` sieht **keinen Fehler**, die CI bleibt grün. Erkannt werden nur
  Fehler beim Laden des Blueprints (Datei fehlt, YAML kaputt, fehlende Pflichteingabe), sofern
  sie als `HomeAssistantError` ankommen. Folge: Die Tests müssen Aufbau und Optionen der
  Template-Blueprints selbst prüfen (`tests/test_struktur.py`); die CI ist hier nur ein
  zusätzliches Netz. **Offen:** ob ein Ladefehler bei `template` als Fehler oder nur als
  Warnung zählt (das hängt an `frontend_dependencies`; `--fail-on-warnings` setzt die Action
  nicht). Gegenprobe mit dem ersten Template-Blueprint (Etappe 3): absichtlich falschen `path`
  und absichtlich falsche Option in die Fixture, CI-Ergebnis hier nachtragen.
- **`template.reload` lädt geänderte Blueprint-Dateien neu – belegt im Quelltext.** Der
  Reload-Dienst leert zuerst den Blueprint-Zwischenspeicher:
  `await async_get_blueprints(hass).async_reset_cache()` (`components/template/services.py`),
  danach liest er `configuration.yaml` neu. Ebenso `automation.reload`
  (`components/automation/services.py`). Die Doku sagt für Automations-Blueprints dasselbe
  („all automations using it pick up the change the next time Home Assistant reloads them“,
  https://www.home-assistant.io/docs/blueprint/), für Template-Blueprints nichts. Live-Bestätigung
  beim ersten `ha_deploy.py`-Lauf (Skill `ha-testen`).
- **Optionen und Mindestversion – offen.** Die Doku sagt nicht, welche Optionen (`attributes`,
  `availability`, `unit_of_measurement`, `device_class`, `state_class`, `delay_on`/`delay_off`)
  in einem Template-Blueprint gehen und ab welcher Version es Template-Blueprints gibt. Klären mit
  dem ersten Template-Blueprint (Etappe 3). `min_version` hat das Format `major.minor.patch`, alle
  drei Teile Pflicht, z. B. `2022.4.0` (https://www.home-assistant.io/docs/blueprint/schema/).

Die Tests bauen diese Funktionen in `tests/conftest.py` nach. Weicht der Nachbau von HA ab
(z. B. Fehler statt Standardwert), ist der Test wertlos. **Die CI fängt das nicht ab:**
`check_config` prüft Aufbau und Schema, wertet aber keine Vorlage aus. Den Nachbau sichern nur
der Beleg in der HA-Doku (hier) und der Vergleich im echten HA (Live-Prüfung, Skill `ha-testen`).
