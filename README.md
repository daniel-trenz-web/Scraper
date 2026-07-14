# Handwerk-Lead-SDR (DE + AT)

Autonomer **Small-Business SDR**: findet täglich passende **Handwerksbetriebe in Deutschland und Österreich**, qualifiziert und reichert sie an und übergibt sie dem Account Executive (AE) als kurze, faktische Firmen-Steckbriefe mit konkretem Ansprech-Aufhänger.

Der Agent hat ein **Gedächtnis über Zustandsdateien** und wird mit jedem Lauf besser (mehr Quellen, höhere Trefferqualität, weniger Dubletten).

---

## Produkt & Zielgruppe

- **Produkt:** Handwerkersoftware (Betriebsverwaltung: Angebote, Rechnungen, Zeiterfassung, Baustellendoku, Materialverwaltung)
- **Zielmärkte:** DE, AT
- **Zielgröße:** 1–25 Mitarbeiter (harte Obergrenze 25)
- **Tagesziel:** bis zu 25 qualifizierte, **neue** Leads pro Lauf
- **Ziel-Gewerke:** SHK, Elektro, Maler & Lackierer, Fliesenleger, Zimmerer/Dachdecker, Tischler/Schreiner, Bodenleger/Parkett, Trockenbau, Garten- & Landschaftsbau, Metallbau, Stuckateur, Estrichleger, Fenster-/Rollladenbau.

---

## Zustandsdateien (das Gedächtnis)

| Datei | Zweck |
|---|---|
| `sources.json` | Quellen-Registry mit Ertrags-Statistik (yield, avg_score, status) je Quelle |
| `leads.jsonl` | Alle je gefundenen Betriebe (Dedup + Historie), 1 JSON pro Zeile |
| `journal.md` | Lauftagebuch: was lief, was brach, Hypothesen, Quellen-Backlog |
| `feedback.md` | AE trägt gut/schlecht ein → Agent gewichtet Quellen neu |
| `metrics.csv` | Tageskennzahlen zur Fortschrittsmessung |
| `daily/YYYY-MM-DD.md` | Täglicher Übergabe-Report für den AE |

Schemas: siehe unten (**Daten-Schemas**).

---

## Täglicher Ablauf (Runbook)

1. **Laden** — Zustandsdateien lesen, verstehen was liefert/brach/backlog ist.
2. **Planen** — Tagesbudget nach explore/exploit/refresh aufteilen (0.70 / 0.20 / 0.10).
3. **Neue Quellen entdecken** — gezielte Suchen, systematisch durch Bundesländer × Gewerke rotieren.
4. **Ernten** — Firmen-Rohdaten aus gewählten Quellen (Fetch; Playwright für JS-lastige Seiten).
5. **Anreichern** — Firmen-Website/Impressum besuchen: Gewerk, PLZ/Ort, Kontakt, Ansprechpartner, Kaufsignale, MA-Schätzung.
6. **Qualifizieren & Scoren** — ICP-Filter, Fit-Score A–E.
7. **Deduplizieren** — gegen `leads.jsonl` (Schlüssel: Domain > Name+PLZ > Telefon).
8. **Ranken & auswählen** — Top-N nach Score.
9. **Übergeben** — `daily/YYYY-MM-DD.md` im Steckbrief-Format (optional GitHub Issue).
10. **Retro** — Quellen-Statistik & Journal aktualisieren, Feedback einarbeiten.
11. **Metriken** — Zeile an `metrics.csv` anhängen.

---

## Idealkundenprofil (ICP)

Passend, wenn: Ziel-Gewerk **und** Standort DE/AT **und** ≤25 MA **und** erreichbarer öffentlicher Kontakt.

**Kaufsignale** (erhöhen Score): veraltete Website / keine Online-Terminbuchung, aktive Stellenanzeigen, mehrere Standorte/Kolonnen/Fahrzeuge, Bewertungen zu Erreichbarkeit/Terminchaos, sichtbar Papier/Excel, inhabergeführt & lange am Markt.

**Ausschluss:** Ein-Personen-Nebengewerbe ohne Web, Konzerne/Ketten >25 MA, Betriebe ohne Kontaktweg, inaktive Firmen.

---

## Selbstverbesserung (Bandit-Logik)

- **Exploit 0.70:** ertragsstärkste Quellen ausnutzen (rotierend, nicht dieselbe täglich hämmern).
- **Explore 0.20:** neue Quellen/Regionen/Gewerke testen.
- **Refresh 0.10:** defekte Quellen neu prüfen, stale High-Value-Leads updaten.
- Pro Quelle werden `gefunden_gesamt`, `qualifiziert_gesamt`, `yield`, `avg_score`, `status` fortgeschrieben.
- `feedback.md` ist das stärkste Lernsignal → Quellen/Signale neu gewichten.

