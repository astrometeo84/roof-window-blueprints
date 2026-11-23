# roof-window-blueprints – Projektregeln für Claude Code

Home-Assistant-Blueprints rund um ein manuelles Dachfenster mit Solar-Rollladen:
Sonneneinfall auf einer Fläche, Helligkeit aus der PV, Beschattung, Warnung bei offenem Fenster.
Lizenz: MIT. Die verbindliche Spezifikation ist `docs/ENTWURF.md`.

## Sprache

- Mit dem Nutzer: **Deutsch**.
- Doku, Blueprint-Texte, Kommentare, Commit-Nachrichten und PR-Texte: **Deutsch**.
- Befehle für den Nutzer einzeln nennen, jeweils mit der erwarteten Ausgabe.

## Vor jeder Änderung lesen

`README.md`, `CONTRIBUTING.md`, `docs/entwicklung.md` (sobald vorhanden, Etappe 2 und 8) und die
Kommentare in den Blueprints. Dort steht, warum bestimmte Dinge so sind, wie sie sind. Was dort
begründet ist, nicht „aufräumen“. Beispiel: `version = "0"` in der `pyproject.toml` (sonst läuft
`uv.lock` weg und die CI des Release-PR scheitert an `--locked`).

## Sicherheitsregeln (nicht verhandelbar)

1. **Keine Geräte im Heimnetz ansprechen.** Der Container hat absichtlich keinen Weg dorthin.
   Live-Tests macht der Nutzer (Skill `ha-testen`, `docs/LIVE_TESTS.md`).
2. **Keine Zugangsdaten** anlegen, erfragen, speichern oder ausgeben (Skill `security-secrets`).
3. **Keine echten Daten aus dem Haus des Nutzers ins Repo:** keine Koordinaten, Adressen,
   Entitäts-IDs oder Anlagenwerte, nur Beispielwerte.
4. **GitHub:** nur Feature-Branches (`feat/…`, `fix/…`, `docs/…`, `chore/…`, `ci/…`), Pushes nur
   nach Rückfrage, PRs mit `ghb pr create`. Nie direkt nach `main`, nie Force-Push, nie Tags,
   nie Releases.
5. **`.github/workflows/` nicht ändern** (die GitHub App darf das nicht). Vorschläge als Text an
   den Nutzer.
6. **Neue Abhängigkeiten nur nach Rückfrage.**
7. **Nichts aus dem Code von Solar Forecast ML (SFML) übernehmen** (proprietäre Lizenz). Die
   Physik hier ist Lehrbuchwissen.

Die Verbote in `.claude/settings.json` sind nur eine zusätzliche Hürde. Die eigentliche
Sicherung ist das Ruleset auf GitHub; daran ändert eine Erlaubnis im Container nichts.

## Releases

- release-please erzeugt Version, CHANGELOG und Release-PR. Keine Version von Hand, keinen Tag
  setzen, `CHANGELOG.md` nicht anfassen. Die Version steht nur im Kopf jeder Blueprint-Datei
  (`# x-release-please-version`).
- Commits nach Conventional Commits, auf Deutsch, so formuliert, dass sie im CHANGELOG
  verständlich sind. `feat`, `fix` und `perf` erscheinen im CHANGELOG und lösen ein Release aus;
  `docs`, `test`, `ci`, `chore`, `refactor` nicht.
- Bricht eine Änderung bestehende Einrichtungen (Eingabe umbenannt oder entfernt):
  `feat!:` plus `BREAKING CHANGE:` im Rumpf.

## Tests

- Die Tests lesen die Jinja-Vorlagen **direkt aus den Blueprint-Dateien**, keine Kopien.
  Standardwerte über `input_default()` lesen, nicht abschreiben.
- Neue Logik: erst der Test, dann prüfen, dass er ohne die Funktion fehlschlägt (Blueprint
  absichtlich kaputt machen). Erkannte Fehler in die Tabelle „Taugen die Tests etwas?“ in
  `docs/entwicklung.md` eintragen.
- Jede Eigenheit im Skill `sonnengeometrie` braucht einen Test.

## Prüf-Agenten

- Vor jedem Push den Subagent `test-manager` aufrufen; bei Änderungen an Vorlagen, Physik,
  Selektoren oder HA-Verhalten zusätzlich `ha-experte`.
- Befunde unter BLOCKIERT beheben, die Berichte im PR-Text kurz zusammenfassen.
- Gegenproben (läuft der Test ohne die Änderung rot?) mit `git stash` oder `git worktree`,
  nie mit `git checkout --` oder `git restore`.

## Arbeitsweise

- Vor größeren Schritten einen kurzen Plan zeigen und auf Freigabe warten.
- Die Spezifikation nur nach Rückfrage ändern; Abweichungen in `docs/ENTWURF.md` nachziehen.
- Unklarheiten: erst Doku und Skills prüfen, dann fragen, nicht raten.
- Verhalten von Home Assistant in der aktuellen Doku prüfen (`www.home-assistant.io`,
  `developers.home-assistant.io`); HA kündigt regelmäßig Muster ab.

## Befehle

```bash
uv sync --locked              # Werkzeuge installieren
uv run pytest                 # Tests (ohne Live-Tests)
uv run yamllint --strict .    # YAML-Stil
```

## Skills und Agenten in diesem Repo

- `sonnengeometrie`: Formeln, Zählweisen, Umrechnung PV → W/m² → lx, Testwerte, Grenzen.
- `neuer-blueprint`: alle Stellen, die ein neuer Blueprint oder eine neue Eingabe berührt.
- `ha-testen`: Blueprints vor dem Merge im echten Home Assistant ausprobieren (Nutzer).
- `security-secrets`: HA-Token, GitHub-App-Schlüssel, private Hausdaten.
- Agenten `test-manager` und `ha-experte`: schreibgeschützte Gegenprüfung vor jedem Push.
