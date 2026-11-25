# -*- coding: utf-8 -*-
import sys, os, csv, html, re
sys.stdout.reconfigure(encoding="utf-8")
from symbols import SYM, ORDER, TIMERS, ALARMS, CMDS, TGLS, P as PARAMS
from rungs import SECTIONS
from dsl import il_rung, svg_rung, esc

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- IL text
lines = ["(* KALBAR PDAM - PANEL MONITORING KUALITAS AIR (pH, KLORIN, TURBIDITY) *)",
         "(* PLC Schneider TM221CE24R + TM3AI4 - EcoStruxure Machine Expert Basic *)",
         "(* Program IL reversible: ketik/tempel per rung dalam mode IL, lalu ubah tampilan ke Ladder *)",
         "(* Ref: ProMinent BAMa, DULCOMETER D1Cb x3, DULCO turb C TUC 5 - lihat README *)", ""]
nr = 0
for code, title, intro, rungs in SECTIONS:
    lines += ["", f"(* ================= {code}  {title} ================= *)"]
    for r in rungs:
        nr += 1
        lines.append(f"(* Rung {nr:03d}: {r.title} *)")
        if r.comment:
            lines.append(f"(*   {r.comment} *)")
        lines += ["    " + l for l in il_rung(r)]
        lines.append("")
open(os.path.join(OUT, "KB_M221_program_IL.txt"), "w", encoding="utf-8").write("\n".join(lines))
TOTAL_RUNGS = nr

# ---------------------------------------------------------------- symbol CSV
with open(os.path.join(OUT, "KB_M221_symbols.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Address", "Symbol", "Comment"])
    for n in ORDER:
        w.writerow([SYM[n]["addr"], n, SYM[n]["comment"]])

# ---------------------------------------------------------------- HMI tag CSV
def weintek(addr):
    m = re.fullmatch(r"%M(\d+)", addr)
    if m: return "0x", m.group(1)
    m = re.fullmatch(r"%MW(\d+)", addr)
    if m: return "4x", m.group(1)
    return None, None

hmi_rows = []
for n in ORDER:
    s = SYM[n]
    if not s["hmi"]: continue
    dev, a = weintek(s["addr"])
    if dev is None: continue
    acc = {"R": "Baca", "RW": "Baca/Tulis", "CMD": "Tulis (Set ON)", "TGL": "Toggle", "ALM": "Alarm (baca)"}[s["hmi"]]
    hmi_rows.append((n, s["addr"], dev, a, acc, s["unit"], s["default"] if s["default"] is not None else "", s["comment"]))
# I/O status for HMI is read via mirrored bits? expose physical I/O through %M copy not needed: HMI reads alarm & state bits.
with open(os.path.join(OUT, "KB_HMI_tags.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Tag", "Alamat PLC", "Device type Weintek", "Alamat (zero-based)", "Akses", "Satuan", "Default", "Keterangan"])
    for r in hmi_rows: w.writerow(r)
