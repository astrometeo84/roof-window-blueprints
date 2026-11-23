---
name: ha-testen
description: Blueprints von roof-window-blueprints vor dem Merge im echten Home Assistant des Nutzers ausprobieren – Feature-Branch auf dem PC auschecken, Dateien hinüberspielen, Konfiguration prüfen, Automationen und Template-Entitäten neu laden, Zustände und Traces prüfen.
---

# Blueprints im echten Home Assistant testen

**Der Container erreicht Home Assistant nicht** (absichtlich, kein Weg ins Heimnetz). Claude Code
nennt die Befehle, der Nutzer führt sie auf seinem PC aus. Der PR wird erst nach dem Test
gemergt.

Befehle immer einzeln nennen, jeweils mit der erwarteten Ausgabe.

## 1. Branch auf den PC holen

```bash
git fetch origin
git switch <feature-branch>
git pull
```

Erwartet: `Switched to branch '<feature-branch>'`, danach `Already up to date.` oder die neuen
Commits.

## 2. Vorher prüfen

```bash
uv sync --locked
uv run pytest
uv run yamllint --strict .
```

Erwartet: alle Tests grün (Live-Tests übersprungen), yamllint ohne Ausgabe. Schlägt etwas fehl,
erst das beheben – einen Blueprint, den die Tests ablehnen, lädt HA oft gar nicht erst.

## 3. Hinüberspielen

```bash
uv run scripts/ha_deploy.py --trocken
uv run scripts/ha_deploy.py
```

`--trocken` zeigt Ziel und Dateien und ändert nichts. Ohne `--trocken` kopiert das Skript beide
Blueprint-Arten aus dem Arbeitsverzeichnis (`blueprints/automation/dachfenster/`,
`blueprints/template/dachfenster/`), lässt HA die Konfiguration prüfen und lädt Automationen
**und** Template-Entitäten neu. Ein Neustart sollte nicht nötig sein; ob `template.reload`
geänderte Template-Blueprints wirklich neu lädt, ist noch offen (`docs/ENTWURF.md` Abschnitt 8)
– im Zweifel einmal HA neu starten und das Ergebnis im Skill nachtragen.

Einstellungen stehen in `.ha.env` (Vorlage `.ha.env.example`), **nur auf dem PC des Nutzers**.
Fehlt die Datei: dem Nutzer die Vorlage zeigen und ihn bitten, sie anzulegen. Den Inhalt nie
lesen, ausgeben oder erfragen (Skill `security-secrets`).

## 4. Was der Nutzer prüfen soll

Passend zur Änderung eine kurze Liste geben, zum Beispiel:

- **Template-Blueprints:** Entwicklerwerkzeuge → Zustände, Sensor suchen. Zustand und Attribute
  (`cos_einfall`, `sonne_trifft_flaeche`, `azimut`, `neigung` bzw. `einstrahlung_w_m2`,
  `pv_leistung_kw`, `kwp`, `performance_ratio`) plausibel? Einheit und Gerätetyp richtig?
- **Sonneneinfall:** mit dem aktuellen Sonnenstand (`sun.sun`) vergleichen; Plausibilität:
  nachts `sonne_trifft_flaeche` falsch, mittags bei Südfläche kleines θ.
- **Helligkeit:** Wert zur aktuellen PV-Leistung nach der Formel aus 4.2 nachrechnen.
- **Automationen:** Automation öffnen, neue Eingaben ausfüllen und speichern (sonst gelten die
  Standardwerte). Unter ⋮ → **Traces** nachsehen, welcher Zweig lief und warum.
- **Beschattung:** Positionswerte und `cover.set_cover_position` über HomeKit-Controller prüfen,
  sobald der KIG 300 eingebunden ist (0 = zu, 100 = offen).
- **Warnung:** Meldung kommt mit `tag`, Priorität hoch, iOS `time-sensitive`; beim Schließen des
  Fensters verschwindet sie (`clear_notification`).
- Einstellungen → System → Protokolle: Fehler oder Warnungen zu den Blueprints?

Der Nutzer meldet nur Zahlen, Zustände und Schlüsselnamen zurück – keine Adresse, keinen Token,
keine Koordinaten.

## 5. Optionale Live-Prüfung

Lesend gegen die REST-API, nur vom PC des Nutzers: `scripts/run-live-tests.ps1` (Adresse und
Token per `Read-Host`, Token mit `-AsSecureString`). Ablauf in `docs/LIVE_TESTS.md`. Nie in CI,
nie im Container.

## 6. Danach

Passt alles: Der Nutzer merged den PR (oder gibt Bescheid). Passt etwas nicht: Rückmeldung
aufnehmen, auf demselben Feature-Branch weiter ändern, Schritt 1–4 wiederholen.
