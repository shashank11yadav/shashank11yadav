"""Generate light/dark SVGs for the profile README: hero banner + project diagrams."""
import os
import sys
from html import escape

import argparse

ARGS = argparse.ArgumentParser(description=__doc__)
ARGS.add_argument("out")
ARGS.add_argument("--views", type=int, help="profile-view count to show in the banner")
ARGS.add_argument("--only", help="comma-separated image names to render, e.g. hero")
ARGS.add_argument("--contrib", help="contributions JSON from scripts/contributions.py")
ARGS = ARGS.parse_args()
OUT = ARGS.out
os.makedirs(OUT, exist_ok=True)

THEMES = {
    "light": dict(bg="#f6f8fa", card="#ffffff", border="#d0d7de", text="#1f2328",
                  muted="#59636e", accent="#0969da", good="#1a7f37", line="#8c959f",
                  goodbg="#f0fff4", warm="#bc4c00", violet="#8250df", pink="#bf3989", eye="#1f2328",
                  cells=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"], glow="#b6d6ff"),
    "dark": dict(bg="#161b22", card="#0d1117", border="#30363d", text="#e6edf3",
                 muted="#9198a1", accent="#4493f8", good="#3fb950", line="#6e7681",
                 goodbg="#0f1f14", warm="#f0883e", violet="#ab7df8", pink="#db61a2", eye="#0d1117",
                 cells=["#21262d", "#0e4429", "#006d32", "#26a641", "#39d353"], glow="#1f3f6b"),
}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"


# Phone layer: when the image is drawn narrower than 600px, swap the desktop group (.dt)
# for a larger, simpler phone group (.ph). Media queries inside an SVG used as an <img>
# evaluate against the image's own rendered width.
PHONE_CSS = """
  .ph{display:none}
  @media (max-width: 600px){ .dt{display:none} .ph{display:inline} }
"""


# Walking robots (modelled on SahajIVVIX-1's): each robot follows a path with SMIL
# animateMotion, but stop-and-go: it eases into a stop, waits, glances back, and walks on.
# Legs swing and the body bobs only while it walks (an animated class switches that on and
# off); it can vanish for a while and pop back in with a small burst of dots.
import math

ROBOT_CSS = """
  .leg{transform-box:fill-box;transform-origin:50% 0}
  .walk{animation:bob .32s ease-in-out infinite alternate}
  .walk .leg{animation:leg .32s ease-in-out infinite alternate}
  .walk .leg2{animation-delay:-.32s}
  @keyframes leg{from{transform:rotate(-26deg)}to{transform:rotate(26deg)}}
  @keyframes bob{to{transform:translateY(-1.6px)}}
  .blink{transform-box:fill-box;transform-origin:center;animation:blink 4.2s infinite}
  @keyframes blink{0%,94%,100%{transform:scaleY(1)}97%{transform:scaleY(.1)}}
  .ant{animation:ant 1.6s ease-in-out infinite}
  @keyframes ant{50%{opacity:.3}}
  @media (prefers-reduced-motion: reduce){ .bot{display:none} }
"""
EASE, FLAT = ".42 0 .58 1", "0 0 1 1"


class Path:
    """Builds an SVG path and keeps its exact length, so stops can be placed on it."""

    def __init__(self, x, y):
        self.d, self.length, self.x, self.y, self.marks = f"M{x:.1f},{y:.1f}", 0.0, x, y, []

    def line(self, x, y):
        self.d += f" L{x:.1f},{y:.1f}"
        self.length += math.hypot(x - self.x, y - self.y)
        self.x, self.y = x, y
        return self

    def corner(self, x, y, r):           # quarter circle, clockwise
        self.d += f" A{r},{r} 0 0 1 {x:.1f},{y:.1f}"
        self.length += math.pi * r / 2
        self.x, self.y = x, y
        return self

    def jump(self, x, y, lift):
        cx, cy = (self.x + x) / 2, min(self.y, y) - lift
        pts = [((1 - u) ** 2 * self.x + 2 * (1 - u) * u * cx + u * u * x,
                (1 - u) ** 2 * self.y + 2 * (1 - u) * u * cy + u * u * y) for u in [i / 60 for i in range(61)]]
        self.length += sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        self.d += f" Q{cx:.1f},{cy:.1f} {x:.1f},{y:.1f}"
        self.x, self.y = x, y
        return self

    def mark(self, kind="stop"):
        self.marks.append((self.length, kind, (self.x, self.y)))
        return self

    def box(self, x, y, w, h, r):
        """Once round a rounded box clockwise from its top-left, with a stop on each side."""
        self.line(x + w - r, y).mark().corner(x + w, y + r, r).line(x + w, y + h - r).mark()
        self.corner(x + w - r, y + h, r).line(x + r, y + h).mark().corner(x, y + h - r, r)
        self.line(x, y + r).corner(x + r, y, r)
        return self


def timeline(path, speed, pauses, jump_speed=None, hide=0.0, appear_burst=False):
    """Turn a path's marks into SMIL timing. Returns dict of keyTimes/keyPoints/etc and bursts."""
    L = path.length
    ev, pos, k = [], 0.0, 0                      # (kind, from, to, seconds)
    if hide:
        ev.append(("hide", 0.0, 0.0, hide))
    start = tuple(float(v) for v in path.d.split()[0][1:].split(","))
    bursts = [(hide, start)] if appear_burst else []      # pop in where it reappears
    for at, kind, pt in path.marks + [(L, "stop", None)]:
        seg = at - pos
        if seg > 0.5:
            fast = jump_speed if kind == "land" else None
            ev.append(("move", pos / L, at / L, max(seg / (fast or speed), 0.35)))
        pause = pauses[k % len(pauses)]; k += 1
        ev.append(("pause", at / L, at / L, pause))
        if kind == "land":
            bursts.append((sum(e[3] for e in ev[:-1]), pt))
        pos = at
    total = sum(e[3] for e in ev)
    kt, kp, ks, t = [0.0], [ev[0][1]], [], 0.0
    eye_v, eye_t, cls_v, cls_t, op_v, op_t = [], [], [], [], [], []
    for kind, a, b, dur in ev:
        cls_v.append("walk" if kind == "move" else "idle"); cls_t.append(t / total)
        op_v.append("0" if kind == "hide" else "1"); op_t.append(t / total)
        if kind == "pause" and dur >= 0.8:           # glance back, then forward again
            for f, v in [(0, 2.4), (0.2, -2.4), (0.65, -2.4), (0.85, 2.4)]:
                eye_t.append((t + f * dur) / total); eye_v.append(v)
        else:
            eye_t.append(t / total); eye_v.append(2.4)
        t += dur
        kt.append(t / total); kp.append(b); ks.append(EASE if kind == "move" else FLAT)
    eye_t.append(1.0); eye_v.append(2.4)
    return dict(total=round(total, 2), kt=kt, kp=kp, ks=ks, eye=(eye_t, eye_v), cls=(cls_t, cls_v),
                op=(op_t, op_v), bursts=[(bt / total, pt) for bt, pt in bursts])


def _times(xs):
    return ";".join(f"{x:.4f}" for x in xs)


def burst(t, c1, c2, x, y, at, dur, begin, scale):
    a = min(at, 0.995); b = min(a + 0.9 / dur, 0.999); e = min(a + 0.12 / dur, b - 0.0001)
    kt = f"0;{a:.4f};{e:.4f};{b:.4f};1"
    dots = "".join(f'<circle cx="{14 * math.cos(i * math.pi / 5):.1f}" cy="{14 * math.sin(i * math.pi / 5):.1f}" '
                   f'r="{2.2 if i % 2 else 1.6}" fill="{c1 if i % 2 else c2}"/>' for i in range(10))
    anim = f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"'
    return (f'<g class="bot" transform="translate({x:.1f} {y - 10 * scale:.1f}) scale({scale})"><g opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="{kt}" {anim}/>'
            f'<animateTransform attributeName="transform" type="scale" values=".2;.2;.6;1.7;1.7" keyTimes="{kt}" {anim}/>'
            f'<circle r="9" fill="none" stroke="{c1}" stroke-width="1.4"/>'
            f'<circle r="5" fill="none" stroke="{c2}" stroke-width="1.2" stroke-dasharray="2 3"/>{dots}</g></g>')


def robot(t, color, path, tl, phase, scale, rotate="auto", partner="accent"):
    c, dur = t[color], tl["total"]
    begin = -round(dur * phase, 2)
    anim = f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"'
    motion = (f'<animateMotion {anim} rotate="{rotate}" path="{path.d}" calcMode="spline" '
              f'keyTimes="{_times(tl["kt"])}" keyPoints="{_times(tl["kp"])}" keySplines="{";".join(tl["ks"])}"/>')
    vis = (f'<animate attributeName="opacity" calcMode="discrete" values="{";".join(tl["op"][1])}" '
           f'keyTimes="{_times(tl["op"][0])}" {anim}/>') if "0" in tl["op"][1] else ""
    walk = (f'<animate attributeName="class" calcMode="discrete" values="{";".join(tl["cls"][1])}" '
            f'keyTimes="{_times(tl["cls"][0])}" {anim}/>')
    eye = (f'<animateTransform attributeName="transform" type="translate" '
           f'values="{";".join(f"{v} 0" for v in tl["eye"][1])}" keyTimes="{_times(tl["eye"][0])}" {anim}/>')
    body = f"""<g class="bot">{motion}{vis}
<g transform="scale({scale})"><g class="idle">{walk}
<line class="leg" x1="-3" y1="-6" x2="-3" y2="0" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>
<line class="leg leg2" x1="3" y1="-6" x2="3" y2="0" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>
<rect x="-7.5" y="-17" width="15" height="12" rx="5" fill="{c}"/>
<g transform="translate(2.4 0)">{eye}<g class="blink"><circle cx="0" cy="-11.6" r="2.4" fill="{t['eye']}"/></g></g>
<line x1="0" y1="-17" x2="0" y2="-21.5" stroke="{c}" stroke-width="1.4" stroke-linecap="round"/>
<circle class="ant" cx="0" cy="-22.6" r="1.7" fill="{c}"/>
</g></g></g>"""
    pops = "".join(burst(t, c, t[partner], float(pt[0]), float(pt[1]), at, dur, begin, scale)
                   for at, pt in tl["bursts"])
    return body + pops


def perimeter(m, w, h, r=14):
    p = Path(m + r, m)
    p.line(m + w - r, m).corner(m + w, m + r, r).line(m + w, m + h - r).corner(m + w - r, m + h, r)
    p.line(m + r, m + h).corner(m, m + h - r, r).line(m, m + r).corner(m + r, m, r)
    return p


def card_walker(t, color, m, w, h, phase, scale):
    p = perimeter(m, w, h)
    for f in (0.14, 0.33, 0.52, 0.71, 0.88):            # stops spread round the card
        p.marks.append((f * p.length, "stop", None))
    tl = timeline(p, 85, [2.2, 1.4, 3.0, 1.0, 2.6, 1.8])
    return robot(t, color, p, tl, phase, scale)


def hopper_path(boxes, r=10, lift=70):
    """Round each box (feet on the border), then jump to the next; the last jumps back to the first."""
    x, y, w, h = boxes[0]
    p = Path(x + r, y)
    for i, (x, y, w, h) in enumerate(boxes):
        p.box(x, y, w, h, r)
        nx, ny, _, _ = boxes[(i + 1) % len(boxes)]
        p.jump(nx + r, ny, lift).mark("land")
    return p


def hoppers(t, boxes, colours, scale=1.1, speed=60):
    p = hopper_path(boxes)
    tl = timeline(p, speed, [1.2, 0.6, 1.6, 0.9, 2.0], jump_speed=speed * 2.6)
    return "\n".join(robot(t, c, p, tl, ph, scale, partner=colours[(i + 1) % len(colours)][0])
                     for i, (c, ph) in enumerate(colours))


def svg(w, h, body, t, title, style="", bots=(), scale=1.7, inner="", margin=None):
    """bots: list of (colour key, phase 0..1). With bots, the card gets a margin for them to walk in."""
    m = margin if margin is not None else (int(26 * scale) + 4 if bots else 0)
    if bots or inner:
        style += ROBOT_CSS
    css = f"<style>{style}</style>\n" if style else ""
    W, H = w + 2 * m, h + 2 * m
    card = (f'<rect x="{m + 0.5}" y="{m + 0.5}" width="{w - 1}" height="{h - 1}" rx="14" '
            f'fill="{t["bg"]}" stroke="{t["border"]}"/>')
    walkers = "\n".join(card_walker(t, c, m + 0.5, w - 1, h - 1, ph, scale) for c, ph in bots)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(title)}">
