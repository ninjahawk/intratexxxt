"""Render the README charts from the measured runs in data/ (light and dark SVG, no dependencies).

    python tools/plot.py [--data data] [--out media]

- staircase.svg   cumulative work to reach every stage of the live challenge (data/trace.json)
- work.svg        work per stage against the geometric law it should follow (data/sweep.json)
- difficulty.svg  seconds per stage for every d at the measured hash rates (data/trace.json)
- chain.svg       the recurrence itself, drawn from challenge.json and the trace

It never draws a point that did not come from a file in data/.
"""

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT = "-apple-system, Segoe UI, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  axis="#c3c2b7", series="#2a78d6", series2="#eb6834", band="#e1e0d9", box="#f3f2ee"),
    "dark": dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 axis="#383835", series="#3987e5", series2="#d95926", band="#2c2c2a", box="#242423"),
}


def _head(w, h, c, title, desc, heading, sub, tid):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{FONT}" role="img" aria-labelledby="{tid}t {tid}d">',
        f'<title id="{tid}t">{title}</title>',
        f'<desc id="{tid}d">{desc}</desc>',
        f'<rect width="{w}" height="{h}" rx="10" fill="{c["surface"]}"/>',
        f'<text x="64" y="38" fill="{c["ink"]}" font-size="20" font-weight="600">{heading}</text>',
        f'<text x="64" y="62" fill="{c["ink2"]}" font-size="13">{sub}</text>',
    ]


def _nice_step(span, target=6):
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def render_staircase(trace: dict, theme: str) -> str:
    c = THEMES[theme]
    w, h = 960, 400
    pl, pr, pt, pb = 64, 120, 92, 52
    pw, ph = w - pl - pr, h - pt - pb
    d = trace["difficulty"]
    stages = trace["stages"]
    n = len(stages)
    cum = [0]
    for s in stages:
        cum.append(cum[-1] + s["tries"])
    total_s = sum(s["seconds"] for s in stages)
    exp = 2 ** d
    y_top_raw = max(cum[-1], exp * n) / 1e9
    step = _nice_step(y_top_raw, 5)
    y_max = step * math.ceil(y_top_raw / step)
    x_max = n

    def x(i):
        return pl + i / x_max * pw

    def y(v):
        return pt + (y_max - v) / y_max * ph

    o = _head(w, h, c, "The staircase, measured",
              f"Cumulative SHA-256 evaluations needed to reach each of the first {n} stages of the live challenge "
              f"at difficulty {d}, against the expected 2^{d} per stage.",
              "The staircase, measured",
              f"Cumulative SHA-256 work to climb the first {n} stages of the live challenge (d = {d}). "
              f"Dashed = expected 2<tspan font-size=\"9\" dy=\"-6\">{d}</tspan><tspan dy=\"6\"> per stage.</tspan>", "s")
    v = 0.0
    while v <= y_max + 1e-9:
        gy = y(v)
        o.append(f'<line x1="{pl}" y1="{gy:.1f}" x2="{pl + pw}" y2="{gy:.1f}" stroke="{c["grid"]}" stroke-width="1"/>')
        lab = f"{v:g}B" if v else "0"
        o.append(f'<text x="{pl - 10}" y="{gy + 4:.1f}" text-anchor="end" fill="{c["muted"]}" font-size="12">{lab}</text>')
        v += step
    xs = _nice_step(x_max, 6)
    i = 0
    while i <= x_max:
        o.append(f'<text x="{x(i):.1f}" y="{h - pb + 22}" text-anchor="middle" fill="{c["muted"]}" font-size="12">'
                 f"{int(i)}</text>")
        i += xs
    o.append(f'<text x="{pl + pw / 2:.1f}" y="{h - 10}" text-anchor="middle" fill="{c["muted"]}" font-size="12">stage</text>')
    o.append(f'<line x1="{x(0):.1f}" y1="{y(0):.1f}" x2="{x(n):.1f}" y2="{y(exp * n / 1e9):.1f}" '
             f'stroke="{c["ink2"]}" stroke-width="1.5" stroke-dasharray="6 5"/>')
    # the staircase: flat while a stage is being solved, a riser when it falls
    path = [f"M{x(0):.1f},{y(0):.1f}"]
    for k in range(n):
        path.append(f"V{y(cum[k + 1] / 1e9):.1f}")
        path.append(f"H{x(k + 1):.1f}")
    o.append(f'<path d="{" ".join(path)}" fill="none" stroke="{c["series"]}" stroke-width="2" '
             'stroke-linejoin="round" stroke-linecap="round"/>')
    ex, ey = x(n), y(cum[-1] / 1e9)
    o.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="{c["series"]}" stroke="{c["surface"]}" stroke-width="2"/>')
    # it does not stop: continue the riser rhythm faintly past the last measured stage
    o.append(f'<path d="M{ex + 8:.1f},{ey:.1f} h14 v-10 h14 v-10 h14 v-10" fill="none" stroke="{c["series"]}" '
             'stroke-width="2" stroke-dasharray="2 4" opacity="0.6"/>')
    o.append(f'<text x="{ex + 10:.1f}" y="{ey - 40:.1f}" fill="{c["ink"]}" font-size="13" font-weight="600">stage {n}</text>')
    o.append(f'<text x="{ex + 10:.1f}" y="{ey - 24:.1f}" fill="{c["ink2"]}" font-size="12">{cum[-1] / 1e9:.1f}B hashes</text>')
    o.append(f'<text x="{ex + 10:.1f}" y="{ey + 20:.1f}" fill="{c["muted"]}" font-size="12">no last stage</text>')
    o.append(f'<text x="{w - 16}" y="{h - 12}" text-anchor="end" fill="{c["muted"]}" font-size="11">'
             f'{n} stages · {total_s / 60:.0f} min on {trace["threads"]} threads · {trace["cpu"]}</text>')
    o.append("</svg>")
    return "\n".join(o)


