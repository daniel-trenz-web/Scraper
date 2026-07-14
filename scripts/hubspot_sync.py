#!/usr/bin/env python3
"""Synchronisiert leads.jsonl als Firmen (Companies) nach HubSpot (CRM API v3).

- Dedup über die HubSpot-Standard-Eigenschaft `domain` (Suche -> Update statt Duplikat).
- SDR-Felder (Gewerk, Score, MA-Schätzung, Aufhänger, Fit-Signale, Quelle, Status)
  gehen in eigene Company-Properties (mit --create-properties einmalig anlegen).
- SICHER by default: ohne --commit nur DRY-RUN (nichts wird geschrieben).

Token: HubSpot Private-App-Token (Scopes: crm.objects.companies.read/write,
crm.schemas.companies.read/write). Übergabe via Umgebungsvariable HUBSPOT_TOKEN
oder --token.

Beispiele:
    # 1) Verbindung testen
    HUBSPOT_TOKEN=pat-xxx python3 scripts/hubspot_sync.py --check
    # 2) Eigene Properties einmalig anlegen
    HUBSPOT_TOKEN=pat-xxx python3 scripts/hubspot_sync.py --create-properties --commit
    # 3) Trockenlauf (zeigt, was gesendet würde)
    python3 scripts/hubspot_sync.py --in leads.jsonl --status uebergeben
    # 4) Wirklich syncen
    HUBSPOT_TOKEN=pat-xxx python3 scripts/hubspot_sync.py --in leads.jsonl --status uebergeben --commit
"""
import argparse, json, os, re, ssl, sys, time
import urllib.request, urllib.error

BASE = "https://api.hubapi.com"
CA = os.environ.get("SSL_CERT_FILE") or ("/root/.ccr/ca-bundle.crt" if os.path.exists("/root/.ccr/ca-bundle.crt") else None)

# Eigene Company-Properties (interner Name -> (Label, fieldType))
CUSTOM_PROPS = [
    ("hw_gewerk",        "Handwerk: Gewerk",          "text"),
    ("hw_score",         "Handwerk: Lead-Score",      "text"),
    ("hw_ma_schaetzung", "Handwerk: MA-Schätzung",    "text"),
    ("hw_ma_konfidenz",  "Handwerk: MA-Konfidenz",    "text"),
    ("hw_aufhaenger",    "Handwerk: Aufhänger",       "textarea"),
    ("hw_fit_signale",   "Handwerk: Fit-Signale",     "textarea"),
    ("hw_quelle",        "Handwerk: Quelle-URL",      "text"),
    ("hw_status",        "Handwerk: Lead-Status",     "text"),
    ("hw_bundesland",    "Handwerk: Bundesland",      "text"),
    ("hw_gefunden_am",   "Handwerk: Gefunden am",     "text"),
    ("hw_ansprechpartner","Handwerk: Ansprechpartner","text"),
]
GROUP = "sdr_handwerk"
LAND = {"DE": "Germany", "AT": "Austria"}