<title>{escape(title)}</title>
{css}<defs>
  <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{t['line']}"/>
  </marker>
</defs>
{card}
<g transform="translate({m},{m})">
{body}
{inner}
</g>
{walkers}
</svg>
"""


def text(x, y, s, t, size=13, color="text", weight=400, font=SANS, anchor="start", spacing=0):
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{t[color]}" text-anchor="{anchor}"{ls}>{escape(s)}</text>')


def box(x, y, w, h, title, lines, t, mono=None, kind="normal"):
    stroke = t["good"] if kind == "good" else t["border"]
    fill = t["goodbg"] if kind == "good" else t["card"]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{1.5 if kind == "good" else 1}"/>']
    out.append(text(x + 14, y + 26, title, t, size=16, weight=600))
    for i, line in enumerate(lines):
        out.append(text(x + 14, y + 49 + i * 20, line, t, size=13.5, color="muted"))
    if mono:
        out.append(text(x + 14, y + h - 13, mono, t, size=11, color="accent", font=MONO))
    return "\n".join(out)


def arrow(d, t, both=False):
    start = ' marker-start="url(#arr)"' if both else ""
    return f'<path d="{d}" fill="none" stroke="{t["line"]}" stroke-width="1.5"{start} marker-end="url(#arr)"/>'


def label(x, y, s, t, anchor="middle"):
    return text(x, y, s, t, size=11.5, color="muted", anchor=anchor)


# ---------------------------------------------------------------- hero
CYCLE = 4.0          # seconds for one packet to run the pipeline and rest
TRAVEL = 0.65        # fraction of the cycle spent travelling


HERO_MARGIN = int(26 * 1.7) + 4

FOCUS = ["→ production ML you can measure", "→ real-time fraud scoring",
         "→ retrieval that cites its sources", "→ evals before opinions"]
FOCUS_SLOT = 3.5       # seconds each phrase stays


def views_pill(t, n):
    x, y, w, h = 932, 34, 220, 34
    cy = y + h / 2
    return [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{t["card"]}" stroke="{t["border"]}"/>',
            f'<path d="M{x + 14},{cy} q8,-9 16,0 q-8,9 -16,0z" fill="none" stroke="{t["accent"]}" stroke-width="1.6" stroke-linejoin="round"/>',
            f'<circle cx="{x + 22}" cy="{cy}" r="2.6" fill="{t["accent"]}"/>',
            text(x + 40, cy + 4.5, "PROFILE VIEWS", t, size=12, color="muted", weight=600, font=MONO, spacing=1),
            text(x + w - 16, cy + 5.5, f"{n:,}", t, size=16, weight=700, anchor="end")]


def hero(t):
    x0, y0, gap = 800, 112, 46
    span = gap * 3
    hit = [round(CYCLE * TRAVEL * i / 3, 2) for i in range(4)]
    style = PHONE_CSS + f"""
  .pkt{{animation:travel {CYCLE}s linear infinite}}
  @keyframes travel{{
    0%{{transform:translateY(0);opacity:0}} 3%{{opacity:1}}
    {TRAVEL * 100:.0f}%{{transform:translateY({span}px);opacity:1}}
    {TRAVEL * 100 + 8:.0f}%,100%{{transform:translateY({span}px);opacity:0}} }}
  .node{{animation:lit {CYCLE}s linear infinite}}
  @keyframes lit{{ 0%{{fill:{t['accent']}}} 12%,100%{{fill:{t['bg']}}} }}
  .cur{{animation:blink 1.1s steps(1) infinite}}
  @keyframes blink{{ 50%{{opacity:0}} }}
  .ping{{transform-box:fill-box;transform-origin:center;animation:ping 2s ease-out infinite}}
  @keyframes ping{{ 0%{{transform:scale(1);opacity:.8}} 100%{{transform:scale(3);opacity:0}} }}
  .rot{{opacity:0;animation:rot {FOCUS_SLOT * len(FOCUS)}s ease-in-out infinite backwards}}
  @keyframes rot{{
    0%{{opacity:0;transform:translateY(7px)}} {100 / len(FOCUS) * 0.12:.1f}%{{opacity:1;transform:none}}
    {100 / len(FOCUS) * 0.88:.1f}%{{opacity:1;transform:none}} {100 / len(FOCUS):.1f}%,100%{{opacity:0;transform:translateY(-7px)}} }}
  @media (prefers-reduced-motion: reduce){{ .pkt,.node,.cur,.ping,.rot{{animation:none}} .pkt,.ping{{opacity:0}} .rot0{{opacity:1}} }}