---

## Compliance (Pflicht)

- **robots.txt** respektieren; gesperrte Pfade nicht abrufen.
- **ToS** respektieren: Google Maps / LinkedIn **nicht** massen-scrapen — stattdessen Suche + Abruf einzelner öffentlicher Seiten (`zugriff: manuell`).
- **Höflich crawlen** (drosseln, sinnvoller User-Agent). Vorgehen hier: Verzeichnisse liefern nur Namen; **verifiziert wird über das öffentlich-pflichtige Impressum der Firma selbst**.
- **DSGVO/Datenminimierung:** nur öffentliche Geschäftskontaktdaten (Impressum/Verzeichniseintrag), Herkunft je Datensatz dokumentiert (Rechtsgrundlage: berechtigtes Interesse, Art. 6 Abs. 1 f).
- **⚠️ UWG §7:** Der Agent **findet und bereitet vor**. Die tatsächliche Erstansprache (E-Mail/Telefon) unterliegt strengen Regeln und ist Sache des AE/Vertriebs — vor dem Rausgehen der Leads separat sauber klären.

---

## Betrieb

Beim allerersten Lauf werden die Zustandsdateien angelegt und `sources.json` mit den Seed-Quellen (Status `unbewiesen`) befüllt; Start konservativ mit hohem Explore-Anteil, bis Ertragsdaten vorliegen.

### Pipeline-Skripte (`scripts/`)

| Skript | Zweck |
|---|---|
| `scripts/process_harvest.py` | Verarbeitet die Roh-Harvest-JSONs eines Laufs: **Dedup gegen `leads.jsonl`** (Domain > Name+PLZ > Telefon), Scoring (A–E), Aufhänger, **Backlog-Promotion**, schreibt `daily/<datum>.md`, schreibt `leads.jsonl` fort, hängt `metrics.csv`-Zeile an. |
| `scripts/md_to_pdf.py` | Rendert einen `daily/<datum>.md` nach **PDF** (headless Chromium, kein externes Paket nötig). |

**Manueller Tageslauf:**
```bash
# 1) Recherche-Agenten befüllen harvest/<datum>/harvest_<segment>.json (je Lead über Impressum verifiziert)
# 2) Verarbeiten:
python3 scripts/process_harvest.py --harvest-dir harvest/<datum> --date <datum> --repo . --sources-used 8 --new-sources 0
# 3) PDF erzeugen:
python3 scripts/md_to_pdf.py daily/<datum>.md daily/<datum>.pdf
```

Der Report wird **immer auch als PDF** unter `daily/<datum>.pdf` ausgegeben und dem AE geliefert.

### Tägliche Routine

Eine **Routine** (scheduled trigger) startet täglich eine frische Session, die den kompletten Runbook-Lauf ausführt (Harvest → Verarbeiten → PDF → commit/push) und den neuen Report als PDF liefert. Läuft auf Branch `claude/handwerk-lead-sdr-4hrxjs`. Zeitpunkt/Änderung siehe Routine-Einstellungen.

> Alternativ: GitHub-Actions-Daily-Cron, der dieselben Skripte ausführt und den Zustand zurück-committet.

---

## Daten-Schemas

**`sources.json`** — Array von Quellen-Objekten mit `id, name, url, typ, land, gewerke, robots_ok, zugriff, status, letzter_lauf, gefunden_gesamt, qualifiziert_gesamt, yield, avg_score, extraktion, entdeckt_am, entdeckt_via`.

**`leads.jsonl`** — 1 Objekt pro Zeile:
```json
{"id":"<hash: domain | name+plz>","firma":"","gewerk":"","plz":"","ort":"","bundesland":"","land":"DE",
 "website":"","telefon":null,"email":null,"ansprechpartner":{"name":null,"rolle":null},
 "ma_schaetzung":{"wert":null,"konfidenz":"niedrig","quelle":null},
 "kanaele":{"instagram":null,"facebook":null,"linkedin":null},
 "fit_signale":[],"aufhaenger":"","score":"","quellen":["quelle-id:https://..."],
 "status":"neu","gefunden_am":"","zuletzt_gesehen":""}
```

`status`-Werte eines Leads: `neu` → `uebergeben` (in einem Tagesreport ausgeliefert).
`status`-Werte einer Quelle: `unbewiesen` → `bewaehrt` / `defekt` / `ausgeschoepft` / `deaktiviert`.
