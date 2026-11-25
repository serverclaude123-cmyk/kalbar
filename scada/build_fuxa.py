# -*- coding: utf-8 -*-
"""Generate FUXA SCADA project for KALBAR PDAM water-quality panel.

Reads the PLC symbol table (../plc/generator/symbols.py) so every Modbus address
matches the M221 program. Output: KB_FUXA_project.json (import in FUXA editor:
Menu > Open Project).

M221 Modbus TCP server: %Mn -> coil n (FUXA memaddress 000000, address n+1)
                         %MWn -> holding register n (FUXA 400000, address n+1)
"""
import sys, os, json, hashlib, re, html

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "plc", "generator"))
from symbols import SYM, ORDER, ALARMS, P as PARAMS, DI_NAMES, DO_NAMES  # noqa: E402

PLC_IP = os.environ.get("KB_PLC_IP", "192.168.1.10")
PLC_PORT = os.environ.get("KB_PLC_PORT", "502")
DEV_NAME = "PLC_M221"
DEV_ID = "d_kalbar_m221"

def uid(prefix, key):
    return prefix + "_" + hashlib.md5(key.encode()).hexdigest()[:12]

def esc(s):
    return html.escape(str(s), quote=True)

# ------------------------------------------------------------------ tags
TAGS = {}       # symbol -> tag dict
SCALE = {}      # symbol -> (divisor, digits, unit)

def scale_of(unit):
    u = unit or ""
    if u.startswith("x0,01"):
        return 100, 2, u.replace("x0,01", "").strip()
    if u.startswith("x0,1"):
        return 10, 1, u.replace("x0,1", "").strip()
    return 1, 0, u

def add_tag(sym, daq=False, divisor=None, digits=None, unit=None):
    s = SYM[sym]
    a = s["addr"]
    m = re.fullmatch(r"%M(\d+)", a)
    if m:
        mem, adr, typ = "000000", int(m.group(1)) + 1, "Bool"
    else:
        m = re.fullmatch(r"%MW(\d+)", a)
        assert m, (sym, a)
        mem, adr, typ = "400000", int(m.group(1)) + 1, "Int16"
    d0, g0, u0 = scale_of(s.get("unit"))
    div = divisor if divisor is not None else d0
    dig = digits if digits is not None else g0
    tid = uid("t", sym)
    TAGS[sym] = {
        "id": tid, "name": sym, "label": sym, "type": typ,
        "memaddress": mem, "address": str(adr),
        "divisor": div, "format": dig if typ != "Bool" else None,
        "daq": {"enabled": daq, "interval": 60, "changed": True, "restored": False},
        "init": "", "description": f"{a} - {s['comment']}",
    }
    SCALE[sym] = (div, dig, unit if unit is not None else u0)
    return tid

PV = [("PH1_PV", "pH #1", "pH", 2), ("PH2_PV", "pH #2", "pH", 2),
      ("CL_PV", "Sisa klor bebas", "mg/L", 2), ("TU_PV", "Turbidity", "NTU", 2)]
for sym, _, unit, dg in PV:
    add_tag(sym, daq=True, divisor=100, digits=dg, unit=unit)
for sym in ["TU_MA_PV", "TU_MB_PV", "PH_DIFF"]:
    add_tag(sym, divisor=100, digits=2)
for sym in ["TU_STATUS", "TU_ERRW", "MB_ERR_TU", "PH1_ZONE", "PH2_ZONE", "CL_ZONE", "TU_ZONE"]:
    add_tag(sym, divisor=1, digits=0)
for name, mw, dflt, unit, cmt in PARAMS:
    add_tag(name)
for n in ORDER:
    s = SYM[n]
    if re.fullmatch(r"%M\d+", s["addr"]) and s["hmi"] in ("R", "ALM", "CMD", "TGL"):
        add_tag(n, daq=(s["hmi"] == "ALM"))

def T(sym):
    return TAGS[sym]["id"]

device = {
    "id": DEV_ID, "name": DEV_NAME, "enabled": True, "type": "ModbusTCP", "polling": 1000,
    # FUXA Modbus TCP: port diambil dari "ip:port" di address (default 502)
    "property": {"address": PLC_IP if PLC_PORT == "502" else f"{PLC_IP}:{PLC_PORT}", "port": PLC_PORT,
                 "slaveid": "1", "connectionOption": "TcpPort",
                 "delay": 10, "forceFC16": False},
    "tags": {t["id"]: t for t in TAGS.values()},
}