"""

    def pill(x, y, label, size, h):
        w = 2 * h + len(label) * (size * 0.6 + 1)
        cy = y + h / 2
        return [f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="{h / 2}" fill="{t["card"]}" stroke="{t["border"]}"/>',
                f'<circle class="ping" cx="{x + h * 0.55}" cy="{cy}" r="{h * 0.14:.1f}" fill="{t["good"]}"/>',
                f'<circle cx="{x + h * 0.55}" cy="{cy}" r="{h * 0.14:.1f}" fill="{t["good"]}"/>',
                text(x + h, cy + size * 0.36, label, t, size=size, color="muted", weight=600, font=MONO, spacing=1)]

    def name(x, y, size):
        return (f'<text x="{x}" y="{y}" font-family="{SERIF}" font-size="{size}" fill="{t["text"]}">Shashank '
                f'<tspan font-style="italic" fill="{t["accent"]}">Yadav</tspan></text>')

    d = ['<g class="dt">']
    d += pill(48, 34, "OPEN TO SOFTWARE ENGINEER · BACKEND · ML/AI ROLES", 13, 34)
    d.append(name(46, 150, 76))
    d.append(text(48, 200, "Software engineer building real-time services, the data paths", t, size=22, color="muted"))
    d.append(text(48, 230, "behind them, and the evals that show the ML inside them works.", t, size=22, color="muted"))
    d.append(text(48, 278, "focus", t, size=15, color="muted", font=MONO))
    for i, phrase in enumerate(FOCUS):
        d.append(f'<g class="rot rot{i}" style="animation-delay:{i * FOCUS_SLOT}s">')
        d.append(text(104, 278, phrase, t, size=15, color="accent", weight=600, font=MONO))
        d.append(f'<rect class="cur" x="{104 + len(phrase) * 9.1 + 6:.0f}" y="264" width="8" height="17" fill="{t["accent"]}"/>')
        d.append("</g>")
    if ARGS.views is not None:
        d += views_pill(t, ARGS.views)
    d.append(f'<line x1="48" y1="312" x2="1152" y2="312" stroke="{t["border"]}"/>')
    for x, k, v in [(48, "MS COMPUTER SCIENCE", "UMass Boston · 2025"), (430, "BASED IN", "United States · open to remote"),
                    (812, "CURRENT ROLE", "Software Developer · Ally Financial")]:
        d.append(text(x, 344, k, t, size=12, color="muted", weight=600, font=MONO, spacing=1.5))
        d.append(text(x, 372, v, t, size=18, weight=600))
    rows = [("stream", "Kafka · Redis"), ("serve", "gRPC · Spring · FastAPI"),
            ("retrieve", "pgvector · BM25 · RRF"), ("evaluate", "bootstrap CIs · audits")]
    d.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 + span}" stroke="{t["border"]}" stroke-width="2"/>')
    for i, (k, v) in enumerate(rows):
        y = y0 + gap * i
        d.append(f'<circle class="node" style="animation-delay:{hit[i]}s" cx="{x0}" cy="{y}" r="7" '
                 f'fill="{t["bg"]}" stroke="{t["accent"]}" stroke-width="2.5"/>')
        d.append(text(x0 + 24, y + 6, k, t, size=18, color="accent", weight=600, font=MONO))
        d.append(text(x0 + 140, y + 6, v, t, size=18, color="muted"))
    d.append(f'<circle class="pkt" cx="{x0}" cy="{y0}" r="4" fill="{t["accent"]}"/>')
    d.append("</g>")
    p = ['<g class="ph">']
    p += pill(48, 30, "OPEN TO SWE · ML/AI ROLES", 30, 64)
    p.append(name(44, 214, 128))
    p.append(text(48, 288, "Backend & ML/AI engineer", t, size=52, color="muted"))
    p.append(text(48, 370, "Ally Financial · MS CS ’25", t, size=44, weight=600))
    p.append("</g>")
    return svg(1200, 400, "\n".join(d + p), t,
               "Shashank Yadav. Open to software engineer, backend and ML/AI roles. Software engineer building "
               "real-time services, the data paths behind them, and the evals that show the ML inside them works. "
               "MS in Computer Science, UMass Boston, 2025. Based in the United States, open to remote. Current role: "
               "Software Developer at Ally Financial.", style=style,
               bots=[("accent", 0.0), ("warm", 0.5)])


# ---------------------------------------------------------------- buttons
BUTTONS = [("portfolio", "Portfolio", True), ("linkedin", "LinkedIn", False), ("x", "X", False),
           ("email", "Email", False), ("resume", "Résumé", False), ("leetcode", "LeetCode", False)]


def button(t, label, primary):
    h, size = 52, 19
    label_w = len(label) * size * 0.6
    w = round(label_w + 92)
    fill, fg, stroke = (t["text"], t["bg"], t["text"]) if primary else (t["card"], t["text"], t["border"])
    ax = w - 38                                  # arrow box: ax..ax+11, vertically centred
    cx = (24 + ax - 10) / 2                      # centre of the label area
    arrow = t["accent"] if not primary else fg
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{escape(label)}">
<title>{escape(label)}</title>
<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{h / 2 - 1}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
<text x="{cx:.0f}" y="33" font-family="{SANS}" font-size="{size}" font-weight="600" fill="{fg}" text-anchor="middle">{escape(label)}</text>
<path d="M{ax},{h / 2 + 5.5} L{ax + 11},{h / 2 - 5.5} M{ax + 2},{h / 2 - 5.5} L{ax + 11},{h / 2 - 5.5} L{ax + 11},{h / 2 + 3.5}" fill="none" stroke="{arrow}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


# ---------------------------------------------------------------- section headers
SERIF = "'Iowan Old Style','Palatino Linotype','Book Antiqua',Palatino,Georgia,serif"
HEADER_COLOURS = ["accent", "warm", "good", "violet", "pink", "violet", "warm"]
SECTIONS = [("about", "01", "About", "whoami"), ("experience", "02", "Experience", "where I've shipped"),
            ("work", "03", "Featured work", "built, measured, written up"),
            ("opensource", "04", "Open-source contributions", "upstream"),
            ("interview", "04", "Things I'd bring up", "in an interview"),
            ("toolbox", "05", "Toolbox", "what I reach for"),
            ("activity", "06", "Activity", "a year on GitHub")]


def header(t, num, title, tag, colour="accent", idx=0):
    W, H, base = 1200, 96, 62
    title_w = len(title) * 44 * 0.5
    tag_w = len(tag) * (13 * 0.6 + 1)
    x1, x2 = 44 + title_w + 28, W - tag_w - 34
    style = PHONE_CSS + f"""
  .tip{{animation:tip 2.4s ease-in-out infinite}}
  @keyframes tip{{ 50%{{opacity:.25}} }}
  @media (prefers-reduced-motion: reduce){{ .tip{{animation:none}} .bot{{display:none}} }}
