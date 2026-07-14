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
- **Roh-Kandidaten:** 47 · **Qualifiziert (ICP):** 47 · **Übergeben heute:** 25 · **Backlog/Reserve:** 22 · **Dubletten:** 0 (Erstlauf, leere Historie).
- **Ø-Score (1–5):** 4.09 · **Verteilung:** A=9, B=34, C=3, D=1, E=0.
- **Länder:** DE=36, AT=11. **Gewerke:** SHK/Installation 9, Elektro 9, Maler/Stuck. 8, Tischler 8, Dach/Zimmerer 6, GaLaBau 3, Metallbau 3, Fliesenleger 1.
- **Alle 47** über das **firmeneigene Impressum** verifiziert (Name/Adresse/Tel/Mail belegt). Kein erfundenes Feld; Unbekanntes = null.
- **Ausgeschlossen & dokumentiert:** ~10 Betriebe (>25 MA wie Stemmle ~80, Schäffer ~70, Maroscheck ~90, MD Elektrotechnik 28, antignum-Gruppe; Region außerhalb: Wendt/Rabe SH; nicht verifizierbar/503: Fliesen Team Salzburg, Ilia-Oarda Mainz, Lehner Ingolstadt).

### Beobachtungen / Hypothesen fürs nächste Mal
- **Was funktioniert:** WebSearch(Gewerk×Ort) → Impressum-Verifikation liefert saubere, compliance-konforme Daten mit sehr hohem Yield (Quelle `websearch-impressum` → Status `bewaehrt`). Impressen deutscher/österreichischer Betriebe sind zuverlässig strukturiert und gut abrufbar.
- **Engpass = MA-Zahl:** selten öffentlich → nur 9 Leads mit belegter Größe (→ Score A). Hypothese: Northdata/Firmenbuch/firmenabc.at im **Anreicherungs-Slot** gezielt nachladen hebt viele B→A. **Refresh-Aufgabe:** Northdata & Kununu waren diesmal nicht per Fetch abrufbar — Zugriffsweg (evtl. anderer Pfad/Playwright) im nächsten Lauf testen.
- **Aufhänger:** signalbasiert generiert (Wachstum/Zettel/keine-Online-Termine/Flotte/Notdienst). Hypothese: Hooks mit konkret zitiertem Signal (z. B. Zahl offener Stellen) erhöhen AE-Trefferquote — im Feedback-Loop messen.
- **Explore/Exploit ab morgen:** Ertragsdaten liegen jetzt vor → auf 0.70/0.20/0.10 umstellen. Exploit = `websearch-impressum` weiter, aber **neue Gewerke/Regionen rotieren** (heute nicht abgedeckt: Bodenleger/Parkett, Estrichleger, Fenster-/Rollladenbau, Trockenbau; Regionen: Berlin/Brandenburg, Schleswig-Holstein, Saarland, Vorarlberg, Kärnten).
- **Sättigung vermeiden:** Innungs-Mitgliederlisten (16 neue Quellen aufgenommen) als nächste Exploit-Ebene erschließen — sie liefern gezielt die kleinsten, am wenigsten digitalisierten Betriebe.

### Nachtrag 2026-07-14 — Volumen auf ≥50/Tag + HubSpot

- **Budget erhöht:** Tagesziel von 25 auf **50** (Konfig + Routine + `process_harvest --budget 50`).
- **2. Harvest-Welle** (10 neue Segmente, neue Gewerke/Regionen): +60 verifizierte Leads. Neu abgedeckt: Fenster-/Rollladenbau, Trockenbau, Bodenleger/Parkett, Estrichleger; Regionen Berlin/Brandenburg, AT-West (Sbg/Tirol/Vbg), AT-Süd (Ktn/Stmk).
- **Kombiniert: 107 verifizierte Leads** (0 Dubletten über beide Wellen — Städte/Gewerke sauber rotiert). **50 übergeben** (21 A / 29 B), **57 im Backlog**. DE 35 / AT 15 in der Übergabe; 12 Gewerke abgedeckt.
- **HubSpot-Integration gebaut:** `export_hubspot_csv.py` (Import-CSV, keine Credentials) + `hubspot_sync.py` (CRM-API-Upsert, Dedup über domain, Dry-Run-sicher). Routine erzeugt täglich die CSV und synct automatisch, sobald `HUBSPOT_TOKEN` gesetzt ist.
- **Beobachtung:** Der Yield pro Segment ist stabil ~5–6 verifizierte Leads; 16–18 Segmente/Tag reichen zuverlässig für ≥50 nach Dedup. MA-Zahl bleibt der Engpass — belegte Größe (→ Score A) korreliert stark mit Website-Teamangaben/Innungslisten. Nächster Hebel: Innungs-Mitgliederlisten als Exploit-Quelle + Northdata/firmenabc-Anreicherung.

### Quellen-Backlog (zu prüfen an Folgetagen)
- Regionale HWK-Betriebssuchen einzeln erschließen und je als eigene Quelle mit Selektoren erfassen (hwk-muenchen.de, hwk-koeln.de, hwk-stuttgart.de, …).
- Gewerkespezifische Innungs-Mitgliederlisten (oft die saubersten, kleinsten Betriebe).
- `firmen.wko.at` strukturiert je Sparte/Bundesland durchgehen (AT-Kernquelle).
- Stellenbörsen (Indeed/regionale) als Signal-Layer systematisch anbinden (Wachstums-Flag).
- Noch nicht abgedeckte Regionen für Folgeläufe: Berlin/Brandenburg, Schleswig-Holstein, Saarland (DE); Vorarlberg, Kärnten-Tiefe (AT).
- Noch nicht abgedeckte Gewerke: Bodenleger/Parkett, Estrichleger, Fenster-/Rollladenbau, reiner Trockenbau.
