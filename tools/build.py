#!/usr/bin/env python3
"""Generates the animated SVGs used in the profile README.

    python3 tools/build.py

No dependencies. Each graphic is a real simulation whose frames or keyframes
are baked into a single SVG, so nothing runs in the browser except CSS.

  hero.svg   a Rubik's cube repeating R U R' U' six times, which returns it to solved
  stack.svg  a 4x3 sliding puzzle, scrambled by a random walk and solved in reverse
  maze.svg   a maze carved by depth-first search and solved by breadth-first search
"""
import math
import random
from collections import deque
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
BG, PANEL, EDGE, INK, SOFT, MUTED = "#0d1117", "#161b22", "#30363d", "#f0f6fc", "#c9d1d9", "#8b949e"
BLUE, GREEN, YELLOW, ORANGE, RED, WHITE = "#58a6ff", "#3fb950", "#f2cc60", "#f0883e", "#f85149", "#f0f6fc"


def n(v):
    """Compact number formatting."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


# ───────────────────────────── hero: Rubik's cube ─────────────────────────────

PSI, PHI = math.radians(38), math.radians(26)
CAM = (math.sin(PSI) * math.cos(PHI), math.sin(PHI), math.cos(PSI) * math.cos(PHI))
RIGHT = (math.cos(PSI), 0.0, -math.sin(PSI))
UP = (CAM[1] * RIGHT[2], CAM[2] * RIGHT[0] - CAM[0] * RIGHT[2], -CAM[1] * RIGHT[0])
LIGHT = (0.25, 0.9, 0.36)

NORMALS = {
    (0, 1, 0): "w", (0, -1, 0): "y",
    (0, 0, 1): "g", (0, 0, -1): "b",
    (1, 0, 0): "r", (-1, 0, 0): "o",
}


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def rot(p, axis, deg):
    if not deg:
        return p
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    if axis == 0:
        return (x, y * c - z * s, y * s + z * c)
    if axis == 1:
        return (x * c + z * s, y, -x * s + z * c)
    return (x * c - y * s, x * s + y * c, z)


def solved_cube():
    cube = []
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            for z in (-1, 0, 1):
                pos = (x, y, z)
                cube.append((pos, {nm: col for nm, col in NORMALS.items() if dot(pos, nm) == 1}))
    return cube


def turn(cube, axis, deg):
    """Quarter-turn the +1 layer on `axis`."""
    snap = lambda v: tuple(int(round(c)) for c in v)
    out = []
    for pos, stickers in cube:
        if pos[axis] == 1:
            pos = snap(rot(pos, axis, deg))
            stickers = {snap(rot(nm, axis, deg)): col for nm, col in stickers.items()}
        out.append((pos, stickers))
    return out


def draw_box(cubies, lo, hi, cx, cy, scale, axis=0, deg=0):
    """Draw a convex slab of cubies. Convex means back-face culling is exact."""
    def project(p):
        p = rot(p, axis, deg)
        return (cx + scale * dot(p, RIGHT), cy - scale * dot(p, UP))

    def quad(points, cls):
        d = "M" + "L".join(f"{n(x)} {n(y)}" for x, y in map(project, points)) + "Z"
        return f'<path class="{cls}" d="{d}"/>'

    def on_face(a, coord, b, vb, c, vc):
        p = [0.0, 0.0, 0.0]
        p[a], p[b], p[c] = coord, vb, vc
        return tuple(p)

    out = []
    for nm in NORMALS:
        turned = rot(nm, axis, deg)
        if dot(turned, CAM) <= 1e-6:
            continue
        a = next(i for i in range(3) if nm[i])
        b, c = [i for i in range(3) if i != a]
        coord = hi[a] if nm[a] > 0 else lo[a]
        out.append(quad([on_face(a, coord, b, vb, c, vc) for vb, vc in
                         ((lo[b], lo[c]), (hi[b], lo[c]), (hi[b], hi[c]), (lo[b], hi[c]))], "k"))
        stickers = []
        for pos, st in cubies:
            if nm in st:
                h = 0.4
                stickers.append(quad([on_face(a, coord, b, pos[b] + sb * h, c, pos[c] + sc * h)
                                      for sb, sc in ((-1, -1), (1, -1), (1, 1), (-1, 1))], st[nm]))
        if stickers:
            shade = 0.6 + 0.4 * max(0.0, dot(turned, LIGHT))
            out.append(f'<g opacity="{min(1.0, shade):.2f}">{"".join(stickers)}</g>')
    return "".join(out)


def build_hero():
    W, H = 840, 420
    cx, cy, scale = 672, 210, 56
    hold, turn_t, pause, steps = 1.6, 0.42, 0.18, 6
    moves = [(0, -90), (1, -90), (0, 90), (1, 90)] * 6   # (R U R' U') x 6
    slot = turn_t + pause
    total = hold + slot * len(moves)
    dt = turn_t / steps
    pct = lambda seconds: f"{(seconds + 0.004) / total * 100:.4f}%"
    ease = lambda t: t * t * (3 - 2 * t)
    full_lo, full_hi = (-1.5, -1.5, -1.5), (1.5, 1.5, 1.5)

    cube = solved_cube()
    solved_markup = draw_box(cube, full_lo, full_hi, cx, cy, scale)
    frames = [f'<g class="fr h">{solved_markup}</g>']
    for i, (axis, deg) in enumerate(moves):
        t0 = hold + i * slot
        rest_hi = list(full_hi); rest_hi[axis] = 0.5
        slab_lo = list(full_lo); slab_lo[axis] = 0.5
        rest = [cb for cb in cube if cb[0][axis] != 1]
        slab = [cb for cb in cube if cb[0][axis] == 1]
        frames.append(f'<g class="fr m" style="animation-delay:{t0:.2f}s">'
                      f'{draw_box(rest, full_lo, rest_hi, cx, cy, scale)}</g>')
        for k in range(1, steps + 1):
            cls = "l" if k == steps else "a"
            frames.append(f'<g class="fr {cls}" style="animation-delay:{t0 + (k - 1) * dt:.2f}s">'
                          f'{draw_box(slab, slab_lo, full_hi, cx, cy, scale, axis, deg * ease(k / steps))}</g>')
        cube = turn(cube, axis, deg)
    assert sorted(map(str, cube)) == sorted(map(str, solved_cube())), "sequence must return to solved"

    phrases = ["CoachClick", "Tomorrow: Daily Calls", "The Tuesday Report", "FORGE", "whatever comes next"]
    each = 2.8
    cycle = each * len(phrases)
    prefix = "$ building "
    rotating = "".join(
        f'<text class="mono ph" x="48" y="332" style="animation-delay:{i * each:.1f}s">'
        f'<tspan fill-opacity="0">{prefix}</tspan><tspan fill="{BLUE}">{p}</tspan><tspan class="cur" fill="{INK}">_</tspan></text>'
        for i, p in enumerate(phrases))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="t d">
<title id="t">Trevor Kist. Marketing technologist turned builder.</title>
<desc id="d">A dark panel with the name Trevor Kist and a terminal line cycling through current projects. Beside it, a Rubik's cube repeats the moves R, U, R prime, U prime six times, which scrambles it and returns it to solved.</desc>
<defs>
<pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#21262d"/></pattern>
<radialGradient id="glow" cx="{cx / W:.3f}" cy=".5" r=".38"><stop offset="0" stop-color="{BLUE}" stop-opacity=".16"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
<linearGradient id="fadeL" x1="0" x2="1"><stop offset="0" stop-color="{BG}"/><stop offset=".55" stop-color="{BG}" stop-opacity=".0"/></linearGradient>
<filter id="blur" x="-30%" y="-200%" width="160%" height="500%"><feGaussianBlur stdDeviation="7"/></filter>
<clipPath id="frame"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13"/></clipPath>
<style>
text {{ font-family: {SANS}; }}
.mono {{ font-family: {MONO}; font-size: 19px; }}
.k {{ fill: #010409; stroke: #010409; stroke-width: 1.5; stroke-linejoin: round; }}
.w, .y, .g, .b, .r, .o {{ fill: currentColor; stroke: currentColor; stroke-width: 4; stroke-linejoin: round; }}
.w {{ color: {WHITE}; }} .y {{ color: {YELLOW}; }} .g {{ color: {GREEN}; }} .b {{ color: {BLUE}; }} .r {{ color: {RED}; }} .o {{ color: {ORANGE}; }}
.fr {{ opacity: 0; animation: {total:.2f}s step-end infinite; }}
.h {{ animation-name: fh; }} .m {{ animation-name: fm; }} .a {{ animation-name: fa; }} .l {{ animation-name: fl; }}
@keyframes fh {{ 0% {{ opacity: 1; }} {pct(hold)}, 100% {{ opacity: 0; }} }}
@keyframes fm {{ 0% {{ opacity: 1; }} {pct(slot)}, 100% {{ opacity: 0; }} }}
@keyframes fa {{ 0% {{ opacity: 1; }} {pct(dt)}, 100% {{ opacity: 0; }} }}
@keyframes fl {{ 0% {{ opacity: 1; }} {pct(dt + pause)}, 100% {{ opacity: 0; }} }}
.ph {{ opacity: 0; animation: ph {cycle:.1f}s linear infinite; }}
@keyframes ph {{ 0% {{ opacity: 0; }} 2% {{ opacity: 1; }} {100 / len(phrases) - 2:.1f}% {{ opacity: 1; }} {100 / len(phrases):.1f}%, 100% {{ opacity: 0; }} }}
.cur {{ animation: blink 1.1s step-end infinite; }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
.in {{ animation: rise .8s cubic-bezier(.2,.8,.2,1) both; }}
@keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }} }}
@media (prefers-reduced-motion: reduce) {{
  .fr, .ph, .cur, .in {{ animation: none; }}
  .h, .ph:first-of-type {{ opacity: 1; }}
}}
</style>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13" fill="{BG}"/>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#dots)"/>
<rect width="{W}" height="{H}" fill="url(#fadeL)"/>
<rect width="{W}" height="{H}" fill="url(#glow)"/>
</g>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13" fill="none" stroke="{EDGE}" stroke-width="1.5"/>
<g class="in">
<text class="mono" x="48" y="112" fill="{MUTED}" style="font-size:16px">// marketing technologist turned builder</text>
<text x="44" y="198" font-size="88" font-weight="700" fill="{INK}" letter-spacing="-2">Trevor Kist</text>
<text x="48" y="244" font-size="23" fill="{SOFT}">I build the tools I wished I had,</text>
<text x="48" y="275" font-size="23" fill="{SOFT}">and I like a good puzzle.</text>
</g>
<text class="mono" x="48" y="332" fill="{MUTED}">{prefix}</text>
{rotating}
<ellipse cx="{cx}" cy="{cy + 158}" rx="126" ry="14" fill="#000" opacity=".55" filter="url(#blur)"/>
{"".join(frames)}
</svg>
'''
    (OUT / "hero.svg").write_text(svg)


# ─────────────────────────── stack: sliding puzzle ────────────────────────────

def build_stack():
    W, H = 840, 354
    cols, rows, tw, th, gap = 4, 3, 186, 84, 8
    x0, y0 = 36, 30
    tiles = [
        ("TypeScript", BLUE), ("React", BLUE), ("React Native", BLUE), ("Three.js", BLUE), ("Node.js", BLUE),
        ("Supabase", GREEN), ("Convex", GREEN), ("PostgreSQL", GREEN),
        ("Netlify", YELLOW), ("Vercel", YELLOW),
        ("Claude Code", ORANGE),
    ]
    legend = [("build", BLUE), ("data", GREEN), ("ship", YELLOW), ("ai", ORANGE)]

    # scramble with a random walk of the blank, then solve by walking it back
    rng = random.Random(25)
    board = {(i // cols, i % cols): i for i in range(len(tiles))}
    blank, prev, walk = (rows - 1, cols - 1), None, []
    for _ in range(26):
        r, c = blank
        options = [(r + dr, c + dc) for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0))
                   if 0 <= r + dr < rows and 0 <= c + dc < cols and (r + dr, c + dc) != prev]
        nxt = rng.choice(options)
        tile = board.pop(nxt)
        board[blank] = tile
        walk.append((tile, nxt, blank))
        prev, blank = blank, nxt

    hold, fast, pause, slow = 3.4, 0.14, 0.9, 0.3
    total = hold + len(walk) * fast + pause + len(walk) * slow + 0.5
    segments = {i: [] for i in range(len(tiles))}
    t = hold
    for tile, src, dst in walk:
        segments[tile].append((t, t + fast, src, dst))
        t += fast
    t += pause
    for tile, src, dst in reversed(walk):
        segments[tile].append((t, t + slow, dst, src))
        t += slow

    def offset(tile, cell):
        return ((cell[1] - tile % cols) * (tw + gap), (cell[0] - tile // cols) * (th + gap))

    css, body = [], []
    for i, (label, color) in enumerate(tiles):
        stops = {0.0: (0, 0)}
        for start, end, src, dst in segments[i]:
            stops[round(start / total * 100, 3)] = offset(i, src)
            stops[round(end / total * 100, 3)] = offset(i, dst)
        stops[100.0] = (0, 0)
        if len(stops) > 2:
            frames = " ".join(f"{p:g}% {{ transform: translate({dx}px, {dy}px); }}" for p, (dx, dy) in sorted(stops.items()))
            css.append(f"@keyframes s{i} {{ {frames} }}\n.s{i} {{ animation: s{i} {total:.2f}s cubic-bezier(.45,0,.3,1) infinite; }}")
        x, y = x0 + (i % cols) * (tw + gap), y0 + (i // cols) * (th + gap)
        body.append(
            f'<g class="s{i}"><rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="12" fill="{PANEL}" stroke="{EDGE}" stroke-width="1.5"/>'
            f'<rect x="{x + 16}" y="{y + 16}" width="11" height="11" rx="3" fill="{color}"/>'
            f'<text class="mono" x="{x + tw - 16}" y="{y + 27}" text-anchor="end" fill="#6e7681">{i + 1:02d}</text>'
            f'<text class="lbl" x="{x + tw / 2:g}" y="{y + 58}" text-anchor="middle">{label}</text></g>')

    lx, key = x0, []
    for name, color in legend:
        key.append(f'<rect x="{lx}" y="{H - 31}" width="10" height="10" rx="3" fill="{color}"/>'
                   f'<text class="mono" x="{lx + 17}" y="{H - 22}" fill="{MUTED}">{name}</text>')
        lx += 40 + len(name) * 8.6

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="t d">
<title id="t">Tech stack: TypeScript, React, React Native, Three.js, Node.js, Supabase, Convex, PostgreSQL, Netlify, Vercel, Claude Code</title>
<desc id="d">A sliding tile puzzle with eleven tiles and one gap. Each tile is one tool. The puzzle scrambles itself, then slides the tiles back into order.</desc>
<defs><style>
text {{ font-family: {SANS}; }}
.mono {{ font-family: {MONO}; font-size: 13px; }}
.lbl {{ font-size: 22px; font-weight: 600; fill: {INK}; }}
{chr(10).join(css)}
@media (prefers-reduced-motion: reduce) {{ g {{ animation: none !important; }} }}
</style></defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13" fill="{BG}" stroke="{EDGE}" stroke-width="1.5"/>
<rect x="{x0 - 9}" y="{y0 - 9}" width="{cols * (tw + gap) - gap + 18}" height="{rows * (th + gap) - gap + 18}" rx="18" fill="#010409"/>
{"".join(body)}
{"".join(key)}
<text class="mono" x="{W - x0}" y="{H - 22}" text-anchor="end" fill="#6e7681">{len(walk)} moves out, {len(walk)} moves back</text>
</svg>
'''
    (OUT / "stack.svg").write_text(svg)


# ──────────────────────────────── maze: BFS ───────────────────────────────────

def build_maze():
    W, H = 840, 392
    cols, rows, cell = 24, 10, 32
    x0, y0 = 36, 28
    start, goal = (0, 4), (cols - 1, 5)

    # carve a perfect maze with an iterative depth-first search
    rng = random.Random(107)
    passages, seen, stack = set(), {start}, [start]
    while stack:
        c, r = stack[-1]
        options = [(c + dc, r + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if 0 <= c + dc < cols and 0 <= r + dr < rows and (c + dc, r + dr) not in seen]
        if not options:
            stack.pop()
            continue
        nxt = rng.choice(options)
        passages.add(frozenset(((c, r), nxt)))
        seen.add(nxt)
        stack.append(nxt)

    # solve it with breadth-first search, recording the order cells were visited
    parent, order, queue = {start: None}, [], deque([start])
    while queue:
        cur = queue.popleft()
        order.append(cur)
        if cur == goal:
            break
        c, r = cur
        for nxt in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if nxt not in parent and frozenset((cur, nxt)) in passages:
                parent[nxt] = cur
                queue.append(nxt)
    route, cur = [], goal
    while cur is not None:
        route.append(cur)
        cur = parent[cur]
    route.reverse()

    total, flood = 12.0, 4.4
    step = flood / len(order)
    centre = lambda p: (x0 + p[0] * cell + cell / 2, y0 + p[1] * cell + cell / 2)

    walls = []
    for c in range(cols):
        for r in range(rows):
            if c < cols - 1 and frozenset(((c, r), (c + 1, r))) not in passages:
                walls.append(f"M{x0 + (c + 1) * cell} {y0 + r * cell}v{cell}")
            if r < rows - 1 and frozenset(((c, r), (c, r + 1))) not in passages:
                walls.append(f"M{x0 + c * cell} {y0 + (r + 1) * cell}h{cell}")

    cells = "".join(
        f'<rect class="c" style="animation-delay:{i * step:.2f}s" x="{x0 + c * cell + 4}" y="{y0 + r * cell + 4}" width="{cell - 8}" height="{cell - 8}" rx="4"/>'
        for i, (c, r) in enumerate(order))
    line = "M" + "L".join(f"{n(x)} {n(y)}" for x, y in map(centre, route))
    marker = lambda p, color: (f'<rect x="{centre(p)[0] - 9:g}" y="{centre(p)[1] - 9:g}" width="18" height="18" rx="4" fill="{color}"/>')
    drawn = flood / total * 100

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="t d">
<title id="t">A maze solved by breadth-first search</title>
<desc id="d">A maze of {cols * rows} cells. A search spreads outward from the green start square, lighting each cell as it is visited, until it reaches the red goal. The shortest route is then traced in yellow.</desc>
<defs><style>
.mono {{ font-family: {MONO}; font-size: 13px; }}
.c {{ fill: #1f6feb; opacity: .34; animation: c {total:g}s linear infinite backwards; }}
@keyframes c {{ 0% {{ opacity: 0; fill: #a5d6ff; }} 1.2% {{ opacity: 1; fill: #a5d6ff; }} 6% {{ opacity: .34; fill: #1f6feb; }} 84% {{ opacity: .34; fill: #1f6feb; }} 89%, 100% {{ opacity: 0; fill: #1f6feb; }} }}
.p {{ fill: none; stroke: {YELLOW}; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1; animation: p {total:g}s linear infinite; }}
@keyframes p {{ 0%, {drawn:.1f}% {{ stroke-dashoffset: 1; opacity: 0; }} {drawn + .3:.1f}% {{ stroke-dashoffset: 1; opacity: 1; animation-timing-function: cubic-bezier(.4,0,.2,1); }} {drawn + 14:.1f}%, 84% {{ stroke-dashoffset: 0; opacity: 1; }} 88%, 100% {{ stroke-dashoffset: 0; opacity: 0; }} }}
.end {{ transform-box: fill-box; transform-origin: center; animation: end {total:g}s ease-out infinite; }}
@keyframes end {{ 0%, {drawn:.1f}% {{ transform: scale(1); }} {drawn + 2:.1f}% {{ transform: scale(1.5); }} {drawn + 6:.1f}%, 100% {{ transform: scale(1); }} }}
@media (prefers-reduced-motion: reduce) {{ .c, .p, .end {{ animation: none; }} }}
</style></defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13" fill="{BG}" stroke="{EDGE}" stroke-width="1.5"/>
{cells}
<path d="{"".join(walls)}" fill="none" stroke="{EDGE}" stroke-width="2" stroke-linecap="round"/>
<rect x="{x0}" y="{y0}" width="{cols * cell}" height="{rows * cell}" rx="4" fill="none" stroke="#484f58" stroke-width="2"/>
<path class="p" pathLength="1" d="{line}"/>
{marker(start, GREEN)}
<g class="end">{marker(goal, RED)}</g>
<text class="mono" x="{x0}" y="{H - 18}" fill="{MUTED}">breadth-first search</text>
<text class="mono" x="{W - x0}" y="{H - 18}" text-anchor="end" fill="#6e7681">visited {len(order)} of {cols * rows} cells · shortest path {len(route) - 1} steps</text>
</svg>
'''
    (OUT / "maze.svg").write_text(svg)
    return len(order), len(route) - 1


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    build_hero()
    build_stack()
    visited, steps = build_maze()
    for name in ("hero", "stack", "maze"):
        print(f"{name}.svg  {(OUT / f'{name}.svg').stat().st_size / 1024:.0f} KB")
    print(f"maze: visited {visited}, path {steps}")
