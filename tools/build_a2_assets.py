"""
產生黑洞 A2 版的自製 SVG（assets/a2/）。

用法：
  python tools/build_a2_assets.py <fonts_dir> <icons_dir>

  fonts_dir 需含（來自 github.com/google/fonts，OFL 1.1）：
    spacegrotesk/SpaceGrotesk[wght].ttf
    jetbrainsmono/JetBrainsMono[wght].ttf
  icons_dir 需含 Simple Icons（CC0）的 <slug>.svg，見 ICON_SLUGS。

需要：fonttools、brotli（woff2 壓縮）。
配色集中在 PALETTES（dark / light）；每張 SVG 開頭以 CSS 變數輸出。
深色版檔名無後綴，淺色版加 -light。
"""
import base64
import math
import io
import pathlib
import re
import sys
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = pathlib.Path(sys.argv[1])
ICONS = pathlib.Path(sys.argv[2])
OUT = ROOT / "assets" / "a2"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 配色
PALETTES = {
    "dark": {
        "bg": "#07070F",      # 深空底
        "panel": "#0D0B1A",   # 卡片底
        "line": "#2A2340",    # 邊框／細線
        "accent": "#FF9A3C",  # 吸積盤橘
        "gold": "#FFD27A",    # 吸積盤金
        "violet": "#8466FF",  # 透鏡紫（略提亮，文字對比 ≥ 4.5）
        "text": "#C9D1D9",
        "muted": "#8B949E",
        "bright": "#F0F6FC",
        "hole": "#000000",    # 事件視界
        "horizon": "#000000", # 頁尾地平線
        "star": "#FFFFFF",
    },
    "light": {
        "bg": "#FFFFFF",
        "panel": "#F6F8FA",
        "line": "#D0D7DE",
        "accent": "#B54708",
        "gold": "#7A4F00",
        "violet": "#6639BA",
        "text": "#1F2328",
        "muted": "#59636E",
        "bright": "#1F2328",
        "hole": "#1F2328",
        "horizon": "#EEEAF8",  # 淺色版不放大面積深色
        "star": "#6639BA",
    },
}
PALETTE = PALETTES["dark"]
SUFFIX = ""
LANG_COLORS = {"Python": "#3572A5", "TypeScript": "#3178C6"}  # GitHub linguist 顏色

CJK_FALLBACK = "'Noto Sans TC','Microsoft JhengHei','PingFang TC','Heiti TC',sans-serif"


# ---------------------------------------------------------------- 字型
class Font:
    def __init__(self, path, wght, family):
        f = TTFont(path)
        f = instantiateVariableFont(f, {"wght": wght})
        buf = io.BytesIO()
        f.save(buf)
        self.raw = buf.getvalue()
        self.family = family
        self.upm = f["head"].unitsPerEm
        self.cmap = f.getBestCmap()
        self.hmtx = f["hmtx"]

    def width(self, s, size):
        w = 0
        for ch in s:
            g = self.cmap.get(ord(ch))
            w += self.hmtx[g][0] / self.upm * size if g else size  # 不在字型內（CJK/emoji）以 1em 估
        return w

    def face(self, text):
        chars = "".join(sorted({c for c in text if ord(c) in self.cmap}))
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.hinting = False
        opts.layout_features = ["kern", "liga"]
        opts.name_IDs = []
        opts.notdef_outline = False
        f = TTFont(io.BytesIO(self.raw))
        s = subset.Subsetter(opts)
        s.populate(text=chars)
        s.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff2"
        f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"@font-face{{font-family:'{self.family}';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


SG = Font(FONTS / "spacegrotesk" / "SpaceGrotesk[wght].ttf", 600, "SG")    # 標題、專案名
SGR = Font(FONTS / "spacegrotesk" / "SpaceGrotesk[wght].ttf", 400, "SGR")  # 說明文字
JB = Font(FONTS / "jetbrainsmono" / "JetBrainsMono[wght].ttf", 400, "JB")  # 等寬：標籤、終端機

