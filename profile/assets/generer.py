"""Images animées du profil de l'orga Shazanny (profile/README.md).

    pip install fonttools pillow
    python assets/generer.py

- SVG autonomes : GitHub n'y charge ni image ni police externe. Les photos GitHub sont intégrées en
  JPEG, les textes du logo convertis en tracés (police Fredoka, licence OFL).
- Icônes Lucide (ISC) et Simple Icons (CC0), versions figées (voir assets/CREDITS.md).
- Animations en CSS, figées sur leur état final si le lecteur demande moins d'animations.
"""

from __future__ import annotations

import base64
import functools
import io
import json
import math
import pathlib
import random
import re
import urllib.request
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image

OUT = pathlib.Path(__file__).resolve().parent
CACHE = OUT / ".cache"
FREDOKA_URL = "https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf"
LUCIDE = "https://cdn.jsdelivr.net/npm/lucide-static@1.64.0/icons/{}.svg"
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/{}.svg"

BG, CARD, LINE = "#0c0c0e", "#131317", "#2c2c33"
TEXT, MUTED = "#f2f2f4", "#a3a3ad"
PINK, BLUE, RED = "#ff4f8b", "#3b82f6", "#ef4444"
FONT = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'Cascadia Code', Consolas, 'SF Mono', Menlo, monospace"

# Dans l'ordre du nom : SHA + ZA + NNY.
MEMBERS = [
    {"id": "shaleena", "name": "Shaleena", "github": "shalee-pnt", "color": PINK, "syl": "SHA", "rest": ("", "LEENA"),
     "vibe": "rap FR · indie · électro", "icon": "headphones"},
    {"id": "hamza", "name": "Hamza", "github": "CodeByHaamza", "color": BLUE, "syl": "ZA", "rest": ("HAM", ""),
     "vibe": "rap · pop", "icon": "mic-vocal"},
    {"id": "lenny", "name": "Lenny", "github": "lennymgrd", "color": RED, "syl": "NNY", "rest": ("LE", ""),
     "vibe": "metal · rock alternatif", "icon": "guitar"},
]

# ---------------------------------------------------------------------------
# Outils


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "shazanny-profil"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def avatar(github: str, size: int = 220) -> str:
    """Photo GitHub du compte, carrée, en JPEG intégré."""
    user = json.loads(fetch(f"https://api.github.com/users/{github}"))
    img = Image.open(io.BytesIO(fetch(f"{user['avatar_url']}&s={size * 2}"))).convert("RGB")
    side = min(img.size)
    img = img.crop(((img.width - side) // 2, (img.height - side) // 2, (img.width + side) // 2, (img.height + side) // 2))
    buf = io.BytesIO()
    img.resize((size, size), Image.LANCZOS).save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


@functools.cache
def fredoka() -> TTFont:
    path = CACHE / "Fredoka.ttf"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch(FREDOKA_URL))
    return instancer.instantiateVariableFont(TTFont(str(path)), {"wght": 700, "wdth": 100})


def text_path(s: str, size: float) -> tuple[str, float]:
    """Tracé du texte en Fredoka (origine : ligne de base, à gauche) et sa largeur."""
    font = fredoka()
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
    k = size / font["head"].unitsPerEm
    pen, x = SVGPathPen(glyphs), 0.0
    for ch in s:
        name = cmap.get(ord(ch))
        if name:
            glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, x, 0)))
            x += glyphs[name].width * k
    return pen.getCommands(), x


@functools.cache
def lucide(name: str) -> str:
    svg = re.sub(r"<!--.*?-->", "", fetch(LUCIDE.format(name)).decode("utf-8"), flags=re.S)
    inner = svg[svg.index(">", svg.index("<svg")) + 1 : svg.rindex("</svg>")]
    return re.sub(r">\s+<", "><", re.sub(r"\s+", " ", inner)).strip()


@functools.cache
def brand_path(slug: str) -> str:
    svg = fetch(SIMPLE_ICONS.format(slug)).decode("utf-8")
    start = svg.index(' d="') + 4
    return svg[start : svg.index('"', start)]