def render_work(sweep: dict, theme: str) -> str:
    c = THEMES[theme]
    w, h = 960, 380
    pl, pr, pt, pb = 64, 28, 92, 52
    pw, ph = w - pl - pr, h - pt - pb
    d = sweep["difficulty"]
    t = [s["tries"] / 2 ** d for s in sweep["stages"]]
    n = len(t)
    width, cap = 0.25, 5.0
    bins = int(cap / width)
    counts = [0] * bins
    over = 0
    for v in t:
        if v >= cap:
            over += 1
            continue
        counts[int(v / width)] += 1
    dens = [k / (n * width) for k in counts]
    y_max = 1.0

    def x(v):
        return pl + v / cap * pw

    def y(v):
        return pt + (y_max - v) / y_max * ph

    mean = sum(t) / n
    o = _head(w, h, c, "Work per stage follows the geometric law",
              f"Histogram of SHA-256 evaluations per stage divided by 2^d over {n} consecutive stages, with the "
              "exponential density e^-t that an ideal hash predicts.",
              "Every stage costs what the math says it should",
              f"Work per stage ÷ 2ᵈ over {n:,} consecutive stages (d = {d}). "
              "Line = e⁻ᵗ, the density an ideal hash predicts.", "w")
    for k in range(0, 6):
        v = k / 5
        o.append(f'<line x1="{pl}" y1="{y(v):.1f}" x2="{pl + pw}" y2="{y(v):.1f}" stroke="{c["grid"]}" stroke-width="1"/>')
        o.append(f'<text x="{pl - 10}" y="{y(v) + 4:.1f}" text-anchor="end" fill="{c["muted"]}" font-size="12">{v:.1f}</text>')
    for k in range(0, int(cap) + 1):
        o.append(f'<text x="{x(k):.1f}" y="{h - pb + 22}" text-anchor="middle" fill="{c["muted"]}" font-size="12">'
                 f'{k}×</text>')
    o.append(f'<text x="{pl + pw / 2:.1f}" y="{h - 10}" text-anchor="middle" fill="{c["muted"]}" font-size="12">'
             "hashes needed ÷ 2ᵈ</text>")
    for k, v in enumerate(dens):
        bx = x(k * width) + 1
        bw = x(width) - pl - 2
        top = y(min(v, y_max))
        hgt = y(0) - top
        if hgt <= 0:
            continue
        r = min(4, hgt / 2, bw / 2)
        o.append(f'<path d="M{bx:.1f},{y(0):.1f} V{top + r:.1f} Q{bx:.1f},{top:.1f} {bx + r:.1f},{top:.1f} '
                 f'H{bx + bw - r:.1f} Q{bx + bw:.1f},{top:.1f} {bx + bw:.1f},{top + r:.1f} V{y(0):.1f} Z" '
                 f'fill="{c["series"]}" opacity="0.85"><title>{k * width:.2f}–{(k + 1) * width:.2f}×: '
                 f'{counts[k]} stages</title></path>')
    curve = " L".join(f"{x(v):.1f},{y(math.exp(-v)):.1f}" for v in [i / 50 for i in range(0, int(cap * 50) + 1)])
    o.append(f'<path d="M{curve}" fill="none" stroke="{c["ink"]}" stroke-width="2" stroke-linejoin="round"/>')
    o.append(f'<text x="{x(1.1):.1f}" y="{y(math.exp(-1.1)) - 10:.1f}" fill="{c["ink"]}" font-size="13">e⁻ᵗ</text>')
    o.append(f'<text x="{x(3.2):.1f}" y="{y(0.62):.1f}" fill="{c["ink"]}" font-size="13" font-weight="600">'
             f"mean {mean:.3f} × 2ᵈ</text>")
    o.append(f'<text x="{x(3.2):.1f}" y="{y(0.62) + 18:.1f}" fill="{c["ink2"]}" font-size="12">'
             "expected 1.000 · no shortcut stage, no lucky streak</text>")
    o.append(f'<text x="{w - 16}" y="{h - 12}" text-anchor="end" fill="{c["muted"]}" font-size="11">'
             f"{n:,} stages ({over} beyond 5×, not drawn) · seed {sweep['stage0'][:12]}…</text>")
    o.append("</svg>")
    return "\n".join(o)


