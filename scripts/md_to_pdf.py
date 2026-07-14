#!/usr/bin/env python3
"""Rendert einen Lead-Report (Markdown) nach PDF via headless Chromium.

Nutzung:
    python3 scripts/md_to_pdf.py daily/2026-07-14.md [ausgabe.pdf]

Kein externes Python-Paket noetig. Markdown->HTML deckt genau die im Report
verwendeten Konstrukte ab (H1-H4, **fett**, *kursiv*, `code`, Listen, Tabellen,
Blockquote, ---). HTML->PDF via im Image vorinstalliertem Chromium (--print-to-pdf).
"""
import sys, os, re, html, subprocess, glob, tempfile

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
]

def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c):
            return c
    hits = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
    if hits:
        return sorted(hits)[-1]
    hits = glob.glob("/opt/pw-browsers/chromium*headless*/chrome-linux/headless_shell")
    if hits:
        return sorted(hits)[-1]
    raise SystemExit("Kein Chromium in /opt/pw-browsers gefunden.")

def inline(t):
    """Inline-Formatierung auf bereits HTML-escaptem Text."""
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\*\w])\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    # nackte URLs klickbar machen
    t = re.sub(r"(?<![\"=>])(https?://[^\s<)]+)", r'<a href="\1">\1</a>', t)
    return t

def esc(s):
    return html.escape(s, quote=False)

def md_to_html_body(md):
    lines = md.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        # Tabelle
        if line.strip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i+1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(esc(h))}</th>" for h in header) + "</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{inline(esc(c))}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            continue
        # Ueberschriften
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(esc(m.group(2)))}</h{lvl}>")
            i += 1
            continue
        # HR
        if re.match(r"^---+\s*$", line):
            out.append("<hr>")
            i += 1
            continue
        # Blockquote (ggf. mehrzeilig)
        if line.strip().startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote>{inline(esc(' '.join(buf)))}</blockquote>")
            continue
        # Liste
        if re.match(r"^\s*[-*]\s+", line):
            out.append("<ul>")
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                item = re.sub(r"^\s*[-*]\s+", "", lines[i])
                out.append(f"<li>{inline(esc(item))}</li>")
                i += 1
            out.append("</ul>")
            continue
        # Leerzeile
        if not line.strip():
            i += 1
            continue
        # Absatz
        buf = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|>|\s*[-*]\s|\|)", lines[i]) and not re.match(r"^---+\s*$", lines[i]):
            buf.append(lines[i])
            i += 1
        out.append(f"<p>{inline(esc(' '.join(buf)))}</p>")
    return "\n".join(out)

CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 10.5px; line-height: 1.5; color: #1f2933; margin: 0; }
h1 { font-size: 21px; margin: 0 0 6px; color: #0b3d2e; border-bottom: 3px solid #0b3d2e; padding-bottom: 6px; }
h2 { font-size: 15px; margin: 20px 0 8px; color: #0b3d2e; }
h3 { font-size: 12.5px; margin: 16px 0 6px; color: #33691e; letter-spacing: .3px; }
h4 { font-size: 11.5px; margin: 12px 0 3px; color: #102a43; break-after: avoid; }
h4 + p, h4 + p + ul { break-before: avoid; }
p { margin: 4px 0; }
ul { margin: 3px 0 8px; padding-left: 16px; }
li { margin: 1px 0; }
strong { color: #102a43; }
code { background: #eef2f5; padding: 0 3px; border-radius: 3px; font-size: 9.5px;
  font-family: "SFMono-Regular", Consolas, monospace; }
a { color: #2166a5; text-decoration: none; word-break: break-all; }
hr { border: 0; border-top: 1px solid #d9e2ec; margin: 14px 0; }
blockquote { margin: 10px 0; padding: 8px 12px; background: #fff8e1; border-left: 4px solid #f5a623;
  font-size: 10px; border-radius: 0 4px 4px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8.8px; }
th { background: #0b3d2e; color: #fff; text-align: left; padding: 4px 6px; }
td { border-bottom: 1px solid #e3e8ee; padding: 3px 6px; vertical-align: top; word-break: break-word; }
tr:nth-child(even) td { background: #f7f9fb; }
/* Steckbrief (h4 + folgender Block) zusammenhalten */
h4 { page-break-inside: avoid; }
"""

def build_html(md, title):
    body = md_to_html_body(md)
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<title>{esc(title)}</title><style>{CSS}</style></head><body>{body}</body></html>"""

def main():
    if len(sys.argv) < 2:
        raise SystemExit("Nutzung: md_to_pdf.py <report.md> [ausgabe.pdf]")
    md_path = sys.argv[1]
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(md_path)[0] + ".pdf"
    with open(md_path, encoding="utf-8") as fh:
        md = fh.read()
    title = os.path.splitext(os.path.basename(md_path))[0]
    htmldoc = build_html(md, f"Lead-Report {title}")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
        tf.write(htmldoc)
        html_path = tf.name
    chrome = find_chrome()
    cmd = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
           "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", "file://" + html_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        # aeltere Chromium-Flags als Fallback
        cmd2 = [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--print-to-pdf-no-header",
                f"--print-to-pdf={pdf_path}", "file://" + html_path]
        r = subprocess.run(cmd2, capture_output=True, text=True)
    os.unlink(html_path)
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        sys.stderr.write(r.stdout + "\n" + r.stderr + "\n")
        raise SystemExit("PDF-Erzeugung fehlgeschlagen.")
    print(f"PDF: {pdf_path} ({os.path.getsize(pdf_path)//1024} KB)")

if __name__ == "__main__":
    main()