with open(os.path.join(OUT, "KB_HMI_alarms.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["No", "Device type", "Alamat", "Kondisi", "Teks alarm", "Latch (perlu RESET)"])
    for i, (n, txt, latch) in enumerate(ALARMS):
        w.writerow([i + 1, "0x", 200 + i, "ON", txt, "Ya" if latch else "Tidak"])

# ---------------------------------------------------------------- HTML
def tbl(head, rows, cls=""):
    h = "".join(f"<th>{esc(str(x))}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'

def code(s): return f"<code>{esc(s)}</code>"

io_rows = []
for n in ORDER:
    a = SYM[n]["addr"]
    if re.match(r"%(I|Q)\d", a) or a.startswith("%IW"):
        io_rows.append((code(a), code(n), esc(SYM[n]["comment"])))
di = [r for r in io_rows if r[0].startswith("<code>%I") and not r[0].startswith("<code>%IW")]
do = [r for r in io_rows if r[0].startswith("<code>%Q")]
ai = [r for r in io_rows if r[0].startswith("<code>%IW") and not r[0].startswith("<code>%IWS")]

par_rows = [(code(f"%MW{mw}"), code(n), str(dflt), esc(u), esc(c)) for n, mw, dflt, u, c in PARAMS]
tm_rows = []
for i, (n, base, pre, c) in enumerate(TIMERS):
    tm_rows.append((code(f"%TM{i}"), code(n), "TON", base, code(SYM[pre]["addr"]) + f" ({pre})" if isinstance(pre, str) else f"<b>{pre}</b> (isi di konfigurasi)", esc(c)))
alm_rows = [(code(f"%M{200+i}"), f"0x {200+i}", code(n), esc(t), "Ya" if l else "–") for i, (n, t, l) in enumerate(ALARMS)]
cmd_rows = [(code(f"%M{m}"), f"0x {m}", code(n), "Set ON", esc(c)) for n, m, c in CMDS] + \
           [(code(f"%M{m}"), f"0x {m}", code(n), "Toggle", esc(c)) for n, m, c in TGLS]
pv_rows = []
for n in ORDER:
    s = SYM[n]
    if s["hmi"] == "R" and re.fullmatch(r"%MW\d+", s["addr"]):
        pv_rows.append((code(s["addr"]), "4x " + s["addr"][3:], code(n), esc(s["comment"])))
st_rows = []
for n in ORDER:
    s = SYM[n]
    if s["hmi"] == "R" and re.fullmatch(r"%M\d+", s["addr"]):
        st_rows.append((code(s["addr"]), "0x " + s["addr"][2:], code(n), esc(s["comment"])))
int_rows = []
for n in ORDER:
    s = SYM[n]
    if not s["hmi"] and re.fullmatch(r"%MW?\d+", s["addr"]):
        int_rows.append((code(s["addr"]), code(n), esc(s["comment"])))

prog = []
toc = []
nr = 0
for code_, title, intro, rungs in SECTIONS:
    sid = code_.lower()
    toc.append(f'<a href="#{sid}">{code_} · {esc(title)}</a>')
    items = []
    for r in rungs:
        nr += 1
        il = "\n".join(il_rung(r))
        cm = f'<p class="rc">{esc(r.comment)}</p>' if r.comment else ""
        items.append(f'''<article class="rung" id="r{nr}">
<header><span class="rn">{nr:03d}</span><h4>{esc(r.title)}</h4></header>{cm}
<div class="lad">{svg_rung(r)}</div>
<details><summary>IL</summary><pre>{esc(il)}</pre></details></article>''')
    prog.append(f'<section class="pou" id="{sid}"><h3><span class="pc">{code_}</span> {esc(title)}</h3><p class="intro">{esc(intro)}</p>{"".join(items)}</section>')

CSS = r"""
:root{
  /* Layout: single reading column (max 1180px) with section index on top; ladder rungs scroll horizontally in their own frames */
  --bg:#f2f4f3; --panel:#ffffff; --fg:#17201e; --muted:#5a6865; --line:#d3dcd9; --line2:#9fb0ab;
  --accent:#0e6d68; --accent-soft:#e1efed; --alarm:#b03a2b; --warn:#9a6a00; --cmp:#eef3f2; --op:#f5f0e4; --tm:#e8eef6;
  --f-body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#111716; --panel:#182120; --fg:#e3ebe9; --muted:#9aaba7; --line:#2b3836; --line2:#4d5f5b;
  --accent:#4fbdb4; --accent-soft:#1c3331; --alarm:#ef7a68; --warn:#e2b04a; --cmp:#1d2928; --op:#2a261c; --tm:#1d2532; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#111716; --panel:#182120; --fg:#e3ebe9; --muted:#9aaba7; --line:#2b3836; --line2:#4d5f5b;
  --accent:#4fbdb4; --accent-soft:#1c3331; --alarm:#ef7a68; --warn:#e2b04a; --cmp:#1d2928; --op:#2a261c; --tm:#1d2532; color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--f-body);font-size:15px;line-height:1.55;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 64px}
.wrap{max-width:1180px;margin:0 auto;display:grid;gap:28px}
.wrap>*{min-width:0}
h1,h2,h3,h4{text-wrap:balance;line-height:1.25;margin:0}
h1{font-size:30px;font-weight:600;letter-spacing:-.01em}
h2{font-size:21px;font-weight:600;padding-bottom:8px;border-bottom:2px solid var(--fg)}
h3{font-size:17px;font-weight:600;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
p{margin:0;max-width:75ch}
code,pre{font-family:var(--f-mono);font-size:12.5px}
.titleblock{display:grid;grid-template-columns:1fr auto;gap:18px;align-items:end;border:2px solid var(--fg);background:var(--panel);padding:18px 20px}
.titleblock .eyebrow{font-family:var(--f-mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.tb-meta{display:grid;grid-template-columns:auto auto;gap:2px 14px;font-family:var(--f-mono);font-size:12px;color:var(--muted)}
.tb-meta b{color:var(--fg);font-weight:500}
@media (max-width:700px){.titleblock{grid-template-columns:1fr}}
.toc{display:flex;flex-wrap:wrap;gap:6px}
.toc a{font-family:var(--f-mono);font-size:12px;color:var(--fg);text-decoration:none;border:1px solid var(--line2);padding:4px 9px;border-radius:3px;background:var(--panel)}
.toc a:hover,.toc a:focus-visible{border-color:var(--accent);color:var(--accent);outline:none}
section.block{display:grid;gap:14px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.grid2>*{min-width:0}
.card{background:var(--panel);border:1px solid var(--line);padding:14px 16px;display:grid;gap:8px;align-content:start}
.card h4{font-size:14px;font-weight:600}
.card ul{margin:0;padding-left:18px;display:grid;gap:4px}
.flag{border-left:4px solid var(--warn);background:var(--panel);padding:12px 16px;display:grid;gap:6px}
.flag.crit{border-left-color:var(--alarm)}
.flag b{font-weight:600}
.tw{overflow-x:auto;background:var(--panel);border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th{text-align:left;font-weight:600;font-size:11.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);background:var(--bg);border-bottom:1px solid var(--line2);padding:7px 10px;white-space:nowrap}
td{border-bottom:1px solid var(--line);padding:6px 10px;vertical-align:top}
td code{white-space:nowrap}
.pou{display:grid;gap:12px;padding-top:6px}
.pc{font-family:var(--f-mono);font-size:12px;background:var(--fg);color:var(--bg);padding:2px 7px;border-radius:2px}
.intro{color:var(--muted)}
.rung{background:var(--panel);border:1px solid var(--line);display:grid;gap:6px;padding:10px 12px}
.rung header{display:flex;gap:10px;align-items:baseline}
.rn{font-family:var(--f-mono);font-size:12px;color:var(--accent);font-weight:600}
.rung h4{font-size:14px;font-weight:500}
.rc{font-size:13px;color:var(--muted)}
.lad{overflow-x:auto}
.lad svg{display:block;max-width:none}
details summary{cursor:pointer;font-family:var(--f-mono);font-size:12px;color:var(--muted);width:max-content}
details summary:focus-visible{outline:2px solid var(--accent)}
pre{margin:6px 0 0;background:var(--bg);border:1px solid var(--line);padding:8px 10px;overflow-x:auto;line-height:1.45}
svg .w{stroke:var(--fg);stroke-width:1.3;fill:none}
svg .rail{stroke:var(--accent);stroke-width:3}
svg .k{stroke:var(--fg);stroke-width:2.2}
svg .cl{stroke:var(--accent);stroke-width:2;fill:none}
svg .cl.set{stroke:var(--warn)} svg .cl.rst{stroke:var(--alarm)}
svg text{font-family:var(--f-mono);text-anchor:middle}
svg .sy{font-size:10px;fill:var(--fg)}
svg .ad{font-size:9.5px;fill:var(--muted)}
svg .cx{font-size:10.5px;fill:var(--fg)}
svg .ct{font-size:11px;font-weight:600;fill:var(--fg)}
svg .tt{font-size:11px;font-weight:600;fill:var(--fg)}
svg .pn{font-size:9.5px;fill:var(--muted)}
svg .cb{fill:var(--cmp);stroke:var(--line2)}
svg .ob{fill:var(--op);stroke:var(--line2)}
svg .tb{fill:var(--tm);stroke:var(--line2)}
.legend{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:12.5px;color:var(--muted)}
.legend span{display:inline-flex;gap:6px;align-items:center}
.sw{width:14px;height:10px;border:1px solid var(--line2);display:inline-block}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
"""


exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_doc.py"), encoding="utf-8").read())