""" + ROBOT_CSS
    walk_y = base - 16
    a, b = x1 + 12, x2 - 24
    path = Path(a, walk_y)
    for f in (0.3, 0.62):
        path.line(a + (b - a) * f, walk_y).mark()
    path.line(b, walk_y).mark()
    for f in (0.7, 0.35):
        path.line(a + (b - a) * f, walk_y).mark()
    path.line(a, walk_y)
    tl = timeline(path, 46, [1.4, 2.2, 1.0, 1.8, 1.2, 0.8], hide=6 + 2.5 * idx, appear_burst=True)
    walker = robot(t, colour, path, tl, (idx * 0.17) % 1, 1.0, rotate="0", partner="warm" if colour != "warm" else "accent")
    d = ['<g class="dt">',
         text(0, base, num, t, size=15, color="accent", weight=600, font=MONO),
         f'<text x="40" y="{base}" font-family="{SERIF}" font-size="44" fill="{t["text"]}">{escape(title)}</text>',
         f'<line x1="{x1}" y1="{walk_y}" x2="{x2}" y2="{walk_y}" stroke="{t["border"]}" stroke-width="1.5"/>',
         f'<circle class="tip" cx="{x2 + 6}" cy="{walk_y}" r="4.5" fill="{t["accent"]}"/>',
         text(W, walk_y + 5, tag, t, size=13, color="muted", font=MONO, anchor="end"),
         walker, "</g>"]
    p = ['<g class="ph">',
         text(0, base + 8, num, t, size=34, color="accent", weight=600, font=MONO),
         f'<text x="76" y="{base + 8}" font-family="{SERIF}" font-size="76" fill="{t["text"]}">{escape(title)}</text>',
         "</g>"]
    svg_ = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{num} {escape(title)}">
<title>{num} {escape(title)}</title>
<style>{style}</style>
{chr(10).join(d + p)}
</svg>
"""
    return svg_


