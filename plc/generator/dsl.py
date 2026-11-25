# -*- coding: utf-8 -*-
import re
from symbols import SYM

class C:   # contact
    def __init__(s, sym, neg=False):
        assert sym in SYM or sym.startswith("%"), sym
        s.sym, s.neg = sym, neg
def N(sym): return C(sym, True)
class Cmp:
    def __init__(s, expr): s.expr = expr
class Ser:
    def __init__(s, *items): s.items = list(items)
class Par:
    def __init__(s, *items): s.items = list(items)

def A(name):
    if name.startswith("%"): return name
    return SYM[name]["addr"]

def AC(name):
    a = A(name)
    return a + ".Q" if a.startswith("%TM") else a

_tok = re.compile(r"\{(\w+)\}")
def expr_addr(e): return _tok.sub(lambda m: A(m.group(1)), e)
def expr_sym(e):  return _tok.sub(lambda m: m.group(1), e)
def check_expr(e):
    for m in _tok.finditer(e):
        assert m.group(1) in SYM, ("unknown symbol", m.group(1))

# outputs
def ST(s): return ("ST", s)
def STN(s): return ("STN", s)
def SET(s): return ("S", s)
def RST(s): return ("R", s)
def OP(e): check_expr(e); return ("OP", e)

class Rung:
    def __init__(s, title, cond, outs, comment="", timer=None, block=None):
        s.title, s.cond, s.outs, s.comment = title, cond, outs, comment
        s.timer = timer      # timer symbol: cond -> IN ; outs on Q
        s.block = block      # READ_VAR symbol: cond -> EXEC
        for o in outs:
            if o[0] != "OP": assert o[1] in SYM, o
        if isinstance(cond, Cmp): check_expr(cond.expr)

# ------------------------------------------------------------- IL
def norm(node):
    if node is None: return None
    if isinstance(node, (C, Cmp)): return Ser(node)
    if isinstance(node, Par): return Ser(node)
    return node

def _first_ok(el):
    return not (isinstance(el, C) and el.neg)

def _reorder(items):
    items = list(items)
    if items and not _first_ok(items[0]):
        for k, el in enumerate(items):
            if _first_ok(el):
                items.insert(0, items.pop(k)); break
        else:
            raise ValueError("all-negated group inside parentheses")
    return items

def _operand(el):
    if isinstance(el, C): return AC(el.sym)
    if isinstance(el, Cmp): return "[" + expr_addr(el.expr) + "]"
    raise TypeError(el)

def il_seq(items, op, out, inner=False):
    """op: 'LD' | 'AND(' | 'OR('"""
    if inner: items = _reorder(items)
    first = True
    for el in items:
        if first:
            if isinstance(el, Par):
                il_par(el, op, out, inner)
            else:
                if op == "LD":
                    out.append(("LDN " if isinstance(el, C) and el.neg else "LD ") + _operand(el))
                else:
                    out.append(op + " " + _operand(el))
            first = False
        else:
            if isinstance(el, Par):
                il_par(el, "AND(", out, True)
                out.append(")")
            elif isinstance(el, Ser):
                raise TypeError("nested Ser in Ser - flatten it")
            else:
                out.append(("ANDN " if isinstance(el, C) and el.neg else "AND ") + _operand(el))

def il_par(par, op, out, inner):
    br = [b.items if isinstance(b, Ser) else [b] for b in par.items]
    il_seq(br[0], op, out, inner or op != "LD")
    for b in br[1:]:
        if len(b) == 1 and not isinstance(b[0], Par):
            el = b[0]
            out.append(("ORN " if isinstance(el, C) and el.neg else "OR ") + _operand(el))
        else:
            il_seq(b, "OR(", out, True)
            out.append(")")

def il_outs(outs, out):
    for o in outs:
        if o[0] == "OP": out.append("[" + expr_addr(o[1]) + "]")
        else: out.append(f"{o[0]} {A(o[1])}")

def il_rung(r):
    out = []
    cond = norm(r.cond)
    if r.timer:
        out.append(f"BLK {A(r.timer)}")
        il_seq(cond.items, "LD", out)
        out.append("IN")
        if r.outs:
            out.append("OUT_BLK")
            out.append("LD Q")
            il_outs(r.outs, out)
        out.append("END_BLK")
        return out
    if r.block:
        out.append(f"BLK {A(r.block)}")
        il_seq(cond.items, "LD", out)
        out.append("EXEC")
        out.append("END_BLK")
        return out
    if cond is not None:
        il_seq(cond.items, "LD", out)
    il_outs(r.outs, out)
    return out

