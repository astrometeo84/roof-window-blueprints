# Mitmachen

Verbindliche Spezifikation: [`docs/ENTWURF.md`](docs/ENTWURF.md). Hintergründe zu Physik, Testaufbau
und Werkzeugen: [`docs/entwicklung.md`](docs/entwicklung.md).

## Ablauf

1. Branch von `main` anlegen: `feat/…`, `fix/…`, `docs/…`, `chore/…`, `ci/…`.
2. Ändern. Neue Logik: erst der Test, dann prüfen, dass er ohne die Änderung fehlschlägt.
3. Lokal prüfen:
   ```bash
   uv sync --locked
   uv run pytest
   uv run yamllint --strict .
   ```
4. Im echten Home Assistant ausprobieren (`uv run scripts/ha_deploy.py`, siehe Kopf des Skripts).
5. Pull Request nach `main`. Die CI prüft YAML-Stil, Tests und ob Home Assistant die Blueprints lädt.

## Commit-Präfixe

Commits nach [Conventional Commits](https://www.conventionalcommits.org/), auf Deutsch und so
formuliert, dass sie im CHANGELOG verständlich sind. Die Tabelle muss zu
`.release-please-config.json` passen; `tests/test_struktur.py` prüft das.

| Präfix | Wofür | CHANGELOG-Abschnitt | Löst Release aus |
|---|---|---|---|
| `feat` | neue Funktion, neuer Blueprint, neue Eingabe | Hinzugefügt | ja |
| `fix` | Fehler behoben | Behoben | ja |
| `perf` | gleiches Ergebnis, weniger Aufwand (z. B. seltener neu berechnen, weniger Fahrten) | Geändert | ja |
| `refactor` | Umbau ohne sichtbare Änderung | – | nein |
| `docs` | nur Doku | – | nein |
| `test` | nur Tests | – | nein |
| `ci` | Workflows, CI-Fixtures | – | nein |
| `chore` | Werkzeuge, Abhängigkeiten, Repo-Pflege | – | nein |

**Bruch bestehender Einrichtungen** (Eingabe umbenannt oder entfernt, neue Eingabe ohne
Standardwert): `feat!:` bzw. `fix!:` und im Rumpf `BREAKING CHANGE: …`. In der 0.x-Phase hebt das
die zweite Stelle an (0.3.0 → 0.4.0), nicht sofort auf 1.0.0 (`bump-minor-pre-major`).

## Wie ein Release entsteht

release-please erzeugt Version, CHANGELOG, Tag und Release aus den Commits.

1. PR nach `main` mergen.
2. Der Bot legt den PR `chore(main): release X.Y.Z` an oder aktualisiert ihn: CHANGELOG und Version
   im Kopf jeder Blueprint-Datei.
3. Weitere Merges sammeln sich im selben Release-PR.
4. **Release-PR einmal schließen und wieder öffnen.** Einen PR, den der Bot mit dem Standard-Token
   anlegt oder aktualisiert, prüft GitHub nicht; ohne die Pflichtprüfungen lässt das Ruleset ihn
   nicht mergen. Schließen und wieder öffnen startet die Prüfungen. Nach jeder neuen Aktualisierung
   durch den Bot wiederholen.
5. Release-PR mergen → Tag, GitHub-Release; alle Blueprint-Dateien unter `blueprints/` werden ans
   Release gehängt.

Keine Version von Hand, kein Tag, `CHANGELOG.md` nicht anfassen. Die Version steht nur im Kopf der
Blueprints (`# Version: … # x-release-please-version`); `pyproject.toml` bleibt absichtlich bei
`version = "0"`.

Zurücknehmen: `gh release delete vX.Y.Z --yes`, Tag löschen, Version in
`.release-please-manifest.json` zurücksetzen.

## GitHub-Einstellungen (einmalig, Repo-Inhaber)

- Ruleset für `main`: Löschen und Force-Push sperren, PR erforderlich, Approvals 0, erforderliche
  Prüfungen: `YAML-Stil`, `Tests (Python 3.13)`, `Tests (Python 3.14)`,
  `Home Assistant lädt die Blueprints`. Die Namen erscheinen erst nach dem ersten Lauf zur Auswahl.
- Settings → Actions → General: „Allow GitHub Actions to create and approve pull requests“ an,
  sonst darf der Bot den Release-PR nicht anlegen.
- Secret Scanning und Push Protection an.
- Kein Ruleset, das das Anlegen von `v*`-Tags verbietet – den Tag legt release-please an.
