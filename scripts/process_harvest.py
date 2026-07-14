#!/usr/bin/env python3
"""Verarbeitet die Roh-Harvest-JSONs eines Laufs zu Report + Zustandsdateien.

Ablauf: Dedup gegen leads.jsonl (Historie) -> Scoring (A-E) -> Aufhaenger ->
Ranking (heutige Neue + Backlog status=neu) -> Top-N uebergeben ->
daily/<date>.md schreiben, leads.jsonl fortschreiben, metrics.csv-Zeile anhaengen.

Nutzung:
    python3 scripts/process_harvest.py --harvest-dir <dir> --date YYYY-MM-DD \
        [--budget 25] [--repo .] [--sources-used N] [--new-sources N]

<dir> enthaelt die Roh-Ausgaben der Recherche-Agenten als harvest_*.json
(Schema: {"segment": "...", "leads": [ {firma,gewerk,plz,ort,bundesland,land,
website,telefon,email,ansprechpartner,ma_schaetzung,kanaele,fit_signale,
quellen,verifikation,evtl_ueber_25}, ... ]}).
"""
import argparse, json, os, re, glob, hashlib
from collections import Counter

# ---------------- Normalisierung / Dedup ----------------
def norm_domain(url):
    if not url:
        return None
    d = re.sub(r"^https?://", "", url.strip(), flags=re.I)
    d = re.sub(r"^www\.", "", d, flags=re.I)
    d = d.split("/")[0].lower().strip()
    return d or None