# ------------------------------------------------------------- SVG ladder
CW = 92      # contact cell width
RH = 58      # row height
PAD = 14

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def tw(text, px=6.3): return len(text) * px

class Box:
    def __init__(s, w, h, draw): s.w, s.h, s.draw = w, h, draw

def lay(node):
    if isinstance(node, C):
        sym = node.sym
        addr = AC(sym)
        label = sym if not sym.startswith("%") else ""
        w = max(CW, tw(label, 6.0) + 14)
        def dr(x, y, o, w=w, node=node, label=label, addr=addr):
            cx = x + w / 2
            o.append(f'<line class="w" x1="{x}" y1="{y}" x2="{cx-7}" y2="{y}"/>')
            o.append(f'<line class="w" x1="{cx+7}" y1="{y}" x2="{x+w}" y2="{y}"/>')
            o.append(f'<line class="k" x1="{cx-7}" y1="{y-11}" x2="{cx-7}" y2="{y+11}"/>')
            o.append(f'<line class="k" x1="{cx+7}" y1="{y-11}" x2="{cx+7}" y2="{y+11}"/>')
            if node.neg:
                o.append(f'<line class="k" x1="{cx-9}" y1="{y+11}" x2="{cx+9}" y2="{y-11}"/>')
            if label:
                o.append(f'<text class="sy" x="{cx}" y="{y-16}">{esc(label)}</text>')
            o.append(f'<text class="ad" x="{cx}" y="{y+24}">{esc(addr)}</text>')
        return Box(w, 1, dr)
    if isinstance(node, Cmp):
        ta = "[" + expr_addr(node.expr) + "]"
        ts = expr_sym(node.expr)
        bw = max(tw(ta, 6.4), tw(ts, 5.6)) + 18
        w = bw + 16
        def dr(x, y, o, w=w, bw=bw, ta=ta, ts=ts):
            o.append(f'<line class="w" x1="{x}" y1="{y}" x2="{x+8}" y2="{y}"/>')
            o.append(f'<line class="w" x1="{x+8+bw}" y1="{y}" x2="{x+w}" y2="{y}"/>')
            o.append(f'<rect class="cb" x="{x+8}" y="{y-12}" width="{bw}" height="24" rx="3"/>')
            o.append(f'<text class="cx" x="{x+8+bw/2}" y="{y+4}">{esc(ta)}</text>')
            o.append(f'<text class="sy" x="{x+8+bw/2}" y="{y-17}">{esc(ts)}</text>')
        return Box(w, 1, dr)
    if isinstance(node, Ser):
        bs = [lay(i) for i in node.items]
        w = sum(b.w for b in bs); h = max(b.h for b in bs)
        def dr(x, y, o, bs=bs):
            for b in bs:
                b.draw(x, y, o); x += b.w
        return Box(w, h, dr)
    if isinstance(node, Par):
        bs = [lay(i) for i in node.items]
        w = max(b.w for b in bs) + 16; h = sum(b.h for b in bs)
        def dr(x, y, o, bs=bs, w=w):
            yy = y
            last = y
            for b in bs:
                o.append(f'<line class="w" x1="{x}" y1="{yy}" x2="{x+8}" y2="{yy}"/>')
                b.draw(x + 8, yy, o)
                o.append(f'<line class="w" x1="{x+8+b.w}" y1="{yy}" x2="{x+w}" y2="{yy}"/>')
                last = yy
                yy += b.h * RH
            o.append(f'<line class="w" x1="{x}" y1="{y}" x2="{x}" y2="{last}"/>')
            o.append(f'<line class="w" x1="{x+w}" y1="{y}" x2="{x+w}" y2="{last}"/>')
        return Box(w, h, dr)
    raise TypeError(node)