def _fmt_secs(s):
    for lim, div, unit in ((60, 1, "s"), (3600, 60, "min"), (86400, 3600, "h"), (86400 * 365, 86400, "d")):
        if s < lim:
            return f"{s / div:.0f} {unit}" if s / div >= 10 else f"{s / div:.1f} {unit}"
    return f"{s / (86400 * 365):.1f} yr"


def render_difficulty(trace: dict, theme: str) -> str:
    c = THEMES[theme]
    w, h = 960, 420
    pl, pr, pt, pb = 64, 150, 92, 72
    pw, ph = w - pl - pr, h - pt - pb
    rates = trace["rates"]
    one, allr = rates[0], rates[-1]
    d_lo, d_hi = 16, 44
    ticks = [(1e-2, "10 ms"), (1, "1 s"), (60, "1 min"), (3600, "1 h"), (86400, "1 day"), (86400 * 365, "1 yr")]
    lo, hi = math.log10(1e-2), math.log10(86400 * 365 * 3)

    def x(dv):
        return pl + (dv - d_lo) / (d_hi - d_lo) * pw

    def y(s):
        return pt + (hi - math.log10(s)) / (hi - lo) * ph

    o = _head(w, h, c, "Seconds per stage at every difficulty",
              "Expected wall-clock seconds to solve one stage, 2^d divided by the measured hash rate, for one thread "
              "and for all threads, on a log scale.",
              "What one more bit of difficulty costs",
              f"Expected time per stage = 2ᵈ ÷ measured hash rate, log scale. Each bit doubles it. "
              f"The live challenge runs at d = {trace['difficulty']}.", "d")
    for s, lab in ticks:
        o.append(f'<line x1="{pl}" y1="{y(s):.1f}" x2="{pl + pw}" y2="{y(s):.1f}" stroke="{c["grid"]}" stroke-width="1"/>')
        o.append(f'<text x="{pl - 10}" y="{y(s) + 4:.1f}" text-anchor="end" fill="{c["muted"]}" font-size="12">{lab}</text>')
    for dv in range(d_lo, d_hi + 1, 4):
        o.append(f'<text x="{x(dv):.1f}" y="{h - pb + 22}" text-anchor="middle" fill="{c["muted"]}" font-size="12">{dv}</text>')
    o.append(f'<text x="{pl + pw / 2:.1f}" y="{h - 38}" text-anchor="middle" fill="{c["muted"]}" font-size="12">'
             "difficulty d (leading zero bits)</text>")
    dv = trace["difficulty"]
    o.append(f'<line x1="{x(dv):.1f}" y1="{pt}" x2="{x(dv):.1f}" y2="{pt + ph}" stroke="{c["axis"]}" stroke-width="1.5" '
             'stroke-dasharray="4 4"/>')
    o.append(f'<text x="{x(dv) + 6:.1f}" y="{pt + 14}" fill="{c["ink2"]}" font-size="12">v1 · d = {dv}</text>')
    for r, col, lab in ((one, c["series2"], f'1 thread · {one["hps"] / 1e6:.1f} MH/s'),
                        (allr, c["series"], f'{allr["threads"]} threads · {allr["hps"] / 1e6:.1f} MH/s')):
        pts = [(dd, 2 ** dd / r["hps"]) for dd in range(d_lo, d_hi + 1)]
        pts = [(dd, s) for dd, s in pts if lo <= math.log10(s) <= hi]
        line = " L".join(f"{x(dd):.1f},{y(s):.1f}" for dd, s in pts)
        o.append(f'<path d="M{line}" fill="none" stroke="{col}" stroke-width="2" stroke-linecap="round"/>')
        s26 = 2 ** dv / r["hps"]
        o.append(f'<circle cx="{x(dv):.1f}" cy="{y(s26):.1f}" r="4.5" fill="{col}" stroke="{c["surface"]}" stroke-width="2">'
                 f"<title>{lab}: {_fmt_secs(s26)} per stage at d = {dv}</title></circle>")
        o.append(f'<text x="{x(dv) - 8:.1f}" y="{y(s26) + 4:.1f}" text-anchor="end" fill="{c["ink"]}" font-size="12">'
                 f"{_fmt_secs(s26)}</text>")
        ed, es = pts[-1]
        nudge = -7 if col == c["series2"] else 9
        o.append(f'<text x="{x(ed) + 8:.1f}" y="{y(es) + 4 + nudge:.1f}" fill="{c["ink2"]}" font-size="12">{lab}</text>')
    o.append(f'<text x="{w - 16}" y="{h - 12}" text-anchor="end" fill="{c["muted"]}" font-size="11">'
             f'measured on {trace["cpu"]}; a GPU moves both lines down, not their slope</text>')
    o.append("</svg>")
    return "\n".join(o)