# ---------------------------------------------------------------- impact strip
def impact(t):
    cols = [
        ("−18%", "fraud losses, first quarter", "Ally Financial · real-time fraud scoring", "−18%", "fraud losses"),
        ("340 → 265 ms", "average fraud-API response", "Ally · query plans + connection pooling", "−22%", "API latency"),
        ("+0.095 F1", "LLM triage vs best free method", "pytest-triage · 95% CI +0.04 to +0.14", "+0.095", "F1 vs baseline"),
    ]
    d, p = ['<g class="dt">'], ['<g class="ph">']
    for i, (num, lab, sub, pnum, plab) in enumerate(cols):
        cx = 200 + 400 * i
        d.append(text(cx, 74, num, t, size=44, color="good", weight=700, anchor="middle"))
        d.append(text(cx, 108, lab, t, size=18, anchor="middle", weight=600))
        d.append(text(cx, 136, sub, t, size=14.5, color="muted", anchor="middle"))
        p.append(text(cx, 92, pnum, t, size=84, color="good", weight=700, anchor="middle"))
        p.append(text(cx, 148, plab, t, size=38, anchor="middle", weight=600))
        if i:
            for g in (d, p):
                g.append(f'<line x1="{400 * i}" y1="30" x2="{400 * i}" y2="140" stroke="{t["border"]}"/>')
    d.append("</g>"); p.append("</g>")
    return svg(1200, 170, "\n".join(d + p), t,
               "Results: fraud losses down 18% in the first quarter after launch of Ally Financial's real-time fraud "
               "scoring; average fraud-API response time from 340 to 265 ms after reworking query plans and adding "
               "connection pooling; pytest-triage's LLM labels beat the best free method by 0.095 macro-F1 "
               "(95% CI +0.04 to +0.14).", style=PHONE_CSS, margin=HERO_MARGIN)