def http(method, path, token, body=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    ctx = ssl.create_default_context(cafile=CA) if CA else ssl.create_default_context()
    handlers = [urllib.request.HTTPSHandler(context=ctx)]
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(req, timeout=40) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else "{}"
        try:
            return e.code, json.loads(raw or "{}")
        except Exception:
            return e.code, {"raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}

def domain_of(website):
    if not website:
        return None
    d = re.sub(r"^https?://", "", website, flags=re.I)
    d = re.sub(r"^www\.", "", d, flags=re.I)
    return d.split("/")[0].strip() or None

def ma_text(ma):
    w = (ma or {}).get("wert")
    return "" if w in (None, "") else (f"~{w}" if isinstance(w, (int, float)) else str(w))

def first_url(quellen):
    for q in quellen or []:
        u = q.split(":", 1)[1] if q.startswith("harvest-") else q
        if u.startswith("http"):
            return u
    return ""

def props_for(r):
    ap = r.get("ansprechpartner") or {}
    ap_txt = ap.get("name") or ""
    if ap_txt and ap.get("rolle"):
        ap_txt = f"{ap_txt} ({ap['rolle']})"
    ma = r.get("ma_schaetzung") or {}
    desc = (f"[SDR-Lead {r.get('score','')}] {r.get('gewerk','')} · {r.get('plz','') or ''} {r.get('ort','') or ''}"
            f"{' ('+r.get('land')+')' if r.get('land') else ''}. "
            f"MA~{ma_text(ma) or '?'} (Konfidenz {ma.get('konfidenz','?')}). "
            f"Aufhänger: {r.get('aufhaenger','')}")
    p = {
        "name": r.get("firma") or "",
        "phone": r.get("telefon") or "",
        "city": r.get("ort") or "",
        "zip": r.get("plz") or "",
        "country": LAND.get(r.get("land"), r.get("land") or ""),
        "industry": "CONSTRUCTION",
        "description": desc[:65000],
        "hw_gewerk": r.get("gewerk") or "",
        "hw_score": r.get("score") or "",
        "hw_ma_schaetzung": ma_text(ma),
        "hw_ma_konfidenz": ma.get("konfidenz") or "",
        "hw_aufhaenger": r.get("aufhaenger") or "",
        "hw_fit_signale": " | ".join(r.get("fit_signale") or []),
        "hw_quelle": first_url(r.get("quellen")),
        "hw_status": r.get("status") or "",
        "hw_bundesland": r.get("bundesland") or "",
        "hw_gefunden_am": r.get("gefunden_am") or "",
        "hw_ansprechpartner": ap_txt,
    }
    dom = domain_of(r.get("website"))
    if dom:
        p["domain"] = dom
    if r.get("website"):
        p["website"] = r["website"]
    return {k: v for k, v in p.items() if v != ""}

def ensure_properties(token, commit):
    # Gruppe anlegen (409 = existiert bereits -> ok)
    st, _ = http("POST", "/crm/v3/properties/companies/groups", token,
                 {"name": GROUP, "label": "SDR Handwerk-Leads"}) if commit else (0, {})
    created = 0
    for name, label, ftype in CUSTOM_PROPS:
        st, _ = http("GET", f"/crm/v3/properties/companies/{name}", token)
        if st == 200:
            continue
        if not commit:
            print(f"  [dry-run] würde Property anlegen: {name} ({ftype})")
            created += 1
            continue
        body = {"name": name, "label": label, "type": "string", "fieldType": ftype, "groupName": GROUP}
        st, resp = http("POST", "/crm/v3/properties/companies", token, body)
        if st in (200, 201):
            created += 1
            print(f"  angelegt: {name}")
        elif st == 409:
            pass  # existiert
        else:
            print(f"  FEHLER Property {name}: {st} {resp}")
    print(f"Properties: {created} neu (bzw. würden angelegt).")

def find_company_id(token, domain):
    body = {"filterGroups": [{"filters": [{"propertyName": "domain", "operator": "EQ", "value": domain}]}],
            "properties": ["domain"], "limit": 1}
    st, resp = http("POST", "/crm/v3/objects/companies/search", token, body)
    if st == 200 and resp.get("results"):
        return resp["results"][0]["id"]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="leads.jsonl")
    ap.add_argument("--status", default="uebergeben", choices=["all", "uebergeben", "neu"])
    ap.add_argument("--date", default=None)
    ap.add_argument("--limit", type=int, default=0, help="max. Anzahl (0=alle)")
    ap.add_argument("--token", default=os.environ.get("HUBSPOT_TOKEN"))
    ap.add_argument("--commit", action="store_true", help="wirklich schreiben (sonst Dry-Run)")
    ap.add_argument("--create-properties", action="store_true", help="eigene Company-Properties anlegen")
    ap.add_argument("--check", action="store_true", help="nur Verbindung/Token testen")
    a = ap.parse_args()

    if a.check:
        if not a.token:
            sys.exit("Kein Token. Setze HUBSPOT_TOKEN oder --token.")
        st, resp = http("GET", "/crm/v3/objects/companies?limit=1", a.token)
        print("Auth OK" if st == 200 else f"Fehler {st}: {resp}")
        sys.exit(0 if st == 200 else 1)

    if a.create_properties:
        if a.commit and not a.token:
            sys.exit("Kein Token für --create-properties --commit.")
        ensure_properties(a.token, a.commit)
        if not a.commit:
            return

    leads = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    if a.status != "all":
        leads = [r for r in leads if r.get("status") == a.status]
    if a.date:
        leads = [r for r in leads if r.get("gefunden_am") == a.date]
    if a.limit:
        leads = leads[:a.limit]

    if not a.commit:
        print(f"DRY-RUN — {len(leads)} Firmen würden gesynct (kein Schreibvorgang). Erste 3 Payloads:")
        for r in leads[:3]:
            print("  •", r.get("firma"), "->", json.dumps(props_for(r), ensure_ascii=False)[:240], "…")
        print("Mit --commit (und HUBSPOT_TOKEN) tatsächlich synchronisieren.")
        return

    if not a.token:
        sys.exit("Kein Token. Setze HUBSPOT_TOKEN oder --token.")

    created = updated = failed = 0
    for i, r in enumerate(leads, 1):
        props = props_for(r)
        dom = props.get("domain")
        cid = find_company_id(a.token, dom) if dom else None
        if cid:
            st, resp = http("PATCH", f"/crm/v3/objects/companies/{cid}", a.token, {"properties": props})
            ok = st == 200
            updated += ok
        else:
            st, resp = http("POST", "/crm/v3/objects/companies", a.token, {"properties": props})
            ok = st in (200, 201)
            created += ok
        if not ok:
            failed += 1
            print(f"  FEHLER {r.get('firma')}: {st} {str(resp)[:200]}")
        if i % 8 == 0:
            time.sleep(1)  # HubSpot Rate-Limit schonen
    print(f"HubSpot-Sync fertig: {created} neu, {updated} aktualisiert, {failed} Fehler (von {len(leads)}).")

if __name__ == "__main__":
    main()