def render_chain(challenge: dict, trace: dict, theme: str) -> str:
    c = THEMES[theme]
    w, h = 960, 272
    o = _head(w, h, c, "The recurrence",
              "Stage i publishes a state S_i; a nonce x_i whose puzzle hash falls below the target produces S_(i+1), "
              "and the same rule applies again. A sealed AES-256-GCM payload ships alongside.",
              "The recurrence",
              "Each solution is the only input to the next stage. Below: the real first stages of the live challenge.",
              "c")
    st = trace["stages"]
    states = [challenge["stage0"]] + [s["next"] for s in st[:3]]
    bw, bh, y0, x0, gap = 170, 64, 96, 40, 62
    for k in range(4):
        bx = x0 + k * (bw + gap)
        o.append(f'<rect x="{bx}" y="{y0}" width="{bw}" height="{bh}" rx="8" fill="{c["box"]}" stroke="{c["axis"]}"/>')
        o.append(f'<text x="{bx + 14}" y="{y0 + 24}" fill="{c["ink"]}" font-size="14" font-weight="600">S<tspan '
                 f'font-size="10" dy="4">{k}</tspan></text>')
        o.append(f'<text x="{bx + 14}" y="{y0 + 46}" fill="{c["ink2"]}" font-size="12" font-family="{MONO}">'
                 f"{states[k][:8]}…{states[k][-6:]}</text>")
        if k < 3:
            ax = bx + bw
            o.append(f'<line x1="{ax + 4}" y1="{y0 + bh / 2}" x2="{ax + gap - 8}" y2="{y0 + bh / 2}" stroke="{c["series"]}" '
                     'stroke-width="2"/>')
            o.append(f'<path d="M{ax + gap - 8},{y0 + bh / 2 - 5} l8,5 l-8,5 z" fill="{c["series"]}"/>')
            o.append(f'<text x="{ax + gap / 2}" y="{y0 - 10}" text-anchor="middle" fill="{c["ink2"]}" font-size="12" '
                     f'font-family="{MONO}">x<tspan font-size="9" dy="3">{k}</tspan><tspan dy="-3">={st[k]["nonce"]:,}</tspan></text>')
    lx = x0 + 4 * (bw + gap) - gap
    o.append(f'<text x="{lx + 10}" y="{y0 + bh / 2 + 6}" fill="{c["series"]}" font-size="22" font-weight="600">⋯</text>')
    rule_y = y0 + bh + 40
    o.append(f'<text x="64" y="{rule_y}" fill="{c["ink"]}" font-size="13" font-family="{MONO}">'
             'valid(x) ⇔ SHA256("RCP|puzzle|" ‖ i ‖ S<tspan font-size="9" dy="3">i</tspan><tspan dy="-3"> ‖ x) &lt; 2</tspan>'
             f'<tspan font-size="9" dy="-6">256−{challenge["difficulty"]}</tspan></text>')
    o.append(f'<text x="64" y="{rule_y + 24}" fill="{c["ink"]}" font-size="13" font-family="{MONO}">'
             'S<tspan font-size="9" dy="3">i+1</tspan><tspan dy="-3"> = SHA256("RCP|next|" ‖ i ‖ S</tspan>'
             '<tspan font-size="9" dy="3">i</tspan><tspan dy="-3"> ‖ x</tspan><tspan font-size="9" dy="3">i</tspan>'
             '<tspan dy="-3">)</tspan></text>')
    L = challenge["lock"]
    px, py, pwid = 600, rule_y - 22, 320
    o.append(f'<rect x="{px}" y="{py}" width="{pwid}" height="62" rx="8" fill="none" stroke="{c["ink2"]}" '
             'stroke-dasharray="5 4"/>')
    o.append(f'<text x="{px + 14}" y="{py + 24}" fill="{c["ink"]}" font-size="13" font-weight="600">sealed payload · '
             f'{len(L["ciphertext"]) // 2} bytes</text>')
    o.append(f'<text x="{px + 14}" y="{py + 44}" fill="{c["ink2"]}" font-size="12">AES-256-GCM · Argon2id '
             f'{L["memory_kib"] // 1024} MiB × {L["time"]}</text>')
    o.append("</svg>")
    return "\n".join(o)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--out", default=str(ROOT / "media"))
    args = ap.parse_args()
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    trace = json.loads((data / "trace.json").read_text())
    sweep = json.loads((data / "sweep.json").read_text())
    challenge = json.loads((ROOT / "challenge.json").read_text())
    for theme in THEMES:
        suffix = "" if theme == "light" else "-dark"
        (out / f"staircase{suffix}.svg").write_text(render_staircase(trace, theme) + "\n")
        (out / f"work{suffix}.svg").write_text(render_work(sweep, theme) + "\n")
        (out / f"difficulty{suffix}.svg").write_text(render_difficulty(trace, theme) + "\n")
        (out / f"chain{suffix}.svg").write_text(render_chain(challenge, trace, theme) + "\n")
    print(f"wrote 8 charts to {out}")


if __name__ == "__main__":
    main()
