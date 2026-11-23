# Anleitung

Einrichtung der Blueprints in Home Assistant. Diese Datei wächst mit jedem Blueprint; die
vollständige Fassung (Checkliste, Gut zu wissen, Fehlersuche für alle Bausteine) folgt in
Etappe 8 (`docs/ENTWURF.md` Abschnitt 9).

Alle Entitäts-IDs und Zahlen hier sind **Beispiele**.

## Template-Blueprints einbinden – so funktioniert es

Template-Blueprints legen Sensoren an. Anders als Automations-Blueprints werden sie nicht in der
Oberfläche eingerichtet, sondern in `configuration.yaml` unter `template:` mit `use_blueprint:`.

1. Die Blueprint-Datei liegt im HA-Konfigurationsordner unter `blueprints/template/`, in einem
   eigenen Unterordner, z. B. `blueprints/template/dachfenster/flaeche_sonneneinfall.yaml`.
   - aus dem Release: Datei am [GitHub-Release](../../../releases) herunterladen und dorthin
     kopieren (Samba-Freigabe, File-Editor- oder SSH-Add-on);
   - zum Ausprobieren eines Branches: `uv run scripts/ha_deploy.py` (Skill `ha-testen`) kopiert
     genau an diese Stelle.
2. In `configuration.yaml` unter `template:` eine Instanz anlegen. `path` ist relativ zu
   `blueprints/template/`.
3. Konfiguration prüfen: Einstellungen → Werkzeuge (früher „Entwicklerwerkzeuge“) → YAML →
   „Konfiguration prüfen“. Die Werkzeuge sehen nur Administratoren.
4. Neu laden: dort unter „YAML-Konfiguration neu laden“ den Punkt „Template-Entitäten“. Steht
   er nicht in der Liste (es gab vorher keine Template-Entitäten), Home Assistant einmal neu
   starten.
5. Nachsehen, ob der Sensor da ist (Werkzeuge → Zustände). **Fehlt er, hat HA die Instanz
   verworfen** – Einstellungen → System → Protokolle und die Benachrichtigungen ansehen. Ein
   unbekannter Schlüssel neben `use_blueprint`, `name` und `unique_id` führt dazu; die
   Konfigurationsprüfung meldet das nicht.
6. **Namen und Werte der Eingaben prüft HA nicht.** Ein falsch geschriebener Eingabename wird
   still ignoriert, und ein Wert außerhalb des Bereichs (z. B. `neigung: 400`) wird übernommen.
   Schreibweise genau wie im Beispiel, Azimut 0–360, Neigung 0–90; die Attribute `azimut` und
   `neigung` am Sensor zeigen, was angekommen ist.

**Achtung bei einem falschen `path`, einer fehlenden Pflichteingabe oder einem unbekannten
Schlüssel unter `use_blueprint:`:** Dann richtet Home Assistant beim nächsten Start **keine
einzige** Template-Entität aus `configuration.yaml` ein, nicht nur diese Instanz fehlt; es
erscheint die Meldung „Invalid config“ für `template`. Beim Neuladen der Template-Entitäten wird
in diesem Fall gar nichts übernommen, die bisherigen Entitäten bleiben mit dem alten Stand. Die
Konfigurationsprüfung zeigt den Fehler vorher als Warnung an – vor dem Neuladen oder Neustart
beheben.

Die Menüpunkte sind nach der HA-Doku beschrieben; die genaue deutsche Beschriftung wird beim
ersten Live-Test bestätigt.

Steht in `configuration.yaml` schon `template: !include templates.yaml` o. Ä., gehört die
Instanz in diese Datei (als weiterer Listeneintrag `- use_blueprint: …`).

## Fläche – Sonneneinfall

Einfallswinkel der Sonne auf eine Fläche (Dachfenster, Fassade, Dachfläche).

**Voraussetzung:** Sun-Integration (`sun.sun`; Teil von `default_config`, in einer normalen
Installation vorhanden). Home Assistant ab 2025.4.

**Eingaben** (beide Pflicht, kein Standardwert):

| Eingabe | Bedeutung | Beispiel |
|---|---|---|
| `azimut` | Richtung, in die die Fläche **schaut**, wie ein Kompass: 0 = Nord, 90 = Ost, 180 = Süd, 270 = West | 180 |
| `neigung` | 0 = waagerecht, 90 = senkrecht; beim Dachfenster die Dachneigung | 40 |

Liegt eine PV-Anlage in derselben Dachfläche, stehen Ausrichtung und Neigung meist in ihrer
Planung bzw. in der Prognose-Integration. Achtung: Manche Programme zählen den Azimut anders
(z. B. 0 = Süd); hier gilt immer der Kompass.

**Beispiel für `configuration.yaml`:**

```yaml
template:
  - use_blueprint:
      path: dachfenster/flaeche_sonneneinfall.yaml
      input:
        azimut: 180
        neigung: 40
    name: Dachfenster Sonneneinfall
    unique_id: dachfenster_sonneneinfall
```

`name` und `unique_id` sind optional, aber empfohlen: Mit `unique_id` lässt sich der Sensor in
der Oberfläche umbenennen und einem Bereich zuordnen. Für weitere Flächen einfach weitere
Einträge `- use_blueprint: …` mit eigenem `name` und eigener `unique_id` anlegen.

**Was der Sensor zeigt:**

- **Zustand:** Einfallswinkel θ in Grad, eine Nachkommastelle. 0° = Sonne steht senkrecht auf
  der Fläche, 90° = streifend, über 90° = Sonne hinter der Fläche.
- `cos_einfall`: cos θ mit vier Nachkommastellen (1 = voll, 0 = streifend, negativ = von hinten).
  Grob der Anteil der direkten Sonne, der auf die Fläche fällt.
- `sonne_trifft_flaeche`: `true`, wenn die Sonne über dem Horizont **und** vor der Fläche steht.
- `azimut`, `neigung`: die eingetragenen Werte, zur Kontrolle.

**Gut zu wissen:**

- Der Sensor rechnet neu, sobald sich der Sonnenstand an `sun.sun` ändert: am Tag etwa alle
  2–4 Minuten, nachts alle 20 Minuten. Er springt deshalb in kleinen Schritten.
- Fehlt der Sonnenstand (z. B. kurz nach einem Neustart), ist der Sensor „nicht verfügbar“ statt
  einen falschen Wert zu zeigen.
- Bei ganz streifendem Licht kann der Zustand `90.0` zeigen und `sonne_trifft_flaeche` trotzdem
  `true` sein: Der Zustand ist auf eine Stelle gerundet, `cos_einfall` auf vier. Maßgeblich ist
  `sonne_trifft_flaeche`.
- Nachts zeigt der Zustand trotzdem einen Winkel (die Sonne steht dann „unter“ der Erde);
  maßgeblich ist `sonne_trifft_flaeche`.
- Der Sensor kennt keine Verschattung durch Nachbarhäuser, Bäume oder Gauben; er rechnet rein
  geometrisch.

**Plausibel prüfen:** Bei einer Südfläche ist θ mittags am kleinsten; im Winter ist θ bei
steilen Flächen kleiner als bei flachen, im Sommer umgekehrt. Nachrechnen lässt es sich mit dem
aktuellen Sonnenstand (Werkzeuge → Zustände → `sun.sun`, Attribute `elevation`,
`azimuth`) und der Formel in `docs/entwicklung.md`.