def out_box(o):
    kind, val = o
    if kind == "OP":
        ta = "[" + expr_addr(val) + "]"; ts = expr_sym(val)
        bw = max(tw(ta, 6.4), tw(ts, 5.6)) + 18
        def dr(x, y, out, bw=bw, ta=ta, ts=ts):
            out.append(f'<rect class="ob" x="{x}" y="{y-12}" width="{bw}" height="24" rx="3"/>')
            out.append(f'<text class="cx" x="{x+bw/2}" y="{y+4}">{esc(ta)}</text>')
            out.append(f'<text class="sy" x="{x+bw/2}" y="{y-17}">{esc(ts)}</text>')
        return bw, dr
    label = val; addr = A(val)
    bw = max(70, tw(label, 6.0) + 10)
    tag = {"ST": "", "STN": "/", "S": "S", "R": "R"}[kind]
    def dr(x, y, out, bw=bw, label=label, addr=addr, tag=tag, kind=kind):
        cx = x + bw / 2
        out.append(f'<line class="w" x1="{x}" y1="{y}" x2="{cx-10}" y2="{y}"/>')
        cls = "cl" + (" set" if kind == "S" else " rst" if kind == "R" else "")
        out.append(f'<path class="{cls}" d="M{cx-4} {y-12} A13 13 0 0 0 {cx-4} {y+12} M{cx+4} {y-12} A13 13 0 0 1 {cx+4} {y+12}"/>')
        if tag: out.append(f'<text class="ct" x="{cx}" y="{y+4}">{tag}</text>')
        out.append(f'<text class="sy" x="{cx}" y="{y-17}">{esc(label)}</text>')
        out.append(f'<text class="ad" x="{cx}" y="{y+25}">{esc(addr)}</text>')
    return bw, dr

def svg_rung(r):
    o = []
    x0 = 10
    cond = norm(r.cond)
    cb = lay(cond) if cond is not None else None
    cw = cb.w if cb else 30
    ch = cb.h if cb else 1
    y0 = 34
    x = x0 + 6
    if cb: cb.draw(x, y0, o)
    else: o.append(f'<line class="w" x1="{x}" y1="{y0}" x2="{x+cw}" y2="{y0}"/>')
    x += cw
    if r.timer or r.block:
        name = r.timer or r.block
        addr = A(name)
        if r.timer:
            from symbols import TIMERS
            idx = int(addr[3:])
            tn, base, pre, _ = TIMERS[idx]
            pre_s = (f"P={pre}" if isinstance(pre, int) else f"P={A(pre)}") + f" ({base})"
            l1, l2, pin, qout = f"TON {addr}", pre_s, "IN", "Q"
        else:
            l1, l2, pin, qout = f"READ_VAR {addr}", "SL1 Modbus", "EXEC", "D/E"
        bw = max(150, tw(name, 6.2) + 20)
        o.append(f'<line class="w" x1="{x}" y1="{y0}" x2="{x+10}" y2="{y0}"/>')
        o.append(f'<rect class="tb" x="{x+10}" y="{y0-22}" width="{bw}" height="62" rx="4"/>')
        o.append(f'<text class="tt" x="{x+10+bw/2}" y="{y0-6}">{esc(l1)}</text>')
        o.append(f'<text class="sy" x="{x+10+bw/2}" y="{y0+10}">{esc(name)}</text>')
        o.append(f'<text class="ad" x="{x+10+bw/2}" y="{y0+30}">{esc(l2)}</text>')
        o.append(f'<text class="pn" x="{x+16}" y="{y0+3}" text-anchor="start">{pin}</text>')
        o.append(f'<text class="pn" x="{x+4+bw}" y="{y0+3}" text-anchor="end">{qout}</text>')
        x += bw + 10
        ch = max(ch, 1.4)
    olist = list(r.outs)
    if len(olist) > 8:
        more = len(olist) - 6
        olist = olist[:6] + [("OP", f"... +{more} operasi lagi (lihat IL)")]
    outs = [out_box(ot) for ot in olist]
    ow = max([w for w, _ in outs] + [0])
    xo = x + 24
    o.append(f'<line class="w" x1="{x}" y1="{y0}" x2="{xo}" y2="{y0}"/>')
    yy = y0
    last = y0
    xr = xo + ow + 18
    for w, dr in outs:
        o.append(f'<line class="w" x1="{xo}" y1="{yy}" x2="{xo+12}" y2="{yy}"/>')
        dr(xo + 12, yy, o)
        o.append(f'<line class="w" x1="{xo+12+w}" y1="{yy}" x2="{xr}" y2="{yy}"/>')
        last = yy; yy += RH
    if len(outs) > 1:
        o.append(f'<line class="w" x1="{xo}" y1="{y0}" x2="{xo}" y2="{last}"/>')
    rows = max(ch, len(outs))
    H = int(y0 + (rows - 1) * RH + 34)
    W = int(xr + 12)
    o.insert(0, f'<line class="rail" x1="{x0}" y1="6" x2="{x0}" y2="{H-6}"/>')
    o.append(f'<line class="rail" x1="{xr}" y1="6" x2="{xr}" y2="{H-6}"/>')
    o.append(f'<line class="w" x1="{x0}" y1="{y0}" x2="{x0+6}" y2="{y0}"/>')
    return f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">' + "".join(o) + "</svg>"