def icon(name: str, cx: float, cy: float, size: float, color: str, width: float = 2, cls: str = "", style: str = "") -> str:
    k = size / 24
    inner = (
        f'<g transform="translate({cx - size / 2:.1f} {cy - size / 2:.1f}) scale({k:.4f})" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{lucide(name)}</g>'
    )
    if not cls:
        return inner
    return f'<g class="{cls}"' + (f' style="{style}"' if style else "") + f">{inner}</g>"


def brand(slug: str, cx: float, cy: float, size: float, color: str) -> str:
    k = size / 24
    return f'<path d="{brand_path(slug)}" transform="translate({cx - size / 2:.1f} {cy - size / 2:.1f}) scale({k:.4f})" fill="{color}"/>'


def text(x: float, y: float, s: str, size: float = 18, color: str = TEXT, weight: int = 400, anchor: str = "start", font: str = FONT) -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(s)}</text>'


def svg(W: int, H: int, title: str, desc: str, css: str, body: str, reduced: str = "", card: bool = True) -> str:
    bg = (
        f'<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>\n<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="24" fill="none" stroke="{LINE}"/>'
        if card else ""
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">{escape(title)}</title>
<desc id="d">{escape(desc)}</desc>
<style>
{css}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} {reduced} }}
</style>
{bg}
{body}
</svg>
"""


def appear(name: str, at: float, end: float = 95, hidden: str = "opacity: 0", shown: str = "opacity: 1", dur: float = 3) -> str:
    return f"@keyframes {name} {{ 0%, {at:.2f}% {{ {hidden}; }} {at + dur:.2f}%, {end:.2f}% {{ {shown}; }} 100% {{ {hidden}; }} }}"


# ---------------------------------------------------------------------------
# Le S : haut (Shaleena), milieu (Hamza), bas (Lenny).


def arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    return f"A{r} {r} 0 {1 if abs(a1 - a0) > 180 else 0} {1 if a1 > a0 else 0} {x1:.2f} {y1:.2f}"


def pt(cx: float, cy: float, r: float, a: float) -> tuple[float, float]:
    return cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))


def s_mark(cx: float = 256, cy: float = 256, r: float = 88, stroke: float = 64, cls: tuple[str, str, str] = ("", "", "")) -> str:
    top, bot, gap = (cx, cy - r), (cx, cy + r), 5
    parts = [
        (PINK, pt(*top, r, -38), arc(*top, r, -38, -180 + gap)),
        (BLUE, pt(*top, r, -180), arc(*top, r, -180, -270) + arc(*bot, r, -90, -gap)),
        (RED, pt(*bot, r, gap / 2), arc(*bot, r, gap / 2, 142)),
    ]
    out = []
    for (color, (sx, sy), d), c in zip(parts, cls):
        attr = f' class="{c}"' if c else ""
        out.append(f'<path{attr} d="M{sx:.2f} {sy:.2f}{d}" fill="none" stroke="{color}" stroke-width="{stroke}" pathLength="100"/>')
    (hx, hy), (tx, ty) = pt(*top, r, -38), pt(*bot, r, 142)
    c0 = f' class="{cls[0]}e"' if cls[0] else ""
    c2 = f' class="{cls[2]}e"' if cls[2] else ""
    out.insert(0, f'<circle{c0} cx="{hx:.2f}" cy="{hy:.2f}" r="{stroke / 2}" fill="{PINK}"/>')
    out.append(f'<circle{c2} cx="{tx:.2f}" cy="{ty:.2f}" r="{stroke / 2}" fill="{RED}"/>')
    return "".join(out)


# ---------------------------------------------------------------------------
# Bannière : les trois prénoms se fondent en SHAZANNY, le S se dessine, des icônes montent derrière.

FLOATING = ["code", "gamepad-2", "music", "sparkles", "rocket", "heart", "headphones", "terminal", "zap", "star", "git-branch", "coffee"]


def banniere() -> str:
    W, H = 1200, 400
    C = "10s"
    size = 92
    rnd = random.Random(3)
    colors = [m["color"] for m in MEMBERS]
    css = [
        "  .float { transform-box: fill-box; transform-origin: center; animation-name: float; animation-timing-function: linear; animation-iteration-count: infinite; opacity: 0; }",
        "  @keyframes float { 0% { opacity: 0; transform: translateY(0) rotate(-10deg); } 15% { opacity: .5; } 85% { opacity: .2; } 100% { opacity: 0; transform: translateY(-220px) rotate(14deg); } }",
        f"  .fade {{ animation: fade {C} ease-in-out infinite; }}",
        "  @keyframes fade { 0%, 20% { opacity: 1; } 30%, 100% { opacity: 0; } }",
        f"  .tag {{ animation: tag {C} ease-out infinite; }}",
        "  " + appear("tag", 72, 96, dur=5),
    ]
    body = [
        '<defs>'
        + "".join(
            f'<radialGradient id="g{i}" cx="{cx}" cy="50%" r="45%"><stop offset="0" stop-color="{c}" stop-opacity=".22"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>'
            for i, (cx, c) in enumerate(zip(("15%", "50%", "85%"), colors))
        )
        + f'<clipPath id="card"><rect width="{W}" height="{H}" rx="24"/></clipPath></defs>',
        '<g clip-path="url(#card)">' + "".join(f'<rect width="{W}" height="{H}" fill="url(#g{i})"/>' for i in range(3)),
    ]
    for i in range(22):
        x, y = rnd.uniform(40, W - 40), rnd.uniform(260, 380)
        body.append(icon(FLOATING[i % len(FLOATING)], x, y, rnd.uniform(18, 30), colors[i % 3], 2, "float",
                         f"animation-duration:{rnd.uniform(7, 12):.1f}s;animation-delay:{-rnd.uniform(0, 12):.1f}s"))
    body.append("</g>")
    # Les prénoms, empilés au départ.
    widths = []
    for m in MEMBERS:
        before, after = m["rest"]
        widths.append(tuple(text_path(s, size)[1] if s else 0 for s in (before, m["syl"], after)))
    block = max(sum(w) for w in widths)
    sx0, ys = (W - block) / 2, [112, 204, 296]
    mark_k = 0.36
    mark_w, gap = 240 * mark_k, 34
    total = sum(w[1] for w in widths)
    ex, ey = (W - mark_w - gap - total) / 2 + mark_w + gap, 214
    mark_cx = ex - gap - mark_w / 2
    for k, (m, (wb, ws, wa)) in enumerate(zip(MEMBERS, widths)):
        before, after = m["rest"]
        x_start = sx0 + wb
        dx, dy = ex - x_start, ey - ys[k]
        css += [
            f"  .m{k} {{ transform: translate({dx:.1f}px, {dy:.1f}px); animation: m{k} {C} cubic-bezier(.6,0,.2,1) infinite; }}",
            f"  @keyframes m{k} {{ 0%, {28 + k * 3}% {{ transform: none; }} {46 + k * 3}%, 96% {{ transform: translate({dx:.1f}px, {dy:.1f}px); }} 100% {{ transform: none; }} }}",
        ]
        if before:
            body.append(f'<g class="fade"><path d="{text_path(before, size)[0]}" transform="translate({sx0:.1f} {ys[k]})" fill="#4a4a55"/></g>')
        if after:
            body.append(f'<g class="fade"><path d="{text_path(after, size)[0]}" transform="translate({x_start + ws:.1f} {ys[k]})" fill="#4a4a55"/></g>')
        body.append(f'<g class="m{k}"><path d="{text_path(m["syl"], size)[0]}" transform="translate({x_start:.1f} {ys[k]})" fill="{m["color"]}"/></g>')
        ex += ws
    for k in range(3):
        at = 54 + k * 6
        css += [
            f"  .d{k} {{ stroke-dasharray: 100; animation: d{k} {C} ease-in-out infinite; }}",
            f"  @keyframes d{k} {{ 0%, {at}% {{ stroke-dashoffset: 100; }} {at + 7}%, 96% {{ stroke-dashoffset: 0; }} 100% {{ stroke-dashoffset: 100; }} }}",
            f"  .d{k}e {{ animation: d{k}e {C} linear infinite; }}",
            "  " + appear(f"d{k}e", at if k == 0 else at + 7, 96, dur=1),
        ]
    body.append(f'<g transform="translate({mark_cx - 256 * mark_k:.1f} {ey - 33 - 256 * mark_k:.1f}) scale({mark_k})">{s_mark(cls=("d0", "d1", "d2"))}</g>')
    body.append(f'<g class="tag">{text(W / 2, 312, "Shaleena · Hamza · Lenny", 26, MUTED, 600, "middle")}'
                f'{text(W / 2, 350, "trois potes, des projets fun, beaucoup trop de musique", 20, TEXT, 400, "middle")}</g>')
    return svg(W, H, "Shazanny",
               "SHA de Shaleena, ZA de Hamza et NNY de Lenny se détachent des prénoms et se rejoignent en SHAZANNY, puis un S en trois couleurs se dessine : trois potes, des projets fun, beaucoup trop de musique.",
               "\n".join(css), "\n".join(body), ".fade { opacity: 0; } .tag { opacity: 1; }")


# ---------------------------------------------------------------------------
# Une carte par membre : photo, anneau et orbite à sa couleur, sa syllabe du nom.


def carte(i: int, m: dict) -> str:
    W, H = 400, 500
    c = m["color"]
    photo = avatar(m["github"], 200)
    syl_d, syl_w = text_path(m["syl"], 210)
    name_d, name_w = text_path(m["name"], 46)
    cx, cy = 200, 182
    delay = -i * 1.3
    rnd = random.Random(10 + i)
    css = [
        f"  .orbit {{ transform-box: view-box; transform-origin: {cx}px {cy}px; animation: spin 14s linear {delay:.1f}s infinite; }}",
        f"  .orbit2 {{ transform-box: view-box; transform-origin: {cx}px {cy}px; animation: spin 9s linear {delay:.1f}s infinite reverse; }}",
        "  @keyframes spin { to { transform: rotate(360deg); } }",
        "  .pulse { transform-box: fill-box; transform-origin: center; animation: pulse 2.4s ease-in-out infinite; }",
        "  @keyframes pulse { 0%, 100% { opacity: .55; } 50% { opacity: 1; } }",
        "  .bob { transform-box: fill-box; transform-origin: center; animation-name: bob; animation-timing-function: ease-in-out; animation-iteration-count: infinite; }",
        "  @keyframes bob { 0%, 100% { transform: translateY(4px) rotate(-8deg); } 50% { transform: translateY(-6px) rotate(8deg); } }",
        "  .wm { opacity: .1; animation: wm 6s ease-in-out infinite; }",
        "  @keyframes wm { 0%, 100% { opacity: .07; } 50% { opacity: .13; } }",
    ]
    sparks = []
    for k, (name, x, y) in enumerate([("sparkles", 72, 92), ("music", 330, 110), ("star", 318, 262), ("code", 80, 270)]):
        sparks.append(icon(name, x, y, rnd.uniform(22, 30), c, 2, "bob", f"animation-duration:{rnd.uniform(2.6, 4):.1f}s;animation-delay:{-k * 0.7:.1f}s"))
    body = [
        f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="28" fill="{CARD}" stroke="{c}" stroke-width="2.5"/>',
        f'<clipPath id="cl{i}"><rect x="2" y="2" width="{W - 4}" height="{H - 4}" rx="28"/></clipPath>',
        f'<g clip-path="url(#cl{i})"><g class="wm"><path d="{syl_d}" transform="translate({W - syl_w + 30:.1f} 200)" fill="{c}"/></g></g>',
        f'<g class="orbit"><circle cx="{cx}" cy="{cy}" r="122" fill="none" stroke="{c}" stroke-opacity=".45" stroke-width="2" stroke-dasharray="2 9" stroke-linecap="round"/>'
        f'<circle cx="{cx + 122}" cy="{cy}" r="7" fill="{c}"/></g>',
        f'<g class="orbit2"><circle cx="{cx}" cy="{cy - 108}" r="4.5" fill="{TEXT}"/></g>',
        f'<clipPath id="ph{i}"><circle cx="{cx}" cy="{cy}" r="96"/></clipPath>',
        f'<image href="{photo}" x="{cx - 96}" y="{cy - 96}" width="192" height="192" clip-path="url(#ph{i})"/>',
        f'<circle cx="{cx}" cy="{cy}" r="100" fill="none" stroke="{c}" stroke-width="7"/>',
        "".join(sparks),
        f'<path d="{name_d}" transform="translate({cx - name_w / 2:.1f} 362)" fill="{TEXT}"/>',
        text(cx, 394, "@" + m["github"], 17, MUTED, 400, "middle", MONO),
    ]
    # Pastille : sa syllabe dans SHAZANNY.
    word = "".join(x["syl"] for x in MEMBERS)
    parts_d = []
    x = 0.0
    for other in MEMBERS:
        d, w = text_path(other["syl"], 22)
        parts_d.append((d, x, other is m))
        x += w
    pw = x + 36
    px = cx - pw / 2
    body.append(f'<rect x="{px:.1f}" y="414" width="{pw:.1f}" height="36" rx="18" fill="{BG}" stroke="{LINE}" stroke-width="1.5"/>')
    for d, ox, mine in parts_d:
        attr = ' class="pulse"' if mine else ""
        body.append(f'<path{attr} d="{d}" transform="translate({px + 18 + ox:.1f} 440)" fill="{c if mine else "#4a4a55"}"/>')
    body.append(icon(m["icon"], cx - len(m["vibe"]) * 4.3 - 6, 474, 18, c, 2))
    body.append(text(cx + 10, 480, m["vibe"], 16, MUTED, 400, "middle"))
    return svg(W, H, f"{m['name']} (@{m['github']})",
               f"{m['name']}, @{m['github']} : le {m['syl']} de {word}. Style : {m['vibe']}.",
               "\n".join(css), "\n".join(body), card=False)


# ---------------------------------------------------------------------------
# Prochain projet : des idées qui s'allument, trois points qui tapent.


def prochain() -> str:
    W, H = 1200, 220
    colors = [m["color"] for m in MEMBERS]
    d, w = text_path("PROCHAIN PROJET", 54)
    css = [
        "  .dot { animation: dot 1.4s ease-in-out infinite; }",
        "  @keyframes dot { 0%, 60%, 100% { transform: translateY(0); opacity: .35; } 30% { transform: translateY(-10px); opacity: 1; } }",
        "  .idea { transform-box: fill-box; transform-origin: center bottom; animation: idea 4.2s ease-in-out infinite; }",
        "  @keyframes idea { 0%, 100% { opacity: .25; transform: scale(.92); } 20%, 40% { opacity: 1; transform: scale(1.08) rotate(-6deg); } }",
        "  .blink { animation: blink 1s steps(1) infinite; }",
        "  @keyframes blink { 50% { opacity: 0; } }",
    ]
    x0 = (W - w) / 2
    body = [
        f'<path d="{d}" transform="translate({x0:.1f} 104)" fill="{TEXT}"/>',
        f'<rect class="blink" x="{x0 + w + 10:.1f}" y="62" width="8" height="46" rx="2" fill="{PINK}"/>',
        text(W / 2, 150, "en plein brainstorm… on vous dit bientôt", 20, MUTED, 400, "middle"),
    ]
    for k, c in enumerate(colors):
        body.append(f'<g transform="translate({W / 2 - 30 + k * 30} 186)"><circle class="dot" r="8" fill="{c}" style="animation-delay:{k * 0.18:.2f}s"/></g>')
    for k, (x, c) in enumerate(zip((120, 1080, 230, 970), colors + [PINK])):
        body.append(icon("lightbulb", x, 112, 56 if k < 2 else 38, c, 1.8, "idea", f"animation-delay:{-k * 1.05:.2f}s"))
    return svg(W, H, "Prochain projet", "Prochain projet : en plein brainstorm, on vous dit bientôt.", "\n".join(css), "\n".join(body))


# ---------------------------------------------------------------------------
# Ce qu'on utilise : une tuile par techno, qui saute à tour de rôle.

STACK = [
    ("typescript", "TypeScript", "#3178c6"), ("javascript", "JavaScript", "#f7df1e"), ("python", "Python", "#4b8bbe"),
    ("react", "React", "#61dafb"), ("nextdotjs", "Next.js", "#ffffff"), ("nodedotjs", "Node.js", "#5fa04e"),
    ("tailwindcss", "Tailwind", "#06b6d4"), ("html5", "HTML", "#e34f26"), ("git", "Git", "#f05032"),
]


def stack() -> str:
    W, H = 1200, 190
    slot = (W - 80) / len(STACK)
    tile = 84
    colors = [m["color"] for m in MEMBERS]
    css = [
        "  .hop { transform-box: fill-box; transform-origin: center bottom; animation: hop 2.6s ease-out infinite; }",
        "  .lit { opacity: 0; animation: lit 2.6s ease-out infinite; }",
        "  @keyframes hop { 0%, 22%, 100% { transform: none; } 7% { transform: translateY(-9px) scale(1.05); } 14% { transform: translateY(1px); } }",
        "  @keyframes lit { 0%, 30%, 100% { opacity: 0; } 6% { opacity: 1; } }",
    ]
    body = []
    for i, (slug, name, color) in enumerate(STACK):
        cx = 40 + slot * (i + 0.5)
        x, y = cx - tile / 2, 36
        st = f"animation-delay:{i * 0.13:.2f}s"
        body.append(f"""<g class="hop" style="{st}">
  <rect x="{x:.1f}" y="{y}" width="{tile}" height="{tile}" rx="20" fill="#16161a" stroke="{LINE}" stroke-width="2"/>
  <rect class="lit" style="{st}" x="{x:.1f}" y="{y}" width="{tile}" height="{tile}" rx="20" fill="{colors[i % 3]}" fill-opacity=".1" stroke="{colors[i % 3]}" stroke-width="2.5"/>
  {brand(slug, cx, y + tile / 2, 44, color)}
