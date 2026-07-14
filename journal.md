# Lauftagebuch — Handwerk-Lead-SDR

---

## 2026-07-14 — Lauf #1 (Erstlauf / Bootstrap)

### Setup
- Repo war leer → alle Zustandsdateien angelegt: `sources.json`, `leads.jsonl`, `journal.md`, `metrics.csv`, `feedback.md`, `daily/`, `README.md`.
- `sources.json` mit 21 Seed-Quellen aus §4 befüllt (Status durchgehend `unbewiesen`, da noch keine Ertragsdaten).

### Planung (Erstlauf → hoher Explore-Anteil)
- Kein Ertragswissen vorhanden → statt 70/20/10 bewusst **explore-lastig** gefahren: breite Abdeckung über Gewerke × Regionen, um Baseline-Yield je Segment zu gewinnen.
- Budget: Ziel 25 neue Leads. Harvest über 8 parallele Recherche-Segmente:
  1. SHK — Bayern (DE)
  2. Elektro — NRW (DE)
  3. Maler & Lackierer — Baden-Württemberg (DE)
  4. Tischler/Schreiner — Niedersachsen/Hamburg (DE)
  5. Dachdecker/Zimmerer — Sachsen/Thüringen (DE)
  6. GaLaBau + Metallbau — Hessen/RLP (DE)
  7. Installateur + Elektro — Wien/NÖ/Bgld (AT)
  8. Maler/Fliesen/Tischler — OÖ/Stmk/Tirol/Sbg (AT)

### Methodik (Compliance-konform)
- **Kein Massen-Scraping** von Verzeichnissen (Google Maps/LinkedIn ausgeschlossen, `zugriff: manuell`).
- Verzeichnisse/Suche liefern nur Kandidaten-**Namen**; **verifiziert** wird jeder Fakt über das **öffentlich-pflichtige Impressum** der Firma selbst (DSGVO-konform, berechtigtes Interesse).
- Harte Regel an alle Recherche-Agents: **kein Feld raten**, unbekannt = null, jeder Lead braucht eine tatsächlich abgerufene URL. Lieber weniger echte als mehr geratene Leads.

### Ergebnisse
<!-- wird nach Harvest gefüllt: gefunden / qualifiziert / übergeben / Dubletten / avg_score / Top-Segmente -->
_(wird nach Abschluss des Harvests ergänzt)_

### Beobachtungen / Hypothesen fürs nächste Mal
<!-- wird nach Harvest gefüllt -->

### Quellen-Backlog (zu prüfen an Folgetagen)
- Regionale HWK-Betriebssuchen einzeln erschließen und je als eigene Quelle mit Selektoren erfassen (hwk-muenchen.de, hwk-koeln.de, hwk-stuttgart.de, …).
- Gewerkespezifische Innungs-Mitgliederlisten (oft die saubersten, kleinsten Betriebe).
- `firmen.wko.at` strukturiert je Sparte/Bundesland durchgehen (AT-Kernquelle).
- Stellenbörsen (Indeed/regionale) als Signal-Layer systematisch anbinden (Wachstums-Flag).
- Noch nicht abgedeckte Regionen für Folgeläufe: Berlin/Brandenburg, Schleswig-Holstein, Saarland (DE); Vorarlberg, Kärnten-Tiefe (AT).
- Noch nicht abgedeckte Gewerke: Bodenleger/Parkett, Estrichleger, Fenster-/Rollladenbau, reiner Trockenbau.
