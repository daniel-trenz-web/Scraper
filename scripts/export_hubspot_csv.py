#!/usr/bin/env python3
"""Exportiert leads.jsonl als HubSpot-Import-CSV (Objekt: Firmen/Companies).

Kein Token / keine Netzverbindung nötig — die CSV wird in HubSpot manuell importiert
(Import > Firmen). Standard-Spalten (Company name, Domain, Phone, City, Postal Code,
Country) werden von HubSpot automatisch erkannt; die SDR-Spalten (Gewerk, Lead Score,
MA-Schätzung, Aufhänger, …) mappt man beim Import auf (eigene) Eigenschaften.

Nutzung:
    python3 scripts/export_hubspot_csv.py [--in leads.jsonl] [--out daily/<datum>_hubspot.csv]
                                          [--status uebergeben|neu|all] [--date YYYY-MM-DD]
"""
import argparse, csv, json, os

LAND = {"DE": "Germany", "AT": "Austria"}

def ma_text(ma):
    ma = ma or {}
    w = ma.get("wert")
    if w in (None, ""):
        return ""
    return f"~{w}" if isinstance(w, (int, float)) else str(w)

def first_url(quellen):
    for q in quellen or []:
        u = q.split(":", 1)[1] if q.startswith("harvest-") else q
        if u.startswith("http"):
            return u
    return ""

COLUMNS = [
    "Company name", "Company Domain Name", "Website URL", "Phone Number",
    "City", "State/Region", "Postal Code", "Country",
    "Industry", "Gewerk", "Lead Score", "MA-Schaetzung", "MA-Konfidenz",
    "Ansprechpartner", "Aufhaenger", "Fit-Signale", "Quelle-URL",
    "Lead-Status", "Gefunden am", "Land-Code",
]

def domain_of(website):
    if not website:
        return ""
    import re
    d = re.sub(r"^https?://", "", website, flags=re.I)
    d = re.sub(r"^www\.", "", d, flags=re.I)
    return d.split("/")[0].strip()

def row_for(r):
    ma = r.get("ma_schaetzung") or {}
    ap = r.get("ansprechpartner") or {}
    ap_txt = ap.get("name") or ""
    if ap_txt and ap.get("rolle"):
        ap_txt = f"{ap_txt} ({ap['rolle']})"
    return {
        "Company name": r.get("firma", ""),
        "Company Domain Name": domain_of(r.get("website")),
        "Website URL": r.get("website") or "",
        "Phone Number": r.get("telefon") or "",
        "City": r.get("ort") or "",
        "State/Region": r.get("bundesland") or "",
        "Postal Code": r.get("plz") or "",
        "Country": LAND.get(r.get("land"), r.get("land") or ""),
        "Industry": "Construction",
        "Gewerk": r.get("gewerk") or "",
        "Lead Score": r.get("score") or "",
        "MA-Schaetzung": ma_text(ma),
        "MA-Konfidenz": ma.get("konfidenz") or "",
        "Ansprechpartner": ap_txt,
        "Aufhaenger": r.get("aufhaenger") or "",
        "Fit-Signale": " | ".join(r.get("fit_signale") or []),
        "Quelle-URL": first_url(r.get("quellen")),
        "Lead-Status": r.get("status") or "",
        "Gefunden am": r.get("gefunden_am") or "",
        "Land-Code": r.get("land") or "",
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="leads.jsonl")
    ap.add_argument("--out", default=None)
    ap.add_argument("--status", default="all", choices=["all", "uebergeben", "neu"])
    ap.add_argument("--date", default=None, help="nur Leads mit gefunden_am == DATE")
    a = ap.parse_args()

    leads = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    if a.status != "all":
        leads = [r for r in leads if r.get("status") == a.status]
    if a.date:
        leads = [r for r in leads if r.get("gefunden_am") == a.date]

    out = a.out or (f"daily/{a.date}_hubspot.csv" if a.date else "leads_hubspot.csv")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    # utf-8-sig -> BOM, damit Excel/HubSpot Umlaute korrekt lesen
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in leads:
            w.writerow(row_for(r))
    print(f"HubSpot-CSV: {out} ({len(leads)} Firmen)")

if __name__ == "__main__":
    main()