# ---------------------------------------------------------------- 圖示（Simple Icons, CC0）
ICON_SLUGS = ["python", "openjdk", "cplusplus", "typescript", "javascript", "pytorch", "tensorflow", "scikitlearn",
              "pandas", "fastapi", "django", "mysql", "postgresql", "sqlite", "supabase", "react", "nextdotjs", "html5",
              "css3", "leaflet", "git", "githubactions", "vercel", "linux", "gnubash", "googlechrome"]


def icon_path(slug):
    if slug == "sparkle":  # LLM + RAG 用的自繪星芒（不使用 OpenAI 商標）
        return "M12 0l2.6 9.4L24 12l-9.4 2.6L12 24l-2.6-9.4L0 12l9.4-2.6z"
    svg = (ICONS / f"{slug}.svg").read_text(encoding="utf-8")
    return re.search(r'<path d="([^"]+)"', svg).group(1)


def icon(slug, x, y, size, cls="gold"):
    return f'<path class="{cls}" transform="translate({x:.1f} {y:.1f}) scale({size / 24:.4f})" d="{icon_path(slug)}"/>'


# ---------------------------------------------------------------- SVG 外框
BASE_CSS = """
.bg{fill:var(--bg)}.panel{fill:var(--panel)}.ln{stroke:var(--line)}.acc{fill:var(--accent)}.gold{fill:var(--gold)}
.vio{fill:var(--violet)}.txt{fill:var(--text)}.mut{fill:var(--muted)}.brt{fill:var(--bright)}
.sg{font-family:'SG',sans-serif;font-weight:600}.sgr{font-family:'SGR',CJKFB}.jb{font-family:'JB',Consolas,monospace}
""".replace("CJKFB", CJK_FALLBACK)


def svg(w, h, body, label, fonts=(), extra_css=""):
    """fonts: [(Font, 用到的文字)]"""
    vars_ = ";".join(f"--{k}:{v}" for k, v in PALETTE.items())
    faces = "".join(f.face(t) for f, t in fonts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{escape(label, {chr(34): "&quot;"})}">\n'
            f"<style>:root{{{vars_}}}{faces}{BASE_CSS}{extra_css}</style>\n{body}\n</svg>\n")


def stop(offset, var, opacity=1):
    return f'<stop offset="{offset}" style="stop-color:var(--{var});stop-opacity:{opacity}"/>'


def write(name, content):
    (OUT / f"{name[:-4]}{SUFFIX}.svg").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- 1. 區塊標題
def title(slug, text, main=True):
    """固定寬度的標題：寬度 = 文字寬 + 兩側裝飾，README 以原生寬度顯示（不撐滿全寬）。
    桌機上字級固定；只有容器比圖窄（手機）時才等比縮小。"""
    size = 30 if main else 22
    h = 64 if main else 46
    line_len = 64 if main else 36
    gap = 20 if main else 16
    tw = SG.width(text, size)
    w = round(tw + 2 * (gap + line_len + 8))
    cx, cy = w / 2, h / 2
    l_end, r_start = cx - tw / 2 - gap, cx + tw / 2 + gap
    fill = "url(#tg)" if main else "var(--bright)"
    dot_r = 3 if main else 2.2
    pulse = "" if not main else (
        f'<circle cx="{l_end:.1f}" cy="{cy}" r="7" fill="none" style="stroke:var(--gold)" stroke-width="1" opacity="0">'
        '<animate attributeName="r" values="3;10" dur="4s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.7;0" dur="4s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{r_start:.1f}" cy="{cy}" r="7" fill="none" style="stroke:var(--gold)" stroke-width="1" opacity="0">'
        '<animate attributeName="r" values="3;10" dur="4s" begin="2s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.7;0" dur="4s" begin="2s" repeatCount="indefinite"/></circle>')
    body = f'''<defs>
<linearGradient id="tg" x1="0" y1="0" x2="1" y2="0">{stop(0, "gold")}{stop(1, "accent")}</linearGradient>
<linearGradient id="ll" x1="0" y1="0" x2="1" y2="0">{stop(0, "violet", 0)}{stop(0.6, "violet", 0.8)}{stop(1, "accent")}</linearGradient>
<linearGradient id="lr" x1="0" y1="0" x2="1" y2="0">{stop(0, "accent")}{stop(0.4, "violet", 0.8)}{stop(1, "violet", 0)}</linearGradient>
<filter id="gl" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="2.5"/></filter>
</defs>
<rect x="{l_end - 8 - line_len:.1f}" y="{cy - 0.6}" width="{line_len}" height="1.2" fill="url(#ll)"/>
<rect x="{r_start + 8:.1f}" y="{cy - 0.6}" width="{line_len}" height="1.2" fill="url(#lr)"/>
<circle cx="{l_end:.1f}" cy="{cy}" r="{dot_r * 2}" class="acc" filter="url(#gl)" opacity="0.6"/>
<circle cx="{l_end:.1f}" cy="{cy}" r="{dot_r}" class="gold"/>
<circle cx="{r_start:.1f}" cy="{cy}" r="{dot_r * 2}" class="acc" filter="url(#gl)" opacity="0.6"/>
<circle cx="{r_start:.1f}" cy="{cy}" r="{dot_r}" class="gold"/>
{pulse}
<text x="{cx}" y="{cy + size * 0.35:.1f}" text-anchor="middle" class="sg" font-size="{size}" style="fill:{fill}">{escape(text)}</text>'''
    write(f"title-{slug}.svg", svg(w, h, body, text, [(SG, text)]))
    return w


