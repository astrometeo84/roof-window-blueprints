---
name: security-secrets
description: Regeln und Prüfliste für Zugangsdaten und private Daten in roof-window-blueprints (HA-Token, GitHub-App-Schlüssel, Daten aus dem Haus des Nutzers). Verwenden, wenn Skripte, Tests, Fixtures, Doku, Commits oder PR-Texte entstehen oder geprüft werden, und vor jedem Commit.
---

# Zugangsdaten und private Daten

## Was hier geheim ist

- **Home-Assistant-Token** (Long-Lived Access Token) und die Adresse des HA.
- **GitHub-App-Schlüssel** und Installations-Token.
- Nicht geheim, aber **privat** (im Repo genauso behandeln): Koordinaten und Adresse des Hauses,
  echte Entitäts-IDs, Namen von Personen und Geräten, Anlagenwerte (kWp, Ausrichtung, Neigung
  der echten Anlage). Im Repo stehen nur Beispielwerte und Platzhalter wie
  `binary_sensor.dachfenster_kontakt` oder `person.DEIN_NAME`.

## HA-Token

1. Der Token steht **nur in `.ha.env` auf dem PC des Nutzers**. Die Datei steht in `.gitignore`
   und existiert nie im Container. Vorlage ist `.ha.env.example` (nur Platzhalter).
2. Claude Code legt den Token nie an, fragt nie danach, liest `.ha.env` nie und gibt nichts
   daraus aus. Fehlt die Datei: Vorlage zeigen, der Nutzer legt sie an.
3. Live-Tests: Adresse und Token per `Read-Host` (Token mit `-AsSecureString`), nie auf der
   Kommandozeile, in Umgebungsvariablen von Beispielbefehlen oder in der PowerShell-Historie.
   Token eines eigenen HA-Benutzers **ohne Adminrechte**, nur lesend.
4. Skripte (`scripts/ha_deploy.py`, Live-Tests) geben Token und Adresse nie aus – nicht in Logs,
   Fehlermeldungen oder Berichten. Ein Test belegt, dass der Live-Bericht weder Adresse noch
   Token enthält; Test-Token offensichtlich falsch wählen, z. B. `"token-test-GEHEIM"`.

## GitHub-App

- Der private Schlüssel gehört nur dem Benutzer `ghapp` (Modus `600`), der Token-Cache ebenso.
  `dev` bekommt kurzlebige Installations-Token über `ghb`; nie einen Token ausgeben, in eine
  Datei im Repo schreiben oder in die Shell-Historie bringen.
- Die App hat nur Contents und Pull requests – keine Workflows, keine Tags, keine Releases.

## Grenzen der Sicherung

Die Verbote in `.claude/settings.json` sind nur eine zusätzliche Hürde. Die eigentlichen
Sicherungen: das Ruleset auf GitHub (kein direkter Push nach `main`, kein Bypass), Secret
Scanning und Push Protection, und dass `.ha.env` nie im Container liegt.

## Prüfliste vor jedem Commit

```bash
git diff --cached
```

- [ ] Kein Token, Passwort, privater Schlüssel, keine HA-Adresse
- [ ] Keine echten Koordinaten, Adressen, Entitäts-IDs, Personennamen oder Anlagenwerte
      (Code, Tests, Fixtures, Doku, Commit-Nachricht, PR-Text)
- [ ] `.ha.env` nicht gestaged, `.ha.env.example` enthält nur Platzhalter
- [ ] Neue Ausgaben in Skripten enthalten keine Adresse und keinen Token (mit Test)