# Request packets: a dot runs along an arrow during [start, end] of each cycle (fractions of the cycle).
MOTION_CSS = "\n  @media (prefers-reduced-motion: reduce){ .pkt{display:none} }\n"


def packet(d, t, start, end, cycle):
    kt = f"0;{start};{end};1"
    fade = f"0;{start};{start + 0.01};{end - 0.01};{end};1"
    return (f'<circle class="pkt" r="4.5" fill="{t["accent"]}" opacity="0">'
            f'<animateMotion dur="{cycle}s" repeatCount="indefinite" path="{d}" keyPoints="0;0;1;1" '
            f'keyTimes="{kt}" calcMode="linear"/>'
            f'<animate attributeName="opacity" dur="{cycle}s" repeatCount="indefinite" values="0;0;1;1;0;0" '
            f'keyTimes="{fade}"/></circle>')


def flow(t, cycle, hops):
    """hops: list of (path, start, end). Draws each arrow, then the packets above everything."""
    return [arrow(d, t) for d, _, _ in hops], [packet(d, t, a, b, cycle) for d, a, b in hops]


# ---------------------------------------------------------------- pytest-triage
def triage(t):
    arrows, pkts = flow(t, 4.5, [
        ("M170,202 L198,202", 0.02, 0.12),
        ("M375,188 C392,188 392,104 408,104", 0.14, 0.30),
        ("M375,216 C392,216 392,284 408,284", 0.14, 0.30),
        ("M720,104 C738,104 736,170 753,170", 0.40, 0.56),
        ("M720,284 C738,284 736,236 753,236", 0.40, 0.56),
    ])
    b = [
        box(20, 162, 150, 82, "New issue", ["read from GitHub,", "never written back"], t),
        box(200, 138, 175, 128, "Guard", ["redact secrets and", "paths; fence and", "datamark the text"], t, mono="guard.py"),
        box(410, 34, 310, 140, "Assess · 1 Gemini call", ["few-shot: 5 most similar labelled issues",
            "enum-constrained JSON output:", "labels + missing-info items"], t, mono="classify.py"),
        box(410, 204, 310, 160, "Duplicates · 2 Gemini calls", ["expand → 3 root-cause search queries",
            "search → own top 8 ∪ queries' top 8", "(BM25 + embeddings, fused by RRF)",
            "verify → which are the same problem?"], t, mono="dedupe.py"),
        box(755, 104, 205, 196, "Report", ["policy check first:", "flagged → a human only",
            "suggested labels", "for review: missing", "info, duplicates", "reply only at ≥ 70%"], t,
            mono="policy.py", kind="good"),
        *arrows,
        text(490, 392, "≈ $0.0015 and 3.3 s per issue  ·  read-only shadow run, scored daily against maintainers",
             t, size=12.5, color="muted", anchor="middle"),
        *pkts,
    ]
    return svg(980, 410, "\n".join(b), t,
               "pytest-triage pipeline: a new issue is read from GitHub and passed through a guard that redacts "
               "secrets and paths and fences and datamarks the text as untrusted. One Gemini call assesses labels and missing information "
               "using the five most similar labelled issues as examples. Two Gemini calls find duplicates: expand "
               "into three root-cause queries, search the issue's own top 8 plus the queries' top 8 with BM25 and "
               "embeddings fused by RRF, then verify. A policy check routes flagged issues to a human; otherwise the "
               "report shows suggested labels, items for maintainer review, and a reply draft only for outputs at 70% "
               "precision or better. About $0.0015 and 3.3 seconds per issue, run daily in read-only shadow mode.",
               style=MOTION_CSS, margin=40,
               inner=hoppers(t, [(20, 162, 150, 82), (200, 138, 175, 128), (410, 34, 310, 140), (410, 204, 310, 160), (755, 104, 205, 196)], [("accent", 0.0), ("warm", 0.5)]))