# ------------------------------------------------------------------ SVG helpers
C_BG, C_CARD, C_LINE, C_TXT, C_MUTED = "#eef2f4", "#ffffff", "#c9d3d8", "#1b2a33", "#5d6d75"
C_HEAD, C_OK, C_ALM, C_WARN, C_OFF, C_ACC = "#123a4f", "#2e9e4f", "#d93a2b", "#f0a500", "#b7c0c4", "#1d6f9a"

class View:
    def __init__(self, vid, name, w=1280, h=760):
        self.id, self.name, self.w, self.h = vid, name, w, h
        self.svg, self.items, self.n = [], {}, 0

    def _id(self, p):
        self.n += 1
        return uid(p, f"{self.id}-{self.n}")

    def rect(self, x, y, w, h, fill=C_CARD, stroke=C_LINE, rx=6, sw=1):
        self.svg.append(f'<rect id="{self._id("svg")}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def text(self, x, y, s, size=14, fill=C_TXT, anchor="start", weight="normal"):
        self.svg.append(f'<text id="{self._id("svg")}" x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" '
                        f'font-weight="{weight}" fill="{fill}" stroke-width="0" text-anchor="{anchor}" '
                        f'xml:space="preserve">{esc(s)}</text>')

    def value(self, x, y, sym, size=16, anchor="middle", fill=C_TXT, unit=None, digits=None, name=None):
        gid, tid = self._id("VAL"), self._id("VAL")
        self.svg.append(
            f'<g id="{gid}" type="svg-ext-value" fill="{fill}" stroke="{fill}" font-size="{size}" stroke-width="0" '
            f'font-family="sans-serif" text-anchor="{anchor}"><text id="{tid}" x="{x}" y="{y}" fill="{fill}" '
            f'stroke="{fill}" stroke-width="0" font-size="{size}" font-family="sans-serif" font-weight="bold" '
            f'text-anchor="{anchor}" xml:space="preserve">##.##</text></g>')
        div, dg, un = SCALE[sym]
        rng = {"type": "output", "min": 0, "max": 0, "text": unit if unit is not None else un, "textId": None,
               "fractionDigits": digits if digits is not None else dg}
        self.items[gid] = {"id": gid, "type": "svg-ext-value", "name": name or sym, "label": "Value",
                           "property": {"variableId": T(sym), "variableSrc": DEV_NAME, "events": [], "actions": [],
                                        "ranges": [rng]}}

    def lamp(self, cx, cy, sym, on=C_OK, off=C_OFF, r=11, name=None, onval=None):
        """Semaphore. onval=None: bit 0/1. onval=k: lit when word == k (other values = off)."""
        gid, eid = self._id("GSE"), self._id("GSE")
        self.svg.append(f'<g id="{gid}" type="svg-ext-gauge_semaphore" fill="#000000" font-size="14" stroke="#000000" '
                        f'font-family="sans-serif"><ellipse id="{eid}" cx="{cx}" cy="{cy}" rx="{r}" ry="{r}" '
                        f'fill="{off}" stroke="#4a5a62" stroke-width="1"/></g>')
        if onval is None:
            rng = [{"type": "range", "min": 0, "max": 0, "color": off}, {"type": "range", "min": 1, "max": 1, "color": on}]
        else:   # last matching range wins in FUXA semaphore
            rng = [{"type": "range", "min": -32768, "max": 32767, "color": off},
                   {"type": "range", "min": onval, "max": onval, "color": on}]
        self.items[gid] = {"id": gid, "type": "svg-ext-gauge_semaphore", "name": name or sym, "label": "HtmlSemaphore",
                           "property": {"variableId": T(sym), "variableSrc": DEV_NAME, "events": [], "actions": [],
                                        "ranges": rng}}

    def bar(self, x, y, w, h, sym, zones, name=None):
        """Vertical bar meter (FUXA gauge_progress). zones: [(min, max, color, label)] bottom->top, engineering units.
        Bar colour follows the zone the value is in; a zone band with scale labels is drawn beside the bar."""
        gid, aid, bid, hid = self._id("GXP"), self._id("A-GXP"), self._id("B-GXP"), self._id("H-GXP")
        lo, hi = zones[0][0], zones[-1][1]
        # zone band + ticks (static)
        for zmin, zmax, color, label in zones:
            y_top = y + h - (zmax - lo) / (hi - lo) * h
            y_bot = y + h - (zmin - lo) / (hi - lo) * h
            self.svg.append(f'<rect id="{self._id("svg")}" x="{x - 12}" y="{y_top:.1f}" width="8" '
                            f'height="{y_bot - y_top:.1f}" fill="{color}" stroke-width="0"/>')
        for v in sorted({z[0] for z in zones} | {zones[-1][1]}):
            yy = y + h - (v - lo) / (hi - lo) * h
            self.svg.append(f'<line id="{self._id("svg")}" x1="{x - 16}" y1="{yy:.1f}" x2="{x + w}" y2="{yy:.1f}" '
                            f'stroke="#8a979e" stroke-width="1" stroke-dasharray="3,2"/>')
            self.text(x - 18, yy + 4, f"{v:g}", size=10, fill=C_MUTED, anchor="end")
        self.svg.append(
            f'<g id="{gid}" type="svg-ext-gauge_progress" font-family="sans-serif" font-size="14" stroke="null">'
            f'<rect id="{aid}" x="{x}" y="{y}" width="{w}" height="{h}" fill="#e3e8ebff" stroke="#9aa7ad"/>'
            f'<rect id="{bid}" x="{x}" y="{y + h}" width="{w}" height="0" fill="{zones[0][2]}" stroke="null"/>'
            f'<foreignObject id="{hid}" x="{x}" y="{y}" width="{w}" height="{h}" font-size="14"/></g>')
        rng = [{"type": "minmax", "min": zmin, "max": zmax, "color": color, "text": "", "style": [False, False]}
               for zmin, zmax, color, label in zones]
        self.items[gid] = {"id": gid, "type": "svg-ext-gauge_progress", "name": name or sym, "label": "HtmlProgress",
                           "property": {"variableId": T(sym), "variableSrc": DEV_NAME, "events": [], "actions": [],
                                        "ranges": rng}}

    def button(self, x, y, w, h, label, sym, action="onSetValue", param="1", color=C_ACC, name=None, view=None):
        gid, rid, fid, bid = self._id("HXB"), self._id("svg"), self._id("H-HXB"), self._id("B-HXB")
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        self.svg.append(
            f'<g id="{gid}" type="svg-ext-html_button" fill="#FFFFFF" font-size="14" font-family="sans-serif" '
            f'text-anchor="right" stroke="#000000"><rect id="{rid}" stroke-width="0" x="{x}" y="{y}" width="{w}" '
            f'height="{h}" fill="{color}ff" stroke="#ffffff"/><foreignObject id="{fid}" x="{x}" y="{y}" height="{h}" '
            f'width="{w}"><BUTTON id="{bid}" style="width: 100%; height: 100%; vector-effect: non-scaling-stroke; '
            f'background-color: rgb({r}, {g}, {b}); color: rgb(255, 255, 255); font-size: 14px;" '
            f'class="md-btn  md-btn-raised">{esc(label)}</BUTTON></foreignObject></g>')
        prop = {"events": [{"type": "click", "action": action, "actparam": view if action == "onpage" else param,
                            "actoptions": {}}], "actions": [], "text": label}
        if sym:
            prop.update({"variableId": T(sym), "variableSrc": DEV_NAME})
        self.items[gid] = {"id": gid, "type": "svg-ext-html_button", "name": name or label, "label": "HtmlButton",
                           "property": prop}

    def inp(self, x, y, w, h, sym, mn=None, mx=None):
        gid, rid, fid, iid = self._id("HXI"), self._id("svg"), self._id("H-HXI"), self._id("I-HXI")
        self.svg.append(
            f'<g id="{gid}" type="svg-ext-html_input" stroke="#000000" text-anchor="right" font-family="sans-serif" '
            f'font-size="14" fill="#f1f1f1ff"><rect id="{rid}" x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" '
            f'stroke="{C_LINE}" stroke-width="1"/><foreignObject id="{fid}" x="{x}" y="{y}" width="{w}" height="{h}">'
            f'<INPUT id="{iid}" type="text" style="width: calc(100% - 7px); height: calc(100% - 7px); text-align: right; '
            f'border: unset; background-color: rgb(255, 255, 255); color: rgb(0, 0, 0); font-size: 14px; '
            f'vector-effect: non-scaling-stroke;"/></foreignObject></g>')
        opts = {"updated": True, "numeric": True, "type": "number", "updatedEsc": False, "selectOnClick": True,
                "actionOnEsc": "update"}
        if mn is not None: opts["min"] = mn
        if mx is not None: opts["max"] = mx
        self.items[gid] = {"id": gid, "type": "svg-ext-html_input", "name": sym, "label": "HtmlInput",
                           "property": {"variableId": T(sym), "variableSrc": DEV_NAME, "events": [], "actions": [],
                                        "options": opts}}

    def chart(self, x, y, w, h, chart_id, name):
        gid, rid, fid, did = self._id("HXC"), self._id("svg"), self._id("H-HXC"), self._id("D-HXC")
        self.svg.append(
            f'<g id="{gid}" type="svg-ext-html_chart" fill="#FFFFFF" font-size="14" font-family="sans-serif" '
            f'text-anchor="right" stroke="#000000"><rect id="{rid}" stroke-width="0" x="{x}" y="{y}" width="{w}" '
            f'height="{h}" fill="#ffffff"/><foreignObject id="{fid}" x="{x}" y="{y}" height="{h}" width="{w}">'
            f'<DIV id="{did}" style="width: 100%; height: 100%; vector-effect: non-scaling-stroke;"></DIV>'
            f'</foreignObject></g>')
        self.items[gid] = {"id": gid, "type": "svg-ext-html_chart", "name": name, "label": "HtmlChart",
                           "property": {"id": chart_id, "type": "realtime1", "options": {
                               "realtime": 60, "refreshInterval": 1, "lastRange": "last8h", "dateFormat": "dd/MM/yyyy",
                               "timeFormat": "hh:mm:ss", "legendMode": "always", "fontFamily": "sans-serif",
                               "titleHeight": 0, "axisLabelFontSize": 12, "colorBackground": "rgba(0,0,0,0)",
                               "axisLineColor": "rgba(0,0,0,1)", "axisLabelColor": "rgba(0,0,0,1)",
                               "gridLineColor": "rgba(0,0,0,0.2)", "yAxisLegend": True}}}

    def header(self, title, sub):
        self.rect(0, 0, self.w, 56, fill=C_HEAD, stroke=C_HEAD, rx=0)
        self.text(24, 36, title, size=22, fill="#ffffff", weight="bold")
        self.text(self.w - 24, 34, sub, size=13, fill="#cfe3ec", anchor="end")
        self.lamp(self.w - 420, 28, "HEARTBEAT", on="#7be495", off="#2b5466", r=8, name="Heartbeat PLC")
        self.text(self.w - 404, 33, "PLC", size=12, fill="#cfe3ec")

    def build(self):
        body = "\n".join(self.svg)
        svg = (f'<svg width="{self.w}" height="{self.h}" xmlns="http://www.w3.org/2000/svg" '
               f'xmlns:svg="http://www.w3.org/2000/svg"><g><title>Layer 1</title>'
               f'<rect id="svg_bg_{self.id}" x="0" y="0" width="{self.w}" height="{self.h}" fill="{C_BG}" stroke-width="0"/>'
               f'{body}</g></svg>')
        return {"id": self.id, "name": self.name, "type": "svg",
                "profile": {"width": self.w, "height": self.h, "bkcolor": C_BG, "margin": 10, "align": "topCenter",
                            "gridType": "fixed", "viewRenderDelay": 0},
                "items": self.items, "variables": {}, "svgcontent": svg, "property": {"events": []}}

V_OV, V_TR, V_SP, V_IO = "v_kb_overview", "v_kb_trend", "v_kb_setpoint", "v_kb_io"
CH_ALL, CH_PH = "c_kb_kualitas", "c_kb_ph"

# ------------------------------------------------------------------ Overview
ov = View(V_OV, "Overview")
ov.header("PDAM KALBAR  ·  Monitoring Kualitas Air", "M221 · BAMa · D1Cb ×3 · TUC 5")
PD = {n: dflt for n, mw, dflt, u, c in PARAMS}
phL, phH = PD["P_PH_L"] / 100, PD["P_PH_H"] / 100
clL, clH = PD["P_CL_L"] / 100, PD["P_CL_H"] / 100
tuM, tuH = PD["P_TU_M"] / 100, PD["P_TU_H"] / 100
# zone colours: pH/klor -> rendah kuning, menengah hijau, tinggi merah; turbidity -> rendah hijau (baik)
Z_PH = [(0, phL, C_WARN, "Rendah"), (phL, phH, C_OK, "Menengah"), (phH, 14, C_ALM, "Tinggi")]
Z_CL = [(0, clL, C_WARN, "Rendah"), (clL, clH, C_OK, "Menengah"), (clH, 2, C_ALM, "Tinggi")]
Z_TU = [(0, tuM, C_OK, "Rendah"), (tuM, tuH, C_WARN, "Menengah"), (tuH, 5, C_ALM, "Tinggi")]
cards = [("PH1_PV", "pH #1", "pH", "VALID_PH1", "A_PH1_L", "A_PH1_H", "P_PH_L", "P_PH_H", "A_PH1_SIG", "PH1_ZONE", Z_PH),
         ("PH2_PV", "pH #2", "pH", "VALID_PH2", "A_PH2_L", "A_PH2_H", "P_PH_L", "P_PH_H", "A_PH2_SIG", "PH2_ZONE", Z_PH),
         ("CL_PV", "Sisa klor bebas", "mg/L", "VALID_CL", "A_CL_L", "A_CL_H", "P_CL_L", "P_CL_H", "A_CL_SIG", "CL_ZONE", Z_CL),
         ("TU_PV", "Turbidity", "NTU", "VALID_TU", None, "A_TU_H", "P_TU_M", "P_TU_H", "A_TU_SIG", "TU_ZONE", Z_TU)]
cw, gap, x0, y0, chh = 295, 20, 24, 72, 318
for i, (pv, title, unit, valid, al, ah, pl, ph, sig, zone, zones) in enumerate(cards):
    x = x0 + i * (cw + gap)
    ov.rect(x, y0, cw, chh)
    ov.text(x + 16, y0 + 28, title, size=17, weight="bold")
    ov.lamp(x + cw - 24, y0 + 22, valid, r=9, name=f"{title} valid")
    ov.text(x + cw - 38, y0 + 27, "valid", size=11, fill=C_MUTED, anchor="end")
    # value block (left)
    ov.value(x + 92, y0 + 96, pv, size=44, unit="", name=title)
    ov.text(x + 92, y0 + 120, unit, size=15, fill=C_MUTED, anchor="middle")
    # zone indicators (from PLC zone word, follow live setpoints)
    for k, (zmin, zmax, color, lbl) in enumerate(reversed(zones)):
        zy = y0 + 150 + k * 30
        val = 3 - k
        ov.rect(x + 16, zy - 12, 150, 24, fill="#f6f8f9", stroke=C_LINE, rx=12)
        ov.lamp(x + 30, zy, zone, on=color, r=8, onval=val, name=f"{title} zona {lbl}")
        ov.text(x + 44, zy + 5, lbl.upper(), size=12, weight="bold")
    # bar meter (right)
    ov.bar(x + cw - 66, y0 + 46, 34, 196, pv, zones, name=f"{title} bar")
    # alarms + limits
    yy = y0 + 266
    if al:
        ov.lamp(x + 24, yy, al, on=C_ALM, r=7, name=f"{title} alarm rendah"); ov.text(x + 36, yy + 4, "Alm rendah", size=11)
    ov.lamp(x + 112, yy, ah, on=C_ALM, r=7, name=f"{title} alarm tinggi"); ov.text(x + 124, yy + 4, "Alm tinggi", size=11)
    ov.lamp(x + 200, yy, sig, on=C_WARN, r=7, name=f"{title} sinyal"); ov.text(x + 212, yy + 4, "Sinyal", size=11)
    ov.text(x + 16, y0 + 300, "Batas PLC:", size=11, fill=C_MUTED)
    ov.value(x + 118, y0 + 300, pl, size=11, anchor="end", fill=C_MUTED, unit="")
    ov.text(x + 122, y0 + 300, "–", size=11, fill=C_MUTED)
    ov.value(x + 164, y0 + 300, ph, size=11, anchor="end", fill=C_MUTED, unit="")
    ov.text(x + 168, y0 + 300, unit, size=11, fill=C_MUTED)

# flow & dosing
y1 = 404
ov.rect(24, y1, 610, 246)
ov.text(42, y1 + 30, "Aliran sampel BAMa & dosing", size=17, weight="bold")
ov.lamp(56, y1 + 60, "X_FS_SAMPLE", name="Reed switch"); ov.text(76, y1 + 65, "Reed switch aliran (%I0.0)", size=14)
ov.lamp(56, y1 + 90, "FLOW_STAB", name="Aliran stabil"); ov.text(76, y1 + 95, "Aliran stabil / pengukuran pH & klor valid", size=14)
ov.lamp(56, y1 + 120, "A_NOFLOW", on=C_ALM, name="Alarm aliran"); ov.text(76, y1 + 125, "Alarm aliran sampel hilang", size=14)
ov.text(42, y1 + 158, "Controller", size=12, fill=C_MUTED); ov.text(250, y1 + 158, "PAUSE", size=12, fill=C_MUTED)
ov.text(330, y1 + 158, "Pause manual (kalibrasi)", size=12, fill=C_MUTED)
for j, (lbl, q, mp) in enumerate([("D1Cb pH #1", "X_Q_PAUSE_PH1", "MAN_PAUSE_PH1"),
                                  ("D1Cb pH #2", "X_Q_PAUSE_PH2", "MAN_PAUSE_PH2"),
                                  ("D1Cb klorin", "X_Q_PAUSE_CL", "MAN_PAUSE_CL")]):
    yy = y1 + 180 + j * 22
    ov.text(42, yy + 5, lbl, size=14)
    ov.lamp(268, yy, q, on=C_WARN, r=8, name=f"{lbl} pause")
    ov.lamp(340, yy, mp, on=C_WARN, r=8, name=f"{lbl} manual")
    ov.button(360, yy - 10, 120, 20, "Toggle pause", mp, action="onToggleValue", color="#7a8790", name=f"{lbl} toggle")

# alarm summary
ov.rect(654, y1, 602, 246)
ov.text(672, y1 + 30, "Ringkasan alarm", size=17, weight="bold")
ov.lamp(686, y1 + 62, "ANY_ALARM", on=C_ALM, r=13, name="Ada alarm"); ov.text(708, y1 + 67, "Ada alarm aktif", size=15)
ov.lamp(686, y1 + 96, "BUZZ_LATCH", on=C_WARN, r=13, name="Belum ACK"); ov.text(708, y1 + 101, "Alarm baru belum di-ACK (buzzer)", size=15)
ov.lamp(686, y1 + 130, "QUALITY_OK", on=C_OK, r=13, name="Kualitas OK"); ov.text(708, y1 + 135, "Kualitas air normal", size=15)
ov.button(1050, y1 + 48, 180, 44, "ACK / Silence", "HMI_ACK", color=C_ALM, name="ACK")
alm_short = [("A_PH1_DEV", "D1Cb pH #1"), ("A_PH2_DEV", "D1Cb pH #2"), ("A_CL_DEV", "D1Cb klorin"),
             ("A_TU_A1", "TUC 5 alarm 1"), ("A_TU_A2", "TUC 5 fault"), ("A_PH_DIFF", "Selisih pH")]
for k, (a, lbl) in enumerate(alm_short):
    cx = 686 + (k % 3) * 190; cy = y1 + 178 + (k // 3) * 30
    ov.lamp(cx, cy, a, on=C_ALM, r=9, name=lbl); ov.text(cx + 16, cy + 5, lbl, size=13)

ov.text(24, 672, "Bar: warna & skala zona mengikuti batas default. Lampu RENDAH/MENENGAH/TINGGI dan alarm mengikuti setpoint PLC aktual.",
        size=12, fill=C_MUTED)
for k, (vid, lbl) in enumerate([(V_TR, "Trend"), (V_SP, "Setpoint"), (V_IO, "I/O & status")]):
    ov.button(24 + k * 150, 686, 136, 40, lbl, None, action="onpage", view=vid, color=C_ACC, name="Ke " + lbl)

# ------------------------------------------------------------------ Trend
tr = View(V_TR, "Trend")
tr.header("Trend kualitas air", "Realtime 60 menit · riwayat dari DAQ")
tr.rect(24, 76, 1232, 300); tr.text(42, 104, "pH #1 / pH #2", size=16, weight="bold")
tr.chart(36, 116, 1208, 250, CH_PH, "Trend pH")
tr.rect(24, 392, 1232, 300); tr.text(42, 420, "Sisa klor (mg/L) / Turbidity (NTU)", size=16, weight="bold")
tr.chart(36, 432, 1208, 250, CH_ALL, "Trend klor & turbidity")
tr.button(24, 706, 136, 40, "Overview", None, action="onpage", view=V_OV, name="Ke Overview")

# ------------------------------------------------------------------ Setpoint
sp = View(V_SP, "Setpoint")
sp.header("Setpoint & parameter", "Ditulis langsung ke %MW0-%MW11 (retentive)")
sp.rect(24, 76, 1232, 622)
sp.text(42, 108, "Parameter", size=13, fill=C_MUTED, weight="bold")
sp.text(420, 108, "Nilai", size=13, fill=C_MUTED, weight="bold")
sp.text(560, 108, "Satuan", size=13, fill=C_MUTED, weight="bold")
sp.text(680, 108, "Keterangan", size=13, fill=C_MUTED, weight="bold")
LIM = {"P_TU_SRC": (0, 1), "P_PH_L": (0, 14), "P_PH_H": (0, 14), "P_PH_DIFF": (0, 14), "P_CL_L": (0, 5),
       "P_CL_H": (0, 5), "P_TU_H": (0, 10), "P_TU_M": (0, 10)}
for k, (name, mw, dflt, unit, cmt) in enumerate(PARAMS):
    y = 126 + k * 46
    div, dg, un = SCALE[name]
    sp.text(42, y + 20, name, size=14, weight="bold")
    sp.text(42, y + 36, f"%MW{mw} · default {dflt / div:g}", size=11, fill=C_MUTED)
    mn, mx = LIM.get(name, (0, 3600))
    sp.inp(420, y + 4, 120, 30, name, mn, mx)
    sp.text(560, y + 24, un or "–", size=14)
    short = cmt if len(cmt) <= 78 else cmt[:76] + "…"
    sp.text(680, y + 24, short, size=12, fill=C_MUTED)
sp.button(24, 708, 136, 40, "Overview", None, action="onpage", view=V_OV, name="Ke Overview")

# ------------------------------------------------------------------ I/O & status
io = View(V_IO, "I/O & status")
io.header("I/O PLC & status", "Cermin %I/%Q di %M40-56 · status internal")
def lamp_list(v, x, y, title, syms, on=C_OK):
    v.rect(x, y, 400, 46 + 36 * len(syms) + 6)
    v.text(x + 18, y + 28, title, size=16, weight="bold")
    for k, s in enumerate(syms):
        yy = y + 56 + k * 36
        base = s[2:] if s.startswith("X_") else s
        addr = SYM[base]["addr"] if base in SYM else SYM[s]["addr"]
        v.lamp(x + 30, yy, s, on=on, r=9)
        v.text(x + 50, yy + 5, f"{addr}  {base}", size=13, weight="bold")
        txt = SYM[base]["comment"]
        v.text(x + 50, yy + 19, txt if len(txt) < 62 else txt[:60] + "…", size=10, fill=C_MUTED)
lamp_list(io, 24, 76, "Digital input (TM221CE16R)", ["X_" + n for n in DI_NAMES])
lamp_list(io, 440, 76, "Digital output (relay)", ["X_" + n for n in DO_NAMES], on=C_WARN)
lamp_list(io, 856, 76, "Status internal", ["STARTUP_DONE", "FLOW_STAB", "VALID_PH1", "VALID_PH2", "VALID_CL",
                                           "VALID_TU", "QUALITY_OK", "PAUSE_ANY"])
io.rect(856, 420, 400, 230)
io.text(874, 448, "Turbidity TUC 5", size=16, weight="bold")
rows = [("TU_MA_PV", "Turbidity dari 4-20 mA", "NTU"), ("TU_MB_PV", "Turbidity dari Modbus", "NTU"),
        ("TU_STATUS", "Status reg 30010 (1 = baik)", ""), ("TU_ERRW", "Error bit reg 30012", ""),
        ("MB_ERR_TU", "Counter error komunikasi", ""), ("P_TU_SRC", "Sumber (0 = mA, 1 = Modbus)", "")]
for k, (s, lbl, u) in enumerate(rows):
    yy = 482 + k * 28
    io.text(874, yy, lbl, size=13)
    io.value(1236, yy, s, size=14, anchor="end", unit=u)
io.button(24, 700, 136, 40, "Overview", None, action="onpage", view=V_OV, name="Ke Overview")

views = [ov.build(), tr.build(), sp.build(), io.build()]

# ------------------------------------------------------------------ alarms (one per PLC alarm bit)
def sub(enabled, text="", group="", bk="#ff5252", fg="#ffffff"):
    return {"enabled": enabled, "checkdelay": 1, "min": 1, "max": 1, "timedelay": 1, "text": text, "group": group,
            "ackmode": "ackactive", "bkcolor": bk, "color": fg}
alarms = []
for n, txt, latch in ALARMS:
    grp = "Instrumen" if n.endswith(("_DEV", "_A1", "_A2", "_SIG", "_COMM", "_MBERR")) else "Kualitas air"
    if n == "A_NOFLOW":
        grp = "Aliran sampel"
    alarms.append({"name": n, "property": {"variableId": T(n), "permission": None},
                   "highhigh": sub(False), "high": sub(True, txt, grp), "low": sub(False), "info": sub(False),
                   "actions": {"enabled": False, "values": []}})

# ------------------------------------------------------------------ charts
def line(sym, color, label, yaxis=1):
    return {"device": DEV_NAME, "id": T(sym), "name": sym, "label": label, "color": color, "yaxis": yaxis,
            "lineInterpolation": 0, "lineWidth": 2, "spanGaps": True}
charts = [
    {"id": CH_PH, "name": "Trend pH", "lines": [line("PH1_PV", "#1d6f9a", "pH #1"), line("PH2_PV", "#e07b00", "pH #2")]},
    {"id": CH_ALL, "name": "Trend klor & turbidity",
     "lines": [line("CL_PV", "#2e9e4f", "Klor mg/L", 1), line("TU_PV", "#8a5a2b", "Turbidity NTU", 2)]},
]

project = {
    "version": "1.01",
    "name": "KALBAR PDAM Kualitas Air",
    "server": {"id": "0", "name": "FUXA Server", "type": "FuxaServer", "property": {}, "polling": 1000},
    "devices": {DEV_ID: device},
    "hmi": {
        "views": views,
        "layout": {
            "autoresize": True, "start": V_OV, "showdev": True, "zoom": "disabled", "inputdialog": "false",
            "hidenavigation": False, "theme": "", "loginonstart": False, "show_connection_error": True,
            "customStyles": "",
            "navigation": {"mode": "push", "type": "block", "bkcolor": "#123a4f", "fgcolor": "#ffffff", "logo": False,
                           "items": [{"id": uid("n", v["id"]), "text": v["name"], "link": "", "view": v["id"],
                                      "icon": ic, "image": "", "permission": None}
                                     for v, ic in zip(views, ["dashboard", "show_chart", "tune", "settings_input_component"])]},
            "header": {"title": "PDAM KALBAR", "alarms": "fix", "infos": "fix", "bkcolor": "#0d2c3c", "fgcolor": "#ffffff",
                       "height": 46, "buttonHeight": 36, "fontSize": 13, "items": [], "itemsAnchor": "left",
                       "dateTimeDisplay": "dd/MM/yyyy HH:mm:ss", "language": "nothing", "loginInfo": "nothing"},
        },
    },
    "alarms": alarms,
    "charts": charts,
    "notifications": [], "scripts": [], "reports": [], "texts": [], "graphs": [], "recipes": [],
}

out = os.path.join(HERE, "KB_FUXA_project.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(project, f, ensure_ascii=False, indent=1)

# tag list CSV for reference
with open(os.path.join(HERE, "KB_FUXA_tags.csv"), "w", encoding="utf-8-sig", newline="") as f:
    f.write("Tag;PLC;Modbus;Alamat FUXA (1-based);Tipe;Divisor;Keterangan\n")
    for s, t in TAGS.items():
        kind = "Coil" if t["memaddress"] == "000000" else "Holding register"
        f.write(f"{s};{SYM[s]['addr']};{kind};{t['address']};{t['type']};{t['divisor']};{SYM[s]['comment']}\n")
print("tags", len(TAGS), "alarms", len(alarms), "views", len(views), "->", out)