# ---------------------------------------------------------------- 2. 專案卡片
def wrap(text, font, size, maxw, max_lines):
    tokens = re.findall(r"[⺀-鿿＀-￯　-〿]|[^\s⺀-鿿＀-￯　-〿]+\s*|\s+", text)
    lines, cur = [], ""
    for t in tokens:
        if font.width((cur + t).rstrip(), size) <= maxw:
            cur += t
        else:
            lines.append(cur.rstrip())
            cur = t.lstrip()
    lines.append(cur.rstrip())
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while font.width(lines[-1] + "…", size) > maxw:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "…"
    return lines


def pill(x_right, y, text, live):
    tw = JB.width(text, 10.5) + (14 if live else 0)
    w = tw + 18
    x = x_right - w
    cls = "acc" if live else "mut"
    dot = (f'<circle cx="{x + 11}" cy="{y + 10}" r="3" class="acc"><animate attributeName="opacity" '
           'values="1;0.25;1" dur="2.4s" repeatCount="indefinite"/></circle>') if live else ""
    return x, (f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="20" rx="10" fill="none" '
               f'style="stroke:var(--{"accent" if live else "muted"})" stroke-opacity="0.7"/>{dot}'
               f'<text x="{x + 9 + (14 if live else 0):.1f}" y="{y + 14}" class="jb {cls}" font-size="10.5" '
               f'letter-spacing="0.8">{text}</text>')


def card(slug, name, desc, lang, tags):
    w, h = 420, 150
    name_size = 20
    maxname = 300
    if SG.width(name, name_size) > maxname:
        name_size = round(name_size * maxname / SG.width(name, name_size), 1)
    lines = wrap(desc, SGR, 13.5, 376, 2)
    desc_svg = "".join(f'<text x="22" y="{78 + i * 20}" class="sgr txt" font-size="13.5">{escape(l)}</text>'
                       for i, l in enumerate(lines))
    lang_svg = ""
    if lang:
        c = LANG_COLORS.get(lang)
        style = f'fill:{c}' if c else "fill:var(--gold)"
        lang_svg = (f'<circle cx="28" cy="{h - 25}" r="5" style="{style}"/>'
                    f'<text x="40" y="{h - 21}" class="jb mut" font-size="12">{escape(lang)}</text>')
    xr, tags_svg = w - 20, ""
    for t in reversed(tags):
        xr, p = pill(xr, h - 35, t, t == "LIVE")
        tags_svg += p
        xr -= 8
    body = f'''<defs>
<radialGradient id="glow" cx="100%" cy="0%" r="70%">{stop(0, "violet", 0.28)}{stop(1, "violet", 0)}</radialGradient>
<linearGradient id="disk" x1="0" y1="0" x2="1" y2="0">{stop(0, "accent", 0.1)}{stop(0.5, "gold")}{stop(1, "accent", 0.1)}</linearGradient>
</defs>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" class="panel ln"/>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="url(#glow)"/>
<g transform="translate({w - 40} 36)">
<g transform="rotate(-12) scale(1 0.3)"><circle r="22" fill="none" stroke="url(#disk)" stroke-width="4">
<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="30s" repeatCount="indefinite"/></circle></g>
<circle r="8" style="fill:var(--hole)"/><circle r="8" fill="none" style="stroke:var(--gold)" stroke-opacity="0.6"/>
</g>
<text x="22" y="44" class="sg gold" font-size="{name_size}">{escape(name)}</text>
{desc_svg}
{lang_svg}
{tags_svg}'''
    label = f"{name} — {desc}"
    write(f"card-{slug}.svg", svg(w, h, body, label,
                                  [(SG, name), (SGR, "".join(lines)), (JB, (lang or "") + "".join(tags))]))