# ---------------------------------------------------------------- ask the filings
def filings(t):
    q = [(20, 120), (156, 165), (337, 115), (468, 160), (644, 160), (820, 136)]     # query row: (x, width)
    hops = [("M170,86 L208,86", 0.02, 0.08), ("M360,86 L398,86", 0.09, 0.15),
            ("M550,86 L588,86", 0.16, 0.22), ("M740,86 L778,86", 0.23, 0.29),
            ("M870,126 L870,150 L238,150 L238,194", 0.32, 0.46)]
    for i in range(len(q) - 1):
        x0 = q[i][0] + q[i][1]
        hops.append((f"M{x0},242 L{q[i + 1][0] - 2},242", 0.38 + 0.07 * i if i else 0.40, 0.42 + 0.07 * i if i else 0.44))
    arrows, pkts = flow(t, 7.5, hops)
    b = [
        text(20, 32, "INGEST · run once", t, size=11.5, color="accent", weight=600, font=MONO, spacing=1),
        box(20, 46, 150, 80, "EDGAR 10-K", ["filing HTML from", "the SEC website"], t),
        box(210, 46, 150, 80, "Clean", ["tables become", "label | value rows"], t),
        box(400, 46, 150, 80, "Chunk", ["400 words, tagged", "with its 10-K Item"], t),
        box(590, 46, 150, 80, "Embed", ["bge-small,", "runs locally"], t),
        box(780, 46, 180, 80, "Postgres", ["pgvector embeddings", "+ full-text index"], t),
        text(20, 182, "QUERY · per question", t, size=11.5, color="accent", weight=600, font=MONO, spacing=1),
        box(*q[0][:1], 196, q[0][1], 92, "Question", ["detects the", "company named"], t),
        box(q[1][0], 196, q[1][1], 92, "Retrieve", ["dense: pgvector", "keyword: full-text"], t),
        box(q[2][0], 196, q[2][1], 92, "Fuse", ["RRF merge of", "both lists"], t),
        box(q[3][0], 196, q[3][1], 92, "Rerank", ["bge-reranker-base", "top 30 → top 8"], t),
        box(q[4][0], 196, q[4][1], 92, "Gemini", ["JSON: answerable,", "answer, citations"], t),
        box(q[5][0], 196, q[5][1], 92, "Cited answer", ["or “not in the", "excerpts”"], t, kind="good"),
        *arrows,
        label(560, 145, "both indexes queried for every question", t),
        text(490, 326, "Hybrid + reranker: recall@8 0.92  ·  57 of 60 answers correct  ·  $0.007 and 4.8 s per question",
             t, size=12.5, color="muted", anchor="middle"),
        text(490, 346, "60 questions over 10 companies' 10-Ks, graded by Gemini. Only the final Gemini call costs money.",
             t, size=12.5, color="muted", anchor="middle"),
        *pkts,
    ]
    return svg(980, 366, "\n".join(b), t,
               "Ask the Filings: ingestion downloads 10-K filing HTML from SEC EDGAR, flattens tables to label and "
               "value rows, cuts 400-word chunks tagged with their 10-K Item, embeds them locally with bge-small and "
               "stores them in Postgres with pgvector and a full-text index. For each question it detects the company "
               "named, runs dense and keyword search, merges them with Reciprocal Rank Fusion, reranks the top 30 with "
               "a local bge-reranker-base and sends the top 8 to Gemini, which answers in JSON with citations or says "
               "the answer is not in the excerpts. Hybrid plus reranker: recall at 8 of 0.92 and 57 of 60 answers "
               "correct, at $0.007 and 4.8 seconds per question.",
               style=MOTION_CSS, margin=40,
               inner=hoppers(t, [(20, 46, 150, 80), (210, 46, 150, 80), (400, 46, 150, 80), (590, 46, 150, 80),
                                 (780, 46, 180, 80), (820, 196, 136, 92), (644, 196, 160, 92), (468, 196, 160, 92),
                                 (337, 196, 115, 92), (156, 196, 165, 92)], [("accent", 0.0), ("good", 0.5)]))


# ---------------------------------------------------------------- syncscribe
def syncscribe(t):
    hops = [("M310,110 L343,110", 0.02, 0.14), ("M635,110 L668,110", 0.16, 0.28),
            ("M165,244 L165,280 L815,280 L815,246", 0.36, 0.72)]
    pkts = [packet(d, t, a, b, 5) for d, a, b in hops]
    b = [
        box(20, 44, 290, 200, "Browser", ["Next.js 14 app", "Lexical rich-text editor",
            "presence avatars and live cursors", "inline comment threads",
            "share modal: editor or viewer"], t, mono="components/"),
        box(345, 44, 290, 200, "Next.js server", ["Clerk sign-in",
            "/api/liveblocks-auth: identify the", "user, return a session token",
            "server actions: create room,", "share, change access"], t, mono="room:write | room:read"),
        box(670, 44, 290, 200, "Liveblocks", ["one room per document",
            "shared document state", "presence and comments",
            "per-user room access", "notifications"], t, mono="@liveblocks/react-lexical"),
        arrow("M310,110 L343,110", t, both=True),
        arrow("M635,110 L668,110", t, both=True),
        label(327, 98, "auth", t), label(652, 98, "API", t),
        arrow("M165,244 L165,280 L815,280 L815,246", t, both=True),
        label(490, 300, "WebSocket, real time: edits, cursors, comments", t),
        *pkts,
    ]
    return svg(980, 320, "\n".join(b), t,
               "SyncScribe: the browser runs a Next.js 14 app with a Lexical editor, live cursors, presence and "
               "comment threads. The Next.js server handles Clerk sign-in, identifies the user to Liveblocks through "
               "/api/liveblocks-auth and uses server actions to create rooms and set per-user write or read access. "
               "Liveblocks keeps one room per document with shared state, presence, comments and notifications, and "
               "syncs edits, cursors and comments with the browser over a WebSocket in real time.",
               style=MOTION_CSS, margin=40,
               inner=hoppers(t, [(20, 44, 290, 200), (345, 44, 290, 200), (670, 44, 290, 200)], [("warm", 0.0), ("good", 0.5)]))


# ---------------------------------------------------------------- contribution field
# Modelled on SahajIVVIX-1's "contribution field": stats on top, one cell per day below.
# Empty days glow as a light sweeps across the year; the busiest day pulses.
import datetime as _dt
import json as _json


def _streaks(days):
    longest = run = 0
    for _, n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    for _, n in reversed(days[:-1] if days and not days[-1][1] else days):
        if not n:
            break
        current += 1
    return longest, current