</g>
{text(cx, y + tile + 32, name, 16, TEXT, 700, "middle")}""")
    return svg(W, H, "Ce qu'on utilise", "TypeScript, JavaScript, Python, React, Next.js, Node.js, Tailwind, HTML et Git.", "\n".join(css), "\n".join(body))


# ---------------------------------------------------------------------------
# Pied de page : un égaliseur aux trois couleurs.


def pied() -> str:
    W, H = 1200, 120
    rnd = random.Random(5)
    colors = [m["color"] for m in MEMBERS]
    n = 60
    bars = []
    for i in range(n):
        bx = 40 + i * (W - 80) / n
        bars.append(
            f'<rect class="eq" x="{bx:.1f}" y="30" width="{(W - 80) / n - 6:.1f}" height="60" rx="3" fill="{colors[i * 3 // n]}" '
            f'style="animation-duration:{rnd.uniform(0.7, 1.6):.2f}s;animation-delay:{-rnd.uniform(0, 1.5):.2f}s"/>'
        )
    css = [
        "  .eq { transform-box: fill-box; transform-origin: center; animation: eq 1s ease-in-out infinite alternate; }",
        "  @keyframes eq { from { transform: scaleY(.12); } to { transform: scaleY(1); } }",
    ]
    return svg(W, H, "Égaliseur", "Un égaliseur aux couleurs de Shaleena, Hamza et Lenny.", "\n".join(css), "".join(bars), card=False)


# ---------------------------------------------------------------------------


def main() -> None:
    files = {
        OUT / "banniere.svg": banniere(),
        OUT / "projets" / "prochain.svg": prochain(),
        OUT / "stack.svg": stack(),
        OUT / "pied.svg": pied(),
    }
    for i, m in enumerate(MEMBERS):
        files[OUT / "membres" / f"{m['id']}.svg"] = carte(i, m)
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"{path.relative_to(OUT)} : {len(content.encode()) // 1024} Ko")


if __name__ == "__main__":
    main()