# ---------------------------------------------------------------- 3. Tech Stack 面板
TECH = {
    "Languages": [("python", "Python"), ("openjdk", "Java"), ("cplusplus", "C/C++"), ("typescript", "TypeScript"),
                  ("javascript", "JavaScript")],
    "AI / ML": [("pytorch", "PyTorch"), ("tensorflow", "TensorFlow"), ("scikitlearn", "scikit-learn"),
                ("pandas", "Pandas"), ("sparkle", "LLM + RAG")],
    "Backend / Data": [("fastapi", "FastAPI"), ("django", "Django"), ("mysql", "MySQL"), ("postgresql", "PostgreSQL"),
                       ("sqlite", "SQLite"), ("supabase", "Supabase")],
    "Frontend": [("react", "React"), ("nextdotjs", "Next.js"), ("html5", "HTML5"), ("css3", "CSS3"),
                 ("leaflet", "Leaflet")],
    "Tools / Deploy": [("git", "Git"), ("githubactions", "GitHub Actions"), ("vercel", "Vercel"), ("linux", "Linux"),
                       ("gnubash", "Shell Script")],
}


def tech_panel(slug, groups, height):
    w, pad, cols = 420, 20, 3
    cell_w = (w - 2 * pad - (cols - 1) * 8) / cols
    y, parts, texts = pad, [], ""
    for g in groups:
        parts.append(f'<text x="{pad}" y="{y + 11}" class="jb mut" font-size="11" letter-spacing="1">{escape(g)}</text>'
                     f'<rect x="{pad + JB.width(g, 11) + len(g) + 10:.1f}" y="{y + 7}" width="{w - 2 * pad - JB.width(g, 11) - len(g) - 10:.1f}" height="1" class="ln" style="fill:var(--line)"/>')
        texts += g
        y += 22
        for i, (ic, lab) in enumerate(TECH[g]):
            cx = pad + (i % cols) * (cell_w + 8)
            cy = y + (i // cols) * 38
            fs = 12.5
            if SGR.width(lab, fs) > cell_w - 40:
                fs = round(fs * (cell_w - 40) / SGR.width(lab, fs), 1)
            parts.append(f'<rect x="{cx:.1f}" y="{cy}" width="{cell_w:.1f}" height="30" rx="8" class="bg ln"/>'
                         f'{icon(ic, cx + 10, cy + 7, 16)}'
                         f'<text x="{cx + 34:.1f}" y="{cy + 19.5}" class="sgr txt" font-size="{fs}">{escape(lab)}</text>')
            texts += lab
        y += ((len(TECH[g]) + cols - 1) // cols) * 38 + 16
    # 下方剩餘空間放一個小吸積盤做平衡
    deco = ""
    free = height - y
    if free > 50:
        cy = y + free / 2 - 6
        deco = f'''<g transform="translate({w / 2} {cy:.1f})" opacity="0.8">
<g transform="rotate(-8) scale(1 0.22)"><circle r="70" fill="none" stroke="url(#disk)" stroke-width="10">
<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="50s" repeatCount="indefinite"/></circle></g>
<circle r="14" class="bg"/><circle r="15" fill="none" style="stroke:var(--gold)" stroke-opacity="0.5"/></g>'''
    body = f'''<defs><linearGradient id="disk" x1="0" y1="0" x2="1" y2="0">{stop(0, "accent", 0.05)}{stop(0.5, "gold", 0.9)}{stop(1, "accent", 0.05)}</linearGradient></defs>
<rect x="0.5" y="0.5" width="{w - 1}" height="{height - 1}" rx="14" class="panel ln"/>
{"".join(parts)}{deco}'''
    label = "Tech Stack — " + "; ".join(f"{g}: " + ", ".join(l for _, l in TECH[g]) for g in groups)
    write(f"stack-{slug}.svg", svg(w, height, body, label, [(JB, texts), (SGR, texts)]))


# ---------------------------------------------------------------- 4. About Me 終端機卡片
ABOUT = """name: ChenYu Hsu
based_in: Taichung, Taiwan 🇹🇼
currently: AI Engineer @ SaySing — building the ECHOAi brand website
current_focus:
  - LLM applications — AI chat assistants, RAG, voice demos
  - Full-stack web with Next.js (+ CMS / Postgres)
  - Side projects in data visualization and game tooling
fun_fact: "My best ideas show up in the shower\"""".split("\n")


def about_card():
    w, fs, lh = 420, 12, 20
    x0 = 46
    maxw = w - x0 - 18
    rows = []  # (行號或 None, [(class, text)], x 偏移字元數)
    for n, line in enumerate(ABOUT, 1):
        m = re.match(r"^(\s*-\s|[a-z_]+:\s?)(.*)$", line)
        head, rest = m.group(1), m.group(2)
        head_cls = "vio" if head.strip() == "-" else "acc"
        rest_cls = "gold" if rest.startswith('"') else "txt"
        # 依寬度換行，續行對齊到值的起點
        indent = len(head)
        avail = int(maxw / JB.width("M", fs))
        words, cur, first = rest.split(" "), "", True
        chunks = []
        for wd in words:
            limit = avail - indent
            if len(cur) + len(wd) + (1 if cur else 0) <= limit:
                cur = f"{cur} {wd}" if cur else wd
            else:
                chunks.append(cur)
                cur = wd
        chunks.append(cur)
        for i, c in enumerate(chunks):
            if i == 0:
                rows.append((n, [(head_cls, head), (rest_cls, c)], 0))
            else:
                rows.append((None, [(rest_cls, c)], indent))
    top = 46
    h = top + len(rows) * lh + 22
    cw = JB.width("M", fs)
    out, alltext = [], ""
    for i, (num, segs, ind) in enumerate(rows):
        y = top + 14 + i * lh
        if num:
            out.append(f'<text x="{x0 - 14}" y="{y}" text-anchor="end" class="jb mut" font-size="{fs}">{num}</text>')
            alltext += str(num)
        spans = "".join(f'<tspan class="{c}">{escape(t).replace(" ", "&#160;")}</tspan>' for c, t in segs)
        out.append(f'<text x="{x0 + ind * cw:.1f}" y="{y}" class="jb" font-size="{fs}">{spans}</text>')
        alltext += "".join(t for _, t in segs)
    last_y = top + 14 + (len(rows) - 1) * lh
    last_len = sum(JB.width(t, fs) for _, t in rows[-1][1]) + rows[-1][2] * cw
    cursor = (f'<rect x="{x0 + last_len + 4:.1f}" y="{last_y - 11}" width="7" height="14" class="acc">'
              '<animate attributeName="opacity" values="1;0" keyTimes="0;0.5" calcMode="discrete" dur="1.1s" repeatCount="indefinite"/></rect>')
    body = f'''<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" class="panel ln"/>
<path d="M0.5 14.5a14 14 0 0 1 14-14h{w - 29}a14 14 0 0 1 14 14v19.5h-{w - 1}z" class="bg"/>
<line x1="0.5" y1="34" x2="{w - 0.5}" y2="34" class="ln"/>
<g fill="none" stroke-width="1.3"><circle cx="20" cy="17.5" r="4.5" style="stroke:var(--accent)"/><circle cx="36" cy="17.5" r="4.5" style="stroke:var(--gold)"/><circle cx="52" cy="17.5" r="4.5" style="stroke:var(--violet)"/></g>
<text x="{w / 2}" y="21.5" text-anchor="middle" class="jb mut" font-size="11">about-me.yml</text>
{"".join(out)}
{cursor}'''
    write("about.svg", svg(w, h, body, "About Me — " + " / ".join(ABOUT), [(JB, alltext + "about-me.yml")]))
    return h


# ---------------------------------------------------------------- 5. 連結膠囊（取代 shields）
def link_pill(slug, ic, text):
    """ic=None 時只放文字，左右留白相同"""
    fs = 13
    h = 34
    tx = 38 if ic else 18
    w = round(SG.width(text, fs) + tx + (14 if ic else 18))
    body = (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="17" class="panel ln"/>'
            f'{icon(ic, 14, 9, 16) if ic else ""}'
            f'<text x="{tx}" y="21.5" class="sg txt" font-size="{fs}">{escape(text)}</text>')
    write(f"link-{slug}.svg", svg(w, h, body, text, [(SG, text)]))


# ---------------------------------------------------------------- 6. 軌道圖（裝飾）
def orbit():
    w, h = 860, 300
    cx, cy = 430, 150
    # (分類, 專案數, 標籤在軌道上的角度)
    cats = [("Professional", 1, -90), ("AI & ML", 1, -140), ("Web & Data", 2, -40), ("Game Tools", 2, -155),
            ("Archive", 1, -25)]
    parts, labels, texts = [], [], ""
    for i, (name, n, ang) in enumerate(cats):
        rx = 130 + i * 60
        ry = rx * 0.32
        d = f"M{cx - rx},{cy} a{rx},{ry} 0 1,0 {2 * rx},0 a{rx},{ry} 0 1,0 {-2 * rx},0"
        parts.append(f'<path id="o{i}" d="{d}" fill="none" class="ln" style="stroke:var(--line)" stroke-width="1.2"/>')
        dur = 40 + i * 22
        for k in range(n):
            parts.append(f'<circle r="{4 if i % 2 else 3.5}" class="{"gold" if i % 2 == 0 else "vio"}">'
                         f'<animateMotion dur="{dur}s" begin="-{dur * (k / n + i * 0.13):.1f}s" repeatCount="indefinite">'
                         f'<mpath href="#o{i}"/></animateMotion></circle>')
        tw = JB.width(name, 11.5)
        lx, ly = cx + rx * math.cos(math.radians(ang)), cy + ry * math.sin(math.radians(ang))
        labels.append(f'<rect x="{lx - tw / 2 - 9:.1f}" y="{ly - 10:.1f}" width="{tw + 18:.1f}" height="20" rx="10" class="bg ln"/>'
                      f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" class="jb txt" font-size="11.5">{escape(name)}</text>')
        texts += name
    body = f'''<defs>
<radialGradient id="halo">{stop(0, "violet", 0.5)}{stop(0.5, "violet", 0.12)}{stop(1, "violet", 0)}</radialGradient>
<linearGradient id="disk" x1="0" y1="0" x2="1" y2="0">{stop(0, "accent", 0.1)}{stop(0.5, "gold")}{stop(1, "accent", 0.1)}</linearGradient>
<filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>
<clipPath id="front"><rect x="-80" y="0" width="160" height="80"/></clipPath>
</defs>
<rect width="{w}" height="{h}" rx="14" class="bg"/>
{"".join(parts)}
<g transform="translate({cx} {cy})">
<circle r="90" fill="url(#halo)"/>
<g transform="scale(1 0.3)"><circle r="56" fill="none" stroke="url(#disk)" stroke-width="12" filter="url(#gl)">
<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="40s" repeatCount="indefinite"/></circle></g>
<circle r="26" fill="none" style="stroke:var(--gold)" stroke-width="2" opacity="0.8"/>
<circle r="24" style="fill:var(--hole)"/>
<g transform="scale(1 0.3)"><g clip-path="url(#front)"><circle r="56" fill="none" stroke="url(#disk)" stroke-width="7"/></g></g>
</g>
{"".join(labels)}'''
    write("orbit.svg", svg(w, h, body, "Decorative orbit map of project categories: " + ", ".join(c[0] for c in cats),
                           [(JB, texts)]))


# ---------------------------------------------------------------- 7. 頂部橫幅、底部收尾
NAME = "Hi, I'm ChenYu Hsu 👋"
DESC = "AI + Full-Stack Developer from Taiwan · Building and learning in public"


def stars(seed, n, w, h, avoid=None):
    import random
    rng = random.Random(seed)
    out = []
    for i in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.choice([0.6, 0.8, 1.0, 1.3])
        o = rng.uniform(0.25, 0.8)
        d = rng.uniform(3, 7)
        if avoid and avoid[0] < x < avoid[2] and avoid[1] < y < avoid[3]:
            continue
        anim = (f'<animate attributeName="opacity" values="{o:.2f};0.1;{o:.2f}" dur="{d:.1f}s" '
                'repeatCount="indefinite"/>') if i % 5 == 0 else ""
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" style="fill:var(--star)" opacity="{o:.2f}">{anim}</circle>')
    return "".join(out)


def banner():
    w, h = 1200, 300
    rot = '<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="{d}s" repeatCount="indefinite"/>'

    def disk(extra=""):
        return (f'<g{extra}>'
                f'<circle r="150" fill="none" stroke="url(#disk)" stroke-width="40" opacity="0.55" filter="url(#glow)">{rot.format(d=60)}</circle>'
                f'<circle r="142" fill="none" stroke="url(#disk)" stroke-width="12">{rot.format(d=60)}</circle>'
                f'<circle r="165" fill="none" style="stroke:var(--gold)" stroke-width="2" stroke-dasharray="2 14" opacity="0.6">{rot.format(d=90)}</circle>'
                '</g>')

    body = f'''<defs>
<radialGradient id="halo">{stop(0, "violet", 0.55)}{stop(0.5, "violet", 0.15)}{stop(1, "violet", 0)}</radialGradient>
<linearGradient id="disk" x1="0" y1="0" x2="1" y2="0">{stop(0, "accent", 0.1)}{stop(0.35, "accent")}{stop(0.6, "gold")}{stop(1, "accent", 0.1)}</linearGradient>
<linearGradient id="name" x1="0" y1="0" x2="1" y2="0">{stop(0, "gold")}{stop(1, "accent")}</linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.5"/></filter>
<clipPath id="front"><rect x="-260" y="0" width="520" height="260"/></clipPath>
<clipPath id="upper"><rect x="-120" y="-120" width="240" height="120"/></clipPath>
<clipPath id="frame"><rect width="{w}" height="{h}" rx="16"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{w}" height="{h}" class="bg"/>
{stars(413, 110, w, h, avoid=(150, 60, 400, 240))}
<g transform="translate(275 150)">
<circle r="150" fill="url(#halo)"><animate attributeName="r" values="145;158;145" dur="12s" repeatCount="indefinite"/></circle>
<g transform="rotate(-10) scale(1 0.24)">{disk()}</g>
<g clip-path="url(#upper)"><ellipse rx="78" ry="72" fill="none" style="stroke:var(--accent)" stroke-width="7" opacity="0.7" filter="url(#soft)"/></g>
<circle r="64" fill="none" style="stroke:var(--gold)" stroke-width="2.5" opacity="0.85" filter="url(#soft)"><animate attributeName="opacity" values="0.6;0.95;0.6" dur="8s" repeatCount="indefinite"/></circle>
<circle r="60" style="fill:var(--hole)"/>
<g transform="rotate(-10) scale(1 0.24)">{disk(' clip-path="url(#front)"')}</g>
</g>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="none" class="ln"/>
<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="0.3s" dur="2.5s" fill="freeze"/>
<text x="500" y="140" class="sg" font-size="46" fill="url(#name)">{escape(NAME)}</text>
<text x="502" y="184" class="sgr txt" font-size="18">{escape(DESC)}</text>
<rect x="502" y="206" width="120" height="2" rx="1" class="vio" opacity="0.8"/>
</g>'''
    write("banner.svg", svg(w, h, body, NAME + " — " + DESC, [(SG, NAME), (SGR, DESC)]))


def footer():
    w, h = 1200, 110
    text = "Thanks for stopping by!"
    body = f'''<defs><radialGradient id="h">{stop(0.55, "accent", 0.5)}{stop(0.75, "violet", 0.2)}{stop(1, "bg", 0)}</radialGradient>
<clipPath id="c"><rect width="{w}" height="{h}" rx="16"/></clipPath></defs>
<g clip-path="url(#c)">
<rect width="{w}" height="{h}" class="bg"/>
{stars(1993, 50, w, h)}
<ellipse cx="600" cy="150" rx="660" ry="100" fill="url(#h)"><animate attributeName="opacity" values="0.75;1;0.75" dur="10s" repeatCount="indefinite"/></ellipse>
<ellipse cx="600" cy="150" rx="560" ry="66" style="fill:var(--horizon);stroke:var(--gold)" stroke-opacity="0.6" stroke-width="1.5"/>
</g>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="none" class="ln"/>
<text x="600" y="58" text-anchor="middle" class="sg gold" font-size="20">{text}</text>'''
    write("footer.svg", svg(w, h, body, text, [(SG, text)]))


# ---------------------------------------------------------------- 產出
def build_all():
    for slug, text in [("about", "About Me"), ("stack", "Tech Stack"), ("stats", "Stats"),
                       ("snake", "Contribution Snake"), ("projects", "Featured Projects")]:
        title(slug, text, main=True)
    for slug, text in [("professional", "Professional"), ("ai-ml", "AI & ML"), ("web-data", "Web & Data"),
                       ("game-tools", "Game Tools"), ("archive", "Archive")]:
        title(slug, text, main=False)

    # 說明文字取自 repo description 或 main README 原文（只截取，不改寫）
    card("echoai", "ECHOAi", "Brand website for ECHOAi, SaySing's new AI product line (Next.js) — developed by me.",
         "Next.js", ["LIVE"])
    card("aitown", "AITown", "Generative multi-agent social simulation", "Python", [])
    card("taiwan-weather-map", "taiwan-weather-map", "Windy-style real-time weather map for Taiwan",
         "TypeScript", ["LIVE"])
    card("lol-worlds-2026", "lol-worlds-2026",
         "LoL Worlds 2026 visualizer — schedule, scores, brackets & match details", "TypeScript", ["LIVE"])
    card("deskrawl-monitor", "deskrawl-monitor",
         "Steam build monitor for Deskrawl — Discord alerts + auto-translated patch notes", None, [])
    card("monster-hunter", "Monster-Hunter-equipment-search-tool",
         "Skill-driven build finder for three Monster Hunter games (Rise: Sunbreak, World: Iceborne, Wilds)",
         "TypeScript", ["LIVE"])
    card("aifinalproject", "AIFinalProject",
         "end-to-end predictive maintenance prototype (ML + MLOps loop, FastAPI + Next.js)", "Python", ["ARCHIVE"])

    left, right = ["Languages", "AI / ML"], ["Backend / Data", "Frontend", "Tools / Deploy"]
    need = lambda gs: 20 + sum(22 + ((len(TECH[g]) + 2) // 3) * 38 + 16 for g in gs) - 16 + 20
    panel_h = max(need(left), need(right))  # 兩張等高，並排時對齊
    tech_panel("left", left, panel_h)
    tech_panel("right", right, panel_h)
    about_card()
    link_pill("personal-page", "googlechrome", "Personal Page")
    link_pill("linkedin", None, "LinkedIn")
    orbit()
    banner()
    footer()



if __name__ == "__main__":
    for theme, suffix in (("dark", ""), ("light", "-light")):
        PALETTE, SUFFIX = PALETTES[theme], suffix
        build_all()
    for p in sorted(OUT.glob("*.svg")):
        print(f"{p.stat().st_size / 1024:6.1f} KB  {p.name}")