def activity(t):
    data = _json.load(open(ARGS.contrib))
    weeks = data["weeks"]
    days = [d for w in weeks for d in w]
    active = sum(1 for _, n in days if n)
    longest, current = _streaks(days)
    top_date, top_n = max(days, key=lambda d: d[1])
    top_label = _dt.date.fromisoformat(top_date).strftime("%a %d %b %Y")
    peak = max(top_n, 1)

    def level(n):
        return 0 if n == 0 else min(4, 1 + int(3 * (n - 1) / max(peak - 1, 1)))

    sweep, step = 7.0, 0.05
    style = PHONE_CSS + f"""
  .e{{animation:glow {sweep}s linear infinite}}
  @keyframes glow{{ 0%{{fill:{t['cells'][0]}}} 3%{{fill:{t['glow']}}} 9%,100%{{fill:{t['cells'][0]}}} }}
  .top{{transform-box:fill-box;transform-origin:center;animation:top 1.8s ease-out infinite}}
  @keyframes top{{ 0%{{transform:scale(1);opacity:.9}} 100%{{transform:scale(2.4);opacity:0}} }}
  @media (prefers-reduced-motion: reduce){{ .e,.top{{animation:none}} .top{{opacity:0}} }}
"""
    stats = [("CONTRIBUTIONS", f"{data['total']:,}", "last 12 months"),
             ("ACTIVE DAYS", f"{active}", "in the last 12 months"),
             ("LONGEST STREAK", f"{longest}", "days in a row"),
             ("CURRENT STREAK", f"{current}", "days and counting" if current else "start one today"),
             ("BUSIEST DAY", f"{top_n}", top_label)]
    d = ['<g class="dt">',
         text(40, 44, "CONTRIBUTION FIELD", t, size=14, color="accent", weight=600, font=MONO, spacing=1.5),
         text(1160, 44, "one cell per day · empty days glow as the light passes", t, size=13, color="muted",
              font=MONO, anchor="end")]
    for i, (k, v, sub) in enumerate(stats):
        x = 40 + i * 226
        if i:
            d.append(f'<line x1="{x - 16}" y1="70" x2="{x - 16}" y2="150" stroke="{t["border"]}"/>')
        d.append(text(x, 88, k, t, size=11.5, color="muted", weight=600, font=MONO, spacing=1.2))
        d.append(text(x, 126, v, t, size=34, weight=700))
        d.append(text(x, 148, sub, t, size=13, color="muted"))
    gx, gy, cell, gap = 84, 202, 16, 4
    pitch = cell + gap
    last_month = None
    for c, week in enumerate(weeks):
        month = week[0][0][:7]
        if month != last_month and c < len(weeks) - 1:
            if last_month is not None or week[0][0][8:] <= "07":
                name = _dt.date.fromisoformat(week[0][0]).strftime("%b")
                d.append(text(gx + c * pitch, gy - 10, name, t, size=12, color="muted", font=MONO))
            last_month = month
        first_dow = (_dt.date.fromisoformat(week[0][0]).weekday() + 1) % 7      # Sunday = 0
        for r, (date, n) in enumerate(week):
            y = gy + (first_dow + r if c == 0 else r) * pitch
            x = gx + c * pitch
            lv = level(n)
            cls = ' class="e" style="animation-delay:%.2fs"' % (c * step) if lv == 0 else ""
            d.append(f'<rect{cls} x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{t["cells"][lv]}">'
                     f'<title>{date}: {n} contribution{"s" if n != 1 else ""}</title></rect>')
            if date == top_date and n:
                d.append(f'<rect class="top" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="none" '
                         f'stroke="{t["accent"]}" stroke-width="2"/>')
    for r, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        d.append(text(40, gy + r * pitch + 12, name, t, size=12, color="muted", font=MONO))
    ly = gy + 7 * pitch + 26
    d.append(text(40, ly + 12, "pulsing cell = busiest day", t, size=12, color="muted", font=MONO))
    lx = 1160 - 5 * pitch - 40
    d.append(text(lx - 10, ly + 12, "less", t, size=12, color="muted", font=MONO, anchor="end"))
    for i in range(5):
        d.append(f'<rect x="{lx + i * pitch}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{t["cells"][i]}"/>')
    d.append(text(lx + 5 * pitch + 6, ly + 12, "more", t, size=12, color="muted", font=MONO))
    d.append("</g>")
    H = ly + 40
    p = ['<g class="ph">', text(40, 70, "CONTRIBUTIONS", t, size=34, color="accent", weight=600, font=MONO, spacing=2)]
    for i, (k, v, sub) in enumerate([("last 12 months", f"{data['total']:,}", ""), ("active days", f"{active}", ""),
                                     ("longest streak", f"{longest}", "")]):
        x = 40 + i * 380
        p.append(text(x, 230, v, t, size=110, weight=700))
        p.append(text(x, 300, k, t, size=36, color="muted"))
    p.append("</g>")
    alt = (f"Contribution field: {data['total']} GitHub contributions in the last 12 months, {active} active days, "
           f"longest streak {longest} days, current streak {current} days, busiest day {top_label} with {top_n}.")
    return svg(1200, H, "\n".join(d + p), t, alt, style=style, margin=HERO_MARGIN)


ONLY = set(ARGS.only.split(",")) if ARGS.only else None
for name, fn in [("hero", hero), ("impact", impact), ("triage", triage), ("filings", filings),
                 ("syncscribe", syncscribe), ("activity", activity)]:
    if name == "activity" and not ARGS.contrib:
        continue
    if ONLY and name not in ONLY:
        continue
    for theme, t in THEMES.items():
        with open(os.path.join(OUT, f"{name}-{theme}.svg"), "w") as f:
            f.write(fn(t))
for theme, t in THEMES.items() if not ONLY else ():
    for key, label, primary in BUTTONS:
        with open(os.path.join(OUT, f"btn-{key}-{theme}.svg"), "w") as f:
            f.write(button(t, label, primary))
    for i, (key, num, title, tag) in enumerate(SECTIONS):
        with open(os.path.join(OUT, f"h-{key}-{theme}.svg"), "w") as f:
            f.write(header(t, num, title, tag, HEADER_COLOURS[i % len(HEADER_COLOURS)], i))
print("ok")