def norm_name(name):
    n = (name or "").lower()
    for suf in [" gmbh & co. kg", " gmbh", " e.k.", " e. k.", " e.u.", " e.u", " gbr",
                " kg", " ohg", " ges.m.b.h.", " ges.m.b.h", " m.b.h.", " ug"]:
        n = n.replace(suf, " ")
    n = re.sub(r"\(.*?\)", " ", n)
    n = re.sub(r"[^a-z0-9äöüß ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()

def keys_for(lead):
    dom = norm_domain(lead.get("website"))
    npz = norm_name(lead.get("firma")) + "|" + (lead.get("plz") or "")
    tel = re.sub(r"\D", "", lead.get("telefon") or "")
    return dom, npz, (tel or None)

# ---------------- Scoring ----------------
STRONG = {
    "wachstum": ["offene stelle", "stellenanz", "jobs", "bilden aus", "bildet aus", "ausbildungsbetrieb", "karriereseite", "wachstum", "personalbedarf", "personaldruck", "lehrling", "sucht", "stellenaus"],
    "veraltet": ["veraltet", "veraltete", "statisch", ".htm", ".php", "schlicht", "einfache website", "wordpress-standard", "baukasten", "layout"],
    "keine_termin": ["keine online-termin", "kein online-termin", "kein echtes online", "keine echte online", "nur kontaktformular", "nur telefon", "nur anfrageformul", "terminvereinbarung nur", "online anfrage"],
    "flotte": ["mehrere standorte", "mehrere kolonnen", "mehrere fahrzeuge", "fuhrpark", "eigene monteure", "mehrere einsatz", "kolonnen"],
    "zettel": ["gmail", "t-online", "web.de", "@speed.at", "isp-email", "isp-mail", "papier", "excel", "zettelwirtschaft", "manuell", "rudimentaer", "handschriftlich"],
    "notdienst": ["notdienst", "havarie", "24-stunden", "24/7", "24 stunden", "stoerungsdienst"],
}
def strong_hits(sig, verif):
    text = " ".join(sig or []).lower() + " " + (verif or "").lower()
    return {c for c, kws in STRONG.items() if any(k in text for k in kws)}

def score_num(lead):
    has = lambda k: bool(lead.get(k))
    reach = sum([has("website"), has("telefon"), has("email")])
    pts = reach + min(len(lead.get("fit_signale") or []), 4)
    ma = lead.get("ma_schaetzung") or {}
    wert, konf = ma.get("wert"), (ma.get("konfidenz") or "").lower()
    if lead.get("evtl_ueber_25"):
        pts -= 2
    elif wert not in (None, "") and konf in ("mittel", "hoch"):
        pts += 2
    elif wert not in (None, ""):
        pts += 1
    if (lead.get("ansprechpartner") or {}).get("name"):
        pts += 1
    cats = strong_hits(lead.get("fit_signale"), lead.get("verifikation"))
    pts += min(len(cats), 3)
    return pts, reach, cats

_ORD = ["E", "D", "C", "B", "A"]
def _cap(l, ceil):
    return _ORD[min(_ORD.index(l), _ORD.index(ceil))]
def letter_for(pts, lead):
    base = "A" if pts >= 11 else "B" if pts >= 9 else "C" if pts >= 7 else "D" if pts >= 5 else "E"
    ma = lead.get("ma_schaetzung") or {}
    wert, konf = ma.get("wert"), (ma.get("konfidenz") or "").lower()
    if lead.get("evtl_ueber_25"):
        return _cap(base, "D")
    if wert in (None, "") or konf == "niedrig":
        return _cap(base, "B")
    return base

def gshort(g):
    g = (g or "").lower()
    if "shk" in g: return "SHK/Installation"
    if "elektro" in g: return "Elektro"
    if "sanit" in g or "heizung" in g or "installat" in g or "klima" in g or "spengler" in g: return "SHK/Installation"
    if "maler" in g or "lackier" in g or "stuck" in g: return "Maler/Stuck."
    if "fliesen" in g: return "Fliesenleger"
    if "tischler" in g or "schreiner" in g or "moebel" in g: return "Tischler"
    if "dach" in g or "zimmer" in g or "holzbau" in g: return "Dach/Zimmerer"
    if "galabau" in g or "garten" in g or "landschaft" in g: return "GaLaBau"
    if "metall" in g or "schlosser" in g: return "Metallbau"
    return g or "?"

def aufhaenger(lead, cats):
    g = gshort(lead.get("gewerk"))
    if "wachstum" in cats:
        return ("Ihr Betrieb wächst und Sie stellen aktiv ein – sobald mehr Kolonnen unterwegs sind, wird "
                "Einsatzplanung, Zeiterfassung und Baustellendoku schnell zum Nadelöhr. Genau dafür bündelt "
                "unsere Handwerkersoftware Angebote, Zeiten und Doku an einem Ort.")
    if "zettel" in cats:
        return ("Vieles läuft bei Ihnen offenbar noch über Telefon, Zettel und private Mailadresse – mit digitalen "
                "Angeboten, Rechnungen und Baustellendoku sparen Sie im Büro pro Woche spürbar Zeit, ohne Ihre "
                "gewohnte Arbeitsweise umzukrempeln.")
    if "keine_termin" in cats or "veraltet" in cats:
        return (f"Anfragen erreichen Sie aktuell nur per Telefon/Formular – mit digitaler Angebots- und "
                f"Rechnungserstellung plus mobiler Baustellendoku verlieren Sie im Tagesgeschäft weniger Zeit und "
                f"wirken für {g}-Kunden moderner.")
    if "flotte" in cats:
        return ("Mit mehreren Fahrzeugen/Kolonnen im Einsatz ist die Koordination der größte Hebel – unsere Software "
                "zeigt Ihnen Zeiten, Material und Baustellenstatus in Echtzeit an einem Ort.")
    if "notdienst" in cats:
        return ("Bei Notdienst/24h-Erreichbarkeit zählt jede Minute in der Disposition – mit mobiler Auftrags- und "
                "Zeiterfassung landen Einsätze sauber dokumentiert direkt in der Abrechnung.")
    return (f"Als inhabergeführter {g}-Betrieb jonglieren Sie Angebote, Baustellendoku und Rechnungen oft parallel – "
            f"unsere Handwerkersoftware bündelt das an einem Ort und spart Ihnen Büro-Zeit für die Baustelle.")

# ---------------- Report-Helfer ----------------
def ma_str(ma):
    w = (ma or {}).get("wert")
    base = "unbekannt" if w in (None, "") else (f"~{w}" if isinstance(w, (int, float)) else str(w).replace("-", "–"))
    return f"{base} MA (Quelle: {(ma or {}).get('quelle') or 'n/a'}; Konfidenz: {(ma or {}).get('konfidenz') or 'niedrig'})"
def ap_str(ap):
    ap = ap or {}; n, r = ap.get("name"), ap.get("rolle")
    return f"{n} ({r})" if n and r else (n or (f"— ({r})" if r else "nicht öffentlich genannt"))
def kan_str(k):
    k = k or {}; p = [x for x in ("instagram", "facebook", "linkedin") if k.get(x)]
    return ", ".join(s.capitalize() for s in p) if p else "keine öffentlichen Social-Kanäle gefunden"
def urls_of(quellen):
    return [q.split(":", 1)[1] if q.startswith("harvest-") else q for q in (quellen or [])]
def loc(r):
    bl = r.get("bundesland") or ""
    suffix = " (AT)" if r.get("land") == "AT" else ""
    return f"{r.get('plz') or ''} {r.get('ort') or ''}, {bl}{suffix}".strip()

# ---------------- Hauptlogik ----------------
def load_jsonl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--harvest-dir", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--budget", type=int, default=25)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--sources-used", type=int, default=0)
    ap.add_argument("--new-sources", type=int, default=0)
    a = ap.parse_args()
    REPO, DATE, BUDGET = a.repo, a.date, a.budget

    leads_path = os.path.join(REPO, "leads.jsonl")
    hist = load_jsonl(leads_path)
    idx_dom, idx_npz, idx_tel = {}, {}, {}
    for r in hist:
        d, npz, tel = keys_for(r)
        if d: idx_dom[d] = r
        idx_npz[npz] = r
        if tel: idx_tel[tel] = r

    raw = []
    for f in sorted(glob.glob(os.path.join(a.harvest_dir, "harvest_*.json"))):
        seg = json.load(open(f, encoding="utf-8"))
        for L in seg.get("leads", []):
            L["segment"] = seg.get("segment", os.path.basename(f))
            raw.append(L)

    new_records, dupes = [], 0
    for L in raw:
        d, npz, tel = keys_for(L)
        match = (idx_dom.get(d) if d else None) or idx_npz.get(npz) or (idx_tel.get(tel) if tel else None)
        if match:
            match["zuletzt_gesehen"] = DATE
            dupes += 1
            continue
        pts, reach, cats = score_num(L)
        lid = d or ("n-" + hashlib.md5(npz.encode()).hexdigest()[:10])
        rec = {
            "id": lid, "firma": L.get("firma"), "gewerk": L.get("gewerk"),
            "plz": L.get("plz"), "ort": L.get("ort"), "bundesland": L.get("bundesland"), "land": L.get("land"),
            "website": L.get("website"), "telefon": L.get("telefon"), "email": L.get("email"),
            "ansprechpartner": L.get("ansprechpartner") or {"name": None, "rolle": None},
            "ma_schaetzung": L.get("ma_schaetzung") or {"wert": None, "konfidenz": "niedrig", "quelle": None},
            "kanaele": L.get("kanaele") or {"instagram": None, "facebook": None, "linkedin": None},
            "fit_signale": L.get("fit_signale") or [],
            "aufhaenger": aufhaenger(L, cats), "score": letter_for(pts, L),
            "evtl_ueber_25": L.get("evtl_ueber_25", False),
            "quellen": [f"harvest-{DATE}:{u}" for u in (L.get("quellen") or [])],
            "verifikation": L.get("verifikation"), "segment": L.get("segment"),
            "status": "neu", "gefunden_am": DATE, "zuletzt_gesehen": DATE,
        }
        new_records.append(rec)
        if d: idx_dom[d] = rec
        idx_npz[npz] = rec
        if tel: idx_tel[tel] = rec

    all_records = hist + new_records

    # Kandidatenpool: alles status=neu (heutige Neue + Backlog frueherer Tage)
    def rank_key(r):
        pts, reach, _ = score_num(r)
        so = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}[r.get("score", "E")]
        return (so, pts, reach)
    candidates = [r for r in all_records if r.get("status") == "neu"]
    candidates.sort(key=rank_key, reverse=True)
    delivered = candidates[:BUDGET]
    backlog = candidates[BUDGET:]
    for r in delivered:
        r["status"] = "uebergeben"
        r["uebergeben_am"] = DATE

    # leads.jsonl fortschreiben (Historie zuerst, dann Neue)
    with open(leads_path, "w", encoding="utf-8") as fh:
        for r in all_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- Report ----
    dist = Counter(r["score"] for r in candidates)
    land = Counter(r["land"] for r in delivered)
    so = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
    avg = (sum(so[r["score"]] for r in delivered) / len(delivered)) if delivered else 0
    md = []
    md.append(f"# Lead-Report {DATE}")
    md.append("")
    md.append(f"**Neu gefunden heute: {len(new_records)} · Dubletten übersprungen: {dupes} · "
              f"Neu übergeben: {len(delivered)} · In Reserve (Backlog): {len(backlog)} · "
              f"Leads gesamt in Historie: {len(all_records)}**")
    md.append("")
    md.append(f"**Score-Verteilung (Übergabe):** " + " · ".join(f"{k}={Counter(r['score'] for r in delivered).get(k,0)}" for k in ['A','B','C','D','E'])
              + f"  ·  **Länder:** DE={land.get('DE',0)}, AT={land.get('AT',0)}  ·  **Ø-Score (1–5):** {avg:.2f}")
    md.append("")
    md.append("> ⚠️ **Vor Erstansprache (UWG §7 / DSGVO):** Diese Leads sind **recherchiert und aufbereitet**, "
              "nicht kontaktiert. Kalte E-Mail/Telefon-Ansprache unterliegt in DE/AT strengen Regeln "
              "(mutmaßliche Einwilligung). Ansprachekanal & Rechtsgrundlage bitte separat klären. Alle "
              "Kontaktdaten stammen aus öffentlichen Impressen (berechtigtes Interesse, Art. 6 Abs. 1 f DSGVO).")
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"## Übergabe — Top {len(delivered)} (nach Score)")
    md.append("")
    cur = None
    for i, r in enumerate(delivered, 1):
        if r["score"] != cur:
            cur = r["score"]; md.append(f"### ▊ Score {cur}"); md.append("")
        u = urls_of(r.get("quellen"))
        flag = "  ⚠️ *evtl. >25 MA — Größe vor Ansprache prüfen*" if r.get("evtl_ueber_25") else ""
        extra = (f" · (+{len(u)-1} weitere belegte URL{'s' if len(u)-1>1 else ''})" if len(u) > 1 else "")
        md.append(f"#### {i}. {r['firma']} — {r['gewerk']}")
        md.append(f"*{loc(r)} · Score: **{r['score']}***{flag}")
        md.append("")
        md.append(f"- **MA (geschätzt):** {ma_str(r['ma_schaetzung'])}")
        md.append(f"- **Web:** {r.get('website') or '—'}  ·  **Tel:** {r.get('telefon') or '—'}  ·  **Mail:** {r.get('email') or '—'}")
        md.append(f"- **Ansprechpartner:** {ap_str(r.get('ansprechpartner'))}")
        md.append(f"- **Kanäle:** {kan_str(r.get('kanaele'))}")
        md.append(f"- **Fit-Signale:** {'; '.join((r.get('fit_signale') or [])[:3]) or '—'}")
        md.append(f"- **Aufhänger Erstansprache:** „{r['aufhaenger']}“")
        md.append(f"- **Quelle(n):** {u[0] if u else '—'}{extra} · Gefunden: {r.get('gefunden_am')}")
        md.append("")
    md.append("---")
    md.append("")
    md.append(f"## Backlog / Reserve — {len(backlog)} weitere qualifizierte Leads")
    md.append("")
    md.append("Bereits verifiziert und in `leads.jsonl` gebankt (Status `neu`). Füllen den nächsten Lauf ohne erneute Recherche.")
    md.append("")
    if backlog:
        md.append("| # | Firma | Gewerk | Ort | Land | Score | Web | Tel |")
        md.append("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(backlog, len(delivered) + 1):
            md.append(f"| {i} | {r['firma']} | {gshort(r['gewerk'])} | {r.get('ort') or ''} | {r['land']} | {r['score']} | {r.get('website') or '—'} | {r.get('telefon') or '—'} |")
    else:
        md.append("_Kein Backlog — alle qualifizierten Leads wurden übergeben._")
    md.append("")

    daily_path = os.path.join(REPO, "daily", f"{DATE}.md")
    os.makedirs(os.path.dirname(daily_path), exist_ok=True)
    open(daily_path, "w", encoding="utf-8").write("\n".join(md) + "\n")

    # ---- metrics.csv ----
    mrow = (f"{DATE},{a.sources_used},{a.new_sources},{len(raw)},{len(raw)},{len(new_records)+dupes},"
            f"{len(delivered)},{dupes},{avg:.2f},websearch-impressum,"
            f"Neu {len(new_records)} / Backlog {len(backlog)} / Historie {len(all_records)}\n")
    metrics_path = os.path.join(REPO, "metrics.csv")
    if not os.path.exists(metrics_path):
        open(metrics_path, "w").write("datum,quellen_genutzt,neue_quellen,roh_kandidaten,angereichert,qualifiziert,uebergeben,dubletten,avg_score,top_quelle,notiz\n")
    open(metrics_path, "a", encoding="utf-8").write(mrow)

    print(f"Roh: {len(raw)} · Neu: {len(new_records)} · Dubletten: {dupes} · "
          f"Übergeben: {len(delivered)} · Backlog: {len(backlog)} · Historie: {len(all_records)}")
    print(f"Report: {daily_path}")

if __name__ == "__main__":
    main()
