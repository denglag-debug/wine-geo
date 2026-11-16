# -*- coding: utf-8 -*-
"""
charts.py — генераторы картинок (SVG) для страниц портала.

Взят из пилота Бургёя; всё, что было «зашито» под Бургёй (рамка карты,
подписи рек, название на мини-карте), теперь передаётся параметрами.

Каждая функция возвращает строку с готовым SVG-кодом. SVG — это векторная
картинка, описанная текстом: её можно вставить прямо в HTML, она не зависит
от интернета и одинаково чётко выглядит на экране и в PDF.

Наведение мыши на столбик/сектор показывает подсказку: для этого внутри
каждого элемента лежит тег <title> — браузер сам рисует всплывающий текст.
"""
import json
import zlib
import math
from html import escape

# ---------------------------------------------------------------------------
# Палитра. Цвета вина — «смысловые» (красное = бордовый, розовое = розовый),
# остальные — нейтральные, чтобы не спорить с ними.
# ---------------------------------------------------------------------------
INK = "#1f1a17"        # основной текст
INK2 = "#5b524b"       # вторичный текст
MUTED = "#8c837b"      # подписи осей
GRID = "#e6dfd6"       # линии сетки
PAPER = "#fbf8f3"      # фон
RED = "#8e1b3a"        # красное вино / Каберне Фран
RED2 = "#5a0f25"       # Каберне Совиньон (темнее)
ROSE = "#e58fa6"       # розовое вино
BLUE = "#2a6fb8"       # осадки, вода
WARM = "#d06a2c"       # температура
SUN = "#d99a00"        # солнце
GREEN = "#7f9a5a"      # виноградники на карте (нейтральный)
LAND = "#efe9df"       # суша на карте
FONT = "font-family:inherit"


def _svg_open(w, h, label):
    """Начало SVG: размеры, адаптивность (viewBox) и подпись для экранных дикторов."""
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" '
            f'aria-label="{escape(label)}" xmlns="http://www.w3.org/2000/svg" '
            f'style="{FONT};max-width:{w}px;display:block">')


def fmt(n, d=0):
    """Число по-русски: пробел между тысячами, запятая в дробях (63 089; 42,5)."""
    s = f"{n:,.{d}f}".replace(",", " ").replace(".", ",")
    return s


# ---------------------------------------------------------------------------
# 1. «Как представить площадь»: квадраты, площадь которых пропорциональна
#    площади виноградников. Глаз хорошо сравнивает площади квадратов.
# ---------------------------------------------------------------------------
def size_squares(items):
    """items: список (название, гектары, подпись-источник, выделить?)."""
    W, H = 760, 330
    base = H - 60                       # нижняя линия, на которой стоят квадраты
    max_ha = max(i[1] for i in items)
    max_side = 220                      # сторона самого большого квадрата, px
    out = [_svg_open(W, H, "Сравнение площади виноградников квадратами")]
    x = 10
    for name, ha, note, hl in items:
        side = max_side * math.sqrt(ha / max_ha)
        side = max(side, 6)
        fill = RED if hl else "#c9bdb0"
        out.append(f'<g><title>{escape(name)}: {fmt(ha)} га ({escape(note)})</title>'
                   f'<rect x="{x + (max(side, 140) - side) / 2:.1f}" y="{base - side:.1f}" width="{side:.1f}" height="{side:.1f}" '
                   f'rx="2" fill="{fill}"/></g>')
        cx = x + max(side, 140) / 2
        out.append(f'<text x="{cx:.1f}" y="{base + 20}" text-anchor="middle" font-size="13" '
                   f'font-weight="{700 if hl else 500}" fill="{INK}">{escape(name)}</text>')
        out.append(f'<text x="{cx:.1f}" y="{base + 38}" text-anchor="middle" font-size="12" '
                   f'fill="{INK2}">{fmt(ha)} га</text>')
        x += max(side, 140) + 24
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# 2. Столбики по годам (производство), с разбивкой красное/розовое.
# ---------------------------------------------------------------------------
def stacked_years(rows, title, unit="гл"):
    """rows: список (год, красное, розовое). Рисует вертикальные столбики."""
    W, H = 760, 300
    L, R, T, B = 60, 20, 20, 40
    n = len(rows)
    maxv = max(r + p for _, r, p in rows)
    top = math.ceil(maxv / 20000) * 20000
    ph = H - T - B
    bw = (W - L - R) / n
    out = [_svg_open(W, H, title)]
    # сетка и подписи оси Y
    for v in range(0, top + 1, 20000):
        y = T + ph - ph * v / top
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{fmt(v)}</text>')
    for i, (yr, red, rose) in enumerate(rows):
        x = L + i * bw + bw * 0.2
        w = bw * 0.6
        hr = ph * red / top
        hp = ph * rose / top
        y0 = T + ph
        tip = f"{yr}: всего {fmt(red + rose)} {unit} (красное {fmt(red)}, розовое {fmt(rose)})"
        out.append(f'<g><title>{tip}</title>'
                   f'<rect x="{x:.1f}" y="{y0 - hr:.1f}" width="{w:.1f}" height="{hr:.1f}" fill="{RED}"/>'
                   f'<rect x="{x:.1f}" y="{y0 - hr - hp - 2:.1f}" width="{w:.1f}" height="{hp:.1f}" rx="2" fill="{ROSE}"/>'
                   f'<rect x="{L + i * bw:.1f}" y="{T}" width="{bw:.1f}" height="{ph}" fill="transparent"/></g>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{H - B + 18}" text-anchor="middle" font-size="12" fill="{INK2}">{yr}</text>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{y0 - hr - hp - 8:.1f}" text-anchor="middle" font-size="10.5" fill="{INK2}">{fmt((red + rose) / 1000, 1)}</text>')
    out.append("</svg>")
    return "".join(out)


def simple_bars(rows, title, unit, color=MUTED, highlight=None, step=100000, decimals=0, H=280):
    """Простые вертикальные столбики: rows = [(подпись, значение, примечание)]."""
    W = 760
    L, R, T, B = 70, 20, 24, 44
    maxv = max(r[1] for r in rows)
    top = math.ceil(maxv / step) * step
    ph = H - T - B
    bw = (W - L - R) / len(rows)
    out = [_svg_open(W, H, title)]
    for v in range(0, int(top) + 1, int(step)):
        y = T + ph - ph * v / top
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{L - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{fmt(v)}</text>')
    for i, (lab, v, note) in enumerate(rows):
        x = L + i * bw + bw * 0.22
        w = bw * 0.56
        h = ph * v / top
        c = RED if (highlight and lab in highlight) else color
        out.append(f'<g><title>{escape(lab)}: {fmt(v, decimals)} {unit}{(" — " + escape(note)) if note else ""}</title>'
                   f'<path d="M{x:.1f},{T + ph:.1f} V{T + ph - h + 3:.1f} q0,-3 3,-3 H{x + w - 3:.1f} q3,0 3,3 V{T + ph:.1f} Z" fill="{c}"/>'
                   f'<rect x="{L + i * bw:.1f}" y="{T}" width="{bw:.1f}" height="{ph}" fill="transparent"/></g>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{T + ph - h - 6:.1f}" text-anchor="middle" font-size="11" fill="{INK2}">{fmt(v, decimals)}</text>')
        out.append(f'<text x="{x + w / 2:.1f}" y="{H - B + 18}" text-anchor="middle" font-size="12" fill="{INK2}">{escape(lab)}</text>')
        if note:
            out.append(f'<text x="{x + w / 2:.1f}" y="{H - B + 33}" text-anchor="middle" font-size="10.5" fill="{MUTED}">{escape(note)}</text>')
    out.append("</svg>")
    return "".join(out)


def hbars(rows, title, unit, maxv=None, decimals=0):
    """Горизонтальные столбики: rows = [(подпись, значение, цвет, пояснение)]."""
    W = 760
    rowh = 40
    L = 290
    H = len(rows) * rowh + 16
    maxv = maxv or max(r[1] for r in rows)
    pw = W - L - 70
    out = [_svg_open(W, H, title)]
    for i, (lab, v, c, note) in enumerate(rows):
        y = 8 + i * rowh
        w = pw * v / maxv
        out.append(f'<g><title>{escape(lab)}: {fmt(v, decimals)} {unit}</title>'
                   f'<rect x="{L}" y="{y + 8}" width="{w:.1f}" height="18" rx="3" fill="{c}"/></g>')
        out.append(f'<text x="{L - 10}" y="{y + 18}" text-anchor="end" font-size="13" fill="{INK}">{escape(lab)}</text>')
        if note:
            out.append(f'<text x="{L - 10}" y="{y + 33}" text-anchor="end" font-size="10.5" fill="{MUTED}">{escape(note)}</text>')
        out.append(f'<text x="{L + w + 8:.1f}" y="{y + 22}" font-size="13" font-weight="600" fill="{INK}">{fmt(v, decimals)} {unit}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# 3. Двухуровневое кольцо: внутри — цвета вина, снаружи — сорта.
# ---------------------------------------------------------------------------
def _arc(cx, cy, r0, r1, a0, a1):
    """Путь кольцевого сектора от угла a0 до a1 (в долях круга 0..1)."""
    def pt(r, a):
        ang = 2 * math.pi * a - math.pi / 2
        return cx + r * math.cos(ang), cy + r * math.sin(ang)
    large = 1 if (a1 - a0) > 0.5 else 0
    x0, y0 = pt(r1, a0)
    x1, y1 = pt(r1, a1)
    x2, y2 = pt(r0, a1)
    x3, y3 = pt(r0, a0)
    return (f"M{x0:.2f},{y0:.2f} A{r1},{r1} 0 {large} 1 {x1:.2f},{y1:.2f} "
            f"L{x2:.2f},{y2:.2f} A{r0},{r0} 0 {large} 0 {x3:.2f},{y3:.2f} Z")


def sunburst(inner, outer, title):
    """
    inner: [(название, доля 0..1, цвет)] — цвета вина;
    outer: [(название, доля 0..1, цвет, штриховка?)] — сорта по кругу в том же порядке.
    """
    W, H = 760, 340
    cx, cy = 170, 170
    out = [_svg_open(W, H, title),
           '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" '
           'patternTransform="rotate(45)"><rect width="6" height="6" fill="#d9a3b1"/>'
           f'<line x1="0" y1="0" x2="0" y2="6" stroke="{RED2}" stroke-width="2.4"/></pattern></defs>']
    a = 0
    for name, share, col in inner:
        out.append(f'<g><title>{escape(name)}: {fmt(share * 100, 1)} %</title>'
                   f'<path d="{_arc(cx, cy, 58, 104, a + 0.002, a + share - 0.002)}" fill="{col}" stroke="{PAPER}" stroke-width="2"/></g>')
        a += share
    a = 0
    for name, share, col, hatch in outer:
        fill = "url(#hatch)" if hatch else col
        out.append(f'<g><title>{escape(name)}</title>'
                   f'<path d="{_arc(cx, cy, 110, 156, a + 0.002, a + share - 0.002)}" fill="{fill}" stroke="{PAPER}" stroke-width="2"/></g>')
        a += share
    out.append(f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="13" fill="{INK2}">цвет</text>')
    out.append(f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="13" fill="{INK2}">и сорт</text>')
    # легенда справа
    lx, ly = 370, 40
    out.append(f'<text x="{lx}" y="{ly}" font-size="12" font-weight="700" fill="{MUTED}" letter-spacing=".06em">ВНУТРЕННЕЕ КОЛЬЦО — ЦВЕТ ВИНА</text>')
    ly += 26
    for name, share, col in inner:
        out.append(f'<rect x="{lx}" y="{ly - 12}" width="14" height="14" rx="3" fill="{col}"/>'
                   f'<text x="{lx + 22}" y="{ly}" font-size="14" fill="{INK}">{escape(name)} — <tspan font-weight="700">{fmt(share * 100, 0)} %</tspan></text>')
        ly += 24
    ly += 14
    out.append(f'<text x="{lx}" y="{ly}" font-size="12" font-weight="700" fill="{MUTED}" letter-spacing=".06em">ВНЕШНЕЕ КОЛЬЦО — СОРТА</text>')
    ly += 26
    for name, share, col, hatch in outer:
        fill = "url(#hatch)" if hatch else col
        lines = name.split("\n")
        out.append(f'<rect x="{lx}" y="{ly - 12}" width="14" height="14" rx="3" fill="{fill}"/>')
        for j, ln in enumerate(lines):
            out.append(f'<text x="{lx + 22}" y="{ly + j * 18}" font-size="{14 if j == 0 else 12}" fill="{INK if j == 0 else INK2}">{escape(ln)}</text>')
        ly += 18 * len(lines) + 10
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# 4. Таймлайн — лента с точками.
# ---------------------------------------------------------------------------
def timeline(events, title="Таймлайн истории"):
    """events: [(подпись даты, позиция 0..1, короткий текст, важное?)]. Горизонтальная лента."""
    W, H = 760, 170
    L, R = 30, 30
    y = 70
    out = [_svg_open(W, H, title)]
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{y}" y2="{y}" stroke="{INK2}" stroke-width="2"/>')
    for i, (lab, pos, txt, big) in enumerate(events):
        x = L + (W - L - R) * pos
        up = i % 2 == 0
        out.append(f'<g><title>{escape(lab)} — {escape(txt)}</title>'
                   f'<circle cx="{x:.1f}" cy="{y}" r="{7 if big else 5}" fill="{RED if big else PAPER}" stroke="{RED}" stroke-width="2"/></g>')
        ty = y - 18 if up else y + 28
        anc = "start" if pos == 0 else ("end" if pos == 1 else "middle")
        tx = x - 6 if pos == 0 else (x + 6 if pos == 1 else x)
        out.append(f'<text x="{tx:.1f}" y="{ty}" text-anchor="{anc}" font-size="13" font-weight="700" fill="{INK}">{escape(lab)}</text>')
        out.append(f'<text x="{tx:.1f}" y="{ty + (-16 if up else 16)}" text-anchor="{anc}" font-size="11" fill="{INK2}">{escape(txt)}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# 5. Климат: температура (полоса мин–макс + линия средней) и осадки.
#    Две отдельные диаграммы — никогда не смешиваем две шкалы на одной оси.
# ---------------------------------------------------------------------------
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def climate_temp(tmin, tmax, tmean, title="Температура по месяцам"):
    W, H = 760, 280
    L, R, T, B = 50, 20, 20, 34
    lo, hi = 0, 30
    ph, pw = H - T - B, W - L - R
    X = lambda i: L + pw * (i + 0.5) / 12
    Y = lambda v: T + ph - ph * (v - lo) / (hi - lo)
    out = [_svg_open(W, H, title)]
    for v in range(lo, hi + 1, 5):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}"/>'
                   f'<text x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{v}°</text>')
    band = "M" + " L".join(f"{X(i):.1f},{Y(t):.1f}" for i, t in enumerate(tmax)) + " L" + \
           " L".join(f"{X(i):.1f},{Y(t):.1f}" for i, t in reversed(list(enumerate(tmin)))) + " Z"
    out.append(f'<path d="{band}" fill="{WARM}" opacity=".18"/>')
    for series, col, w in ((tmax, WARM, 1.5), (tmin, BLUE, 1.5), (tmean, INK, 2.2)):
        out.append(f'<polyline points="{" ".join(f"{X(i):.1f},{Y(t):.1f}" for i, t in enumerate(series))}" '
                   f'fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>')
    for i in range(12):
        out.append(f'<g><title>{MONTHS[i]}: мин {fmt(tmin[i], 1)}°, средняя {fmt(tmean[i], 1)}°, макс {fmt(tmax[i], 1)}°</title>'
                   f'<rect x="{X(i) - pw / 24:.1f}" y="{T}" width="{pw / 12:.1f}" height="{ph}" fill="transparent"/>'
                   f'<circle cx="{X(i):.1f}" cy="{Y(tmean[i]):.1f}" r="3.5" fill="{INK}"/></g>'
                   f'<text x="{X(i):.1f}" y="{H - 12}" text-anchor="middle" font-size="12" fill="{INK2}">{MONTHS[i]}</text>')
    # прямые подписи линий (справа) вместо отдельной легенды
    out.append(f'<text x="{X(6):.1f}" y="{Y(tmax[6]) - 8:.1f}" text-anchor="middle" font-size="11.5" fill="{WARM}" font-weight="600">макс. днём {fmt(tmax[6], 1)}°</text>')
    out.append(f'<text x="{X(6):.1f}" y="{Y(tmin[6]) + 18:.1f}" text-anchor="middle" font-size="11.5" fill="{BLUE}" font-weight="600" dy="6">мин. ночью {fmt(tmin[6], 1)}°</text>')
    out.append(f'<text x="{X(1):.1f}" y="{Y(tmax[1]) - 10:.1f}" text-anchor="middle" font-size="11.5" fill="{INK}">средняя</text>')
    out.append("</svg>")
    return "".join(out)


def climate_bars(values, title, unit, color, step, decimals=1, H=220, label_dec=0):
    W = 760
    L, R, T, B = 50, 20, 22, 30
    ph, pw = H - T - B, W - L - R
    top = math.ceil(max(values) / step) * step
    out = [_svg_open(W, H, title)]
    for v in range(0, int(top) + 1, int(step)):
        y = T + ph - ph * v / top
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>'
                   f'<text x="{L - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{v}</text>')
    bw = pw / 12
    for i, v in enumerate(values):
        h = ph * v / top
        x = L + i * bw + bw * 0.2
        w = bw * 0.6
        out.append(f'<g><title>{MONTHS[i]}: {fmt(v, decimals)} {unit}</title>'
                   f'<path d="M{x:.1f},{T + ph:.1f} V{T + ph - h + 3:.1f} q0,-3 3,-3 H{x + w - 3:.1f} q3,0 3,3 V{T + ph:.1f} Z" fill="{color}"/>'
                   f'<rect x="{L + i * bw:.1f}" y="{T}" width="{bw:.1f}" height="{ph}" fill="transparent"/></g>'
                   f'<text x="{x + w / 2:.1f}" y="{H - 10}" text-anchor="middle" font-size="12" fill="{INK2}">{MONTHS[i]}</text>')
        if v > 0:
            out.append(f'<text x="{x + w / 2:.1f}" y="{T + ph - h - 5:.1f}" text-anchor="middle" font-size="10" fill="{INK2}">{fmt(v, label_dec)}</text>')
    out.append("</svg>")
    return "".join(out)


def climate_panel(c, title="Климат по месяцам"):
    """
    Весь климат на ОДНОЙ картинке: четыре полосы друг под другом с общей шкалой месяцев.
      1) температура — полоса от средней ночной до средней дневной + линия средней;
      2) осадки, мм; 3) солнечные часы; 4) дни с заморозком.
    У каждой полосы своя шкала (разные единицы на одной оси не смешиваем), но месяцы общие —
    глаз сразу видит, что, например, самый солнечный месяц совпадает с самым сухим.
    c — словарь climate из page.yaml (tmin, tmax, tmean, rain, sun, frost).
    """
    W = 760
    L, R = 118, 16                      # слева — место под названия полос
    pw = W - L - R
    X = lambda i: L + pw * (i + 0.5) / 12
    bw = pw / 12
    rows = [("temp", 150)] + [(k, h) for k, h in (("rain", 78), ("sun", 78), ("frost", 62)) if c.get(k)]
    H = 14 + sum(h + 18 for _, h in rows) + 22
    out = [_svg_open(W, H, title)]
    y = 14
    # вертикальные «колонки» месяцев — чередующийся фон, чтобы взгляд не терял месяц
    for i in range(0, 12, 2):
        out.append(f'<rect x="{L + i * bw:.1f}" y="8" width="{bw:.1f}" height="{H - 34}" fill="#f6f1ea" opacity=".6"/>')

    def label(y0, h, name, unit, col):
        out.append(f'<text x="{L - 12}" y="{y0 + h / 2 - 2:.0f}" text-anchor="end" font-size="13" font-weight="700" fill="{col}">{name}</text>'
                   f'<text x="{L - 12}" y="{y0 + h / 2 + 14:.0f}" text-anchor="end" font-size="11" fill="{MUTED}">{unit}</text>')

    for kind, h in rows:
        if kind == "temp":
            lo, hi = min(c["tmin"]) - 2, max(c["tmax"]) + 3
            Y = lambda v, y0=y: y0 + h - h * (v - lo) / (hi - lo)
            band = "M" + " L".join(f"{X(i):.1f},{Y(t):.1f}" for i, t in enumerate(c["tmax"])) + " L" + \
                   " L".join(f"{X(i):.1f},{Y(t):.1f}" for i, t in reversed(list(enumerate(c["tmin"])))) + " Z"
            out.append(f'<path d="{band}" fill="{WARM}" opacity=".2"/>')
            tmean = c.get("tmean") or [(a + b) / 2 for a, b in zip(c["tmin"], c["tmax"])]
            c = dict(c, tmean=tmean)
            for ser, col, w in ((c["tmax"], WARM, 1.5), (c["tmin"], BLUE, 1.5), (c["tmean"], INK, 2.2)):
                out.append(f'<polyline points="{" ".join(f"{X(i):.1f},{Y(t):.1f}" for i, t in enumerate(ser))}" fill="none" stroke="{col}" stroke-width="{w}"/>')
            for i in range(12):
                out.append(f'<g><title>{MONTHS[i]}: ночью {fmt(c["tmin"][i], 1)}°, в среднем {fmt(c["tmean"][i], 1)}°, днём {fmt(c["tmax"][i], 1)}°</title>'
                           f'<rect x="{L + i * bw:.1f}" y="{y}" width="{bw:.1f}" height="{h}" fill="transparent"/>'
                           f'<circle cx="{X(i):.1f}" cy="{Y(c["tmean"][i]):.1f}" r="3" fill="{INK}"/></g>')
            j = max(range(12), key=lambda i: c["tmax"][i])
            out.append(f'<text x="{X(j):.1f}" y="{Y(c["tmax"][j]) - 7:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="{WARM}">днём {fmt(c["tmax"][j], 0)}°</text>')
            out.append(f'<text x="{X(j):.1f}" y="{Y(c["tmin"][j]) + 16:.1f}" text-anchor="middle" font-size="12" font-weight="600" fill="{BLUE}">ночью {fmt(c["tmin"][j], 0)}°</text>')
            k = min(range(12), key=lambda i: c["tmin"][i])
            out.append(f'<text x="{X(k):.1f}" y="{Y(c["tmin"][k]) + 16:.1f}" text-anchor="middle" font-size="12" fill="{BLUE}">{fmt(c["tmin"][k], 0)}°</text>')
            label(y, h, "Температура", "°C", INK)
        else:
            col, name, unit, dec = {
                "rain": (BLUE, "Осадки", "мм", 0),
                "sun": (SUN, "Солнце", "часов", 0),
                "frost": ("#7d97b8", "Заморозки", "дней ≤ 0 °C", 1),
            }[kind]
            vals = c[kind]          # берём только тот ряд, который есть (у Телави нет солнца и заморозков)
            top = max(vals) or 1
            for i, v in enumerate(vals):
                bh = (h - 16) * v / top
                x = L + i * bw + bw * 0.22
                out.append(f'<g><title>{MONTHS[i]}: {fmt(v, dec)} {unit}</title>'
                           f'<rect x="{x:.1f}" y="{y + h - bh:.1f}" width="{bw * .56:.1f}" height="{bh:.1f}" rx="2" fill="{col}"/></g>')
                if v > 0:
                    out.append(f'<text x="{x + bw * .28:.1f}" y="{y + h - bh - 4:.1f}" text-anchor="middle" font-size="11" fill="{INK2}">{fmt(v, dec if v < 10 else 0)}</text>')
            label(y, h, name, unit, col)
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y + h:.1f}" y2="{y + h:.1f}" stroke="{GRID}"/>')
        y += h + 18
    for i in range(12):
        out.append(f'<text x="{X(i):.1f}" y="{y + 4}" text-anchor="middle" font-size="12" fill="{INK2}">{MONTHS[i]}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------------------
# 7. Карты. Проекция простая: долгота сжимается на cos(широты) — для
#    небольшой территории этого достаточно, расстояния почти не искажаются.
# ---------------------------------------------------------------------------
def _proj(x0, x1, y0, y1, W):
    c = math.cos(math.radians((y0 + y1) / 2))
    k = W / ((x1 - x0) * c)
    H = (y1 - y0) * k
    return (lambda lon, lat: ((lon - x0) * c * k, (y1 - lat) * k)), H, k


def _rings(geom):
    t = geom["type"]
    if t == "Polygon":
        return [geom["coordinates"]]
    if t == "MultiPolygon":
        return geom["coordinates"]
    return []


def _lines(geom):
    t = geom["type"]
    if t == "LineString":
        return [geom["coordinates"]]
    if t == "MultiLineString":
        return geom["coordinates"]
    if t == "GeometryCollection":
        r = []
        for g in geom["geometries"]:
            r += _lines(g)
        return r
    return []


def _poly_path(P, polys):
    d = []
    for poly in polys:
        for ring in poly:
            d.append("M" + " L".join("%.1f,%.1f" % P(*p) for p in ring) + "Z")
    return "".join(d)


def detail_map(geo_dir, aoc_codes, partial_codes, own_aoc_codes, towns,
               bbox=(-0.16, 0.74, 47.12, 47.46), river_labels=(), main_river="Loire",
               title="Карта аппелласьона"):
    """Подробная карта аппелласьона: коммуны AOC, реки, города, масштаб.

    bbox — рамка карты (долгота от, долгота до, широта от, широта до);
    river_labels — подписи рек: [(текст, долгота, широта, угол поворота)];
    main_river — какая река рисуется толще остальных.
    """
    x0, x1, y0, y1 = bbox
    W = 760
    P, H, k = _proj(x0, x1, y0, y1, W)
    com = json.load(open(geo_dir + "/communes-zone.geojson"))["features"]
    riv = json.load(open(geo_dir + "/rivers-zone.geojson"))["features"]
    out = [_svg_open(W, round(H), title),
           '<defs><pattern id="mhatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<rect width="7" height="7" fill="#e9c3cc"/><line x1="0" y1="0" x2="0" y2="7" stroke="{RED}" stroke-width="2.2"/></pattern>'
           f'<clipPath id="mclip"><rect width="{W}" height="{H:.0f}"/></clipPath></defs>',
           f'<rect width="{W}" height="{H:.0f}" fill="#f6f2ec"/><g clip-path="url(#mclip)">']
    labels = []
    for f in com:
        code = f["properties"]["code"]
        polys = _rings(f["geometry"])
        if code in aoc_codes:
            fill = RED
            op = ".75" if code in partial_codes else ".9"
        elif code in own_aoc_codes:
            fill, op = "url(#mhatch)", "1"
        else:
            fill, op = LAND, "1"
        out.append(f'<path d="{_poly_path(P, polys)}" fill="{fill}" fill-opacity="{op}" stroke="#fff" stroke-width="0.8">'
                   f'<title>{escape(f["properties"]["nom"])}</title></path>')
    for f in riv:
        for ln in _lines(f["geometry"]):
            d = "M" + " L".join("%.1f,%.1f" % P(*p) for p in ln)
            w = 5 if f["properties"]["name"] == main_river else 3
            out.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" opacity=".8"/>')
    # подписи рек
    for name, lon, lat, rot in river_labels:
        x, y = P(lon, lat)
        out.append(f'<text x="{x:.0f}" y="{y:.0f}" transform="rotate({rot} {x:.0f} {y:.0f})" font-size="15" font-style="italic" fill="{BLUE}" '
                   f'stroke="#f6f2ec" stroke-width="3" paint-order="stroke">{name}</text>')
    # города и коммуны
    for name, lon, lat, kind, dx, dy in towns:
        x, y = P(lon, lat)
        if kind == "town":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{INK}" stroke="#fff" stroke-width="1.5"/>')
            fs, fw, col = 13, 600, INK
        elif kind == "sight":
            out.append(f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" transform="rotate(45 {x:.1f} {y:.1f})" fill="{SUN}" stroke="#fff" stroke-width="1.2"/>')
            fs, fw, col = 11.5, 500, INK2
        else:  # aoc-коммуна — подпись поверх заливки
            fs, fw, col = 11.5, 600, "#fff"
        stroke = 'stroke="#f6f2ec" stroke-width="3" paint-order="stroke"' if kind != "aoc" else 'stroke="#5a0f25" stroke-width="2.5" paint-order="stroke"'
        out.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" font-size="{fs}" font-weight="{fw}" fill="{col}" {stroke} '
                   f'text-anchor="{"middle" if kind == "aoc" else "start"}">{escape(name)}</text>')
    out.append("</g>")
    # масштабная линейка 10 км: 1° широты ≈ 111 км
    px10 = k * 10 / 111.2
    sx, sy = 20, H - 24
    out.append(f'<rect x="{sx - 8}" y="{sy - 22}" width="{px10 + 70:.0f}" height="36" rx="4" fill="#fff" opacity=".85"/>'
               f'<line x1="{sx}" x2="{sx + px10:.1f}" y1="{sy}" y2="{sy}" stroke="{INK}" stroke-width="3"/>'
               f'<text x="{sx}" y="{sy - 8}" font-size="11" fill="{INK}">0</text>'
               f'<text x="{sx + px10:.1f}" y="{sy - 8}" font-size="11" fill="{INK}" text-anchor="middle">10 км</text>')
    # стрелка севера
    out.append(f'<g transform="translate({W - 30},34)"><path d="M0,-18 L7,6 L0,1 L-7,6 Z" fill="{INK}"/>'
               f'<text y="20" text-anchor="middle" font-size="12" font-weight="700" fill="{INK}">С</text></g>')
    out.append("</svg>")
    return "".join(out)


def country_map(geo_dir, dots, cfg, highlight=(), title="Карта страны", W=300):
    """Мини-карта страны: контур, подсвеченные регионы/департаменты, главные реки, столица и точки.

    Работает для любой страны: всё «французское» вынесено в настройки cfg (блок map в page.yaml страны):
      bbox:        [долгота от, долгота до, широта от, широта до] — рамка карты;
      capital:     [название, долгота, широта] — точка столицы для ориентира;
      rivers:      какие реки рисовать (имена из rivers.geojson);
      river_label: [подпись, долгота, широта].
    Файлы в папке geo/ страны: country.geojson (контур), regions.geojson (регионы, поле code), rivers.geojson.
    dots — точки: [(подпись, долгота, широта, ссылка или None)].
    """
    x0, x1, y0, y1 = cfg["bbox"]
    P, H, k = _proj(x0, x1, y0, y1, W)
    fr = json.load(open(geo_dir + "/country.geojson"))
    deps = json.load(open(geo_dir + "/regions.geojson"))["features"]
    riv = json.load(open(geo_dir + "/rivers.geojson"))["features"]
    out = [_svg_open(W, round(H), title)]
    geoms = fr["features"] if "features" in fr else [fr]
    # реки из Natural Earth тянутся и за границу; обрезаем их по контуру страны (clipPath)
    shape = " ".join(_poly_path(P, _rings(f.get("geometry", f))) for f in geoms)
    cid = "cm" + str(zlib.crc32(f"{title}{W}".encode()))     # уникальное имя: на странице бывает 2 карты
    out.append(f'<defs><clipPath id="{cid}"><path d="{shape}"/></clipPath></defs>')
    out.append(f'<path d="{shape}" fill="{LAND}" stroke="#b9ad9f" stroke-width="1"/>')
    for f in deps:
        if f["properties"]["code"] in highlight:
            out.append(f'<path d="{_poly_path(P, _rings(f["geometry"]))}" fill="#e8c2cb" stroke="{RED}" stroke-width="1"/>')
    for f in riv:
        if f["properties"]["name"] not in cfg.get("rivers", []):
            continue
        for ln in _lines(f["geometry"]):
            out.append('<path d="M' + " L".join("%.1f,%.1f" % P(*p) for p in ln) + f'" fill="none" stroke="{BLUE}" stroke-width="1.6" clip-path="url(#{cid})"/>')
    if cfg.get("capital"):
        name, lon, lat = cfg["capital"][:3]
        # необязательный сдвиг подписи [dx, dy] — если она налезает на точку страницы (как Тбилиси у Кахетии)
        dx, dy = cfg.get("capital_offset", [6, -4])
        px, py = P(lon, lat)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{INK}"/><text x="{px + dx:.1f}" y="{py + dy:.1f}" font-size="11" fill="{INK2}" '
                   f'stroke="{PAPER}" stroke-width="3" paint-order="stroke">{escape(name)}</text>')
    if cfg.get("river_label"):
        t, lon, lat = cfg["river_label"]
        lx, ly = P(lon, lat)
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" font-style="italic" fill="{BLUE}">{escape(t)}</text>')
    fs = 13 if W <= 320 else 15
    for label, lon, lat, href in dots:
        x, y = P(lon, lat)
        anchor, tx = ("end", x - 10) if x > W * 0.35 else ("start", x + 10)
        dot = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{RED}" stroke="#fff" stroke-width="2"><title>{escape(label)}</title></circle>'
               f'<text x="{tx:.1f}" y="{y - 10:.1f}" text-anchor="{anchor}" font-size="{fs}" font-weight="700" fill="{INK}" '
               f'stroke="{PAPER}" stroke-width="3" paint-order="stroke">{escape(label)}</text>')
        out.append(f'<a href="{escape(href)}">{dot}</a>' if href else dot)
    out.append("</svg>")
    return "".join(out)


def points_map(geo_dir, bbox, points, river_labels=(), title="Карта", region_file="region.geojson",
               rivers_file="rivers-zone.geojson", main_river=None, W=760):
    """Карта зоны, когда точных границ участков нет: контур региона, реки и сёла точками.
    points: [(подпись, долгота, широта, тип, сдвиг x, сдвиг y)], тип: aoc (село зоны — бордовая точка),
    town (город), sight (достопримечательность — ромб)."""
    x0, x1, y0, y1 = bbox
    P, H, k = _proj(x0, x1, y0, y1, W)
    out = [_svg_open(W, round(H), title),
           f'<defs><clipPath id="pclip"><rect width="{W}" height="{H:.0f}"/></clipPath></defs>',
           f'<rect width="{W}" height="{H:.0f}" fill="#f6f2ec"/><g clip-path="url(#pclip)">']
    for f in json.load(open(geo_dir + "/" + region_file))["features"]:
        out.append(f'<path d="{_poly_path(P, _rings(f["geometry"]))}" fill="{LAND}" stroke="#b9ad9f" stroke-width="1.2"/>')
    for f in json.load(open(geo_dir + "/" + rivers_file))["features"]:
        w = 5 if f["properties"]["name"] == main_river else 3
        for ln in _lines(f["geometry"]):
            out.append('<path d="M' + " L".join("%.1f,%.1f" % P(*p) for p in ln) +
                       f'" fill="none" stroke="{BLUE}" stroke-width="{w}" stroke-linecap="round" opacity=".8"/>')
    for name, lon, lat, rot in river_labels:
        x, y = P(lon, lat)
        out.append(f'<text x="{x:.0f}" y="{y:.0f}" transform="rotate({rot} {x:.0f} {y:.0f})" font-size="15" font-style="italic" fill="{BLUE}" '
                   f'stroke="#f6f2ec" stroke-width="3" paint-order="stroke">{escape(name)}</text>')
    for name, lon, lat, kind, dx, dy in points:
        x, y = P(lon, lat)
        if kind == "aoc":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{RED}" stroke="#fff" stroke-width="2"><title>{escape(name)}</title></circle>')
            fs, fw, col = 12.5, 600, INK
        elif kind == "town":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{INK}" stroke="#fff" stroke-width="1.5"/>')
            fs, fw, col = 13.5, 700, INK
        else:
            out.append(f'<rect x="{x - 4.5:.1f}" y="{y - 4.5:.1f}" width="9" height="9" transform="rotate(45 {x:.1f} {y:.1f})" fill="{SUN}" stroke="#fff" stroke-width="1.2"/>')
            fs, fw, col = 12, 500, INK2
        out.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" font-size="{fs}" font-weight="{fw}" fill="{col}" '
                   f'stroke="#f6f2ec" stroke-width="3" paint-order="stroke">{escape(name)}</text>')
    out.append("</g>")
    px5 = k * 5 / 111.2
    sx, sy = 20, H - 24
    out.append(f'<rect x="{sx - 8}" y="{sy - 22}" width="{px5 + 60:.0f}" height="36" rx="4" fill="#fff" opacity=".85"/>'
               f'<line x1="{sx}" x2="{sx + px5:.1f}" y1="{sy}" y2="{sy}" stroke="{INK}" stroke-width="3"/>'
               f'<text x="{sx}" y="{sy - 8}" font-size="11" fill="{INK}">0</text>'
               f'<text x="{sx + px5:.1f}" y="{sy - 8}" font-size="11" fill="{INK}" text-anchor="middle">5 км</text>')
    out.append(f'<g transform="translate({W - 30},34)"><path d="M0,-18 L7,6 L0,1 L-7,6 Z" fill="{INK}"/>'
               f'<text y="20" text-anchor="middle" font-size="12" font-weight="700" fill="{INK}">С</text></g>')
    out.append("</svg>")
    return "".join(out)


def _main_polys(geom, reach=12):
    """Оставить «материковые» части страны: самый большой многоугольник и всё, что от него
    не дальше reach градусов (Корсика остаётся, Французская Гвиана и Канары — нет)."""
    polys = _rings(geom)
    if not polys:
        return []
    def size(p):
        xs = [pt[0] for pt in p[0]]; ys = [pt[1] for pt in p[0]]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    big = max(polys, key=size)
    bx, by = big[0][0]
    return [p for p in polys if abs(p[0][0][0] - bx) <= reach and abs(p[0][0][1] - by) <= reach]


def country_tile(geom, dots=(), title="Страна", W=240, H=160, ready=True):
    """Силуэт страны для плитки на главной: контур, вписанный в рамку W×H, и маленькие точки
    готовых страниц (без подписей — подписи на плитке, под картинкой).
    geom — геометрия страны (GeoJSON), dots — [(долгота, широта)]."""
    polys = _main_polys(geom)
    xs = [pt[0] for p in polys for r in p for pt in r]
    ys = [pt[1] for p in polys for r in p for pt in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    c = math.cos(math.radians((y0 + y1) / 2))
    pad = 10
    k = min((W - 2 * pad) / ((x1 - x0) * c), (H - 2 * pad) / (y1 - y0))   # масштаб, чтобы влезло целиком
    ox = (W - (x1 - x0) * c * k) / 2
    oy = (H - (y1 - y0) * k) / 2
    P = lambda lon, lat: (ox + (lon - x0) * c * k, oy + (y1 - lat) * k)
    fill, stroke = (LAND, "#b9ad9f") if ready else ("#f3efe9", "#d6cdc1")
    out = [_svg_open(W, H, title),
           f'<path d="{_poly_path(P, polys)}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>']
    for lon, lat in dots:
        x, y = P(lon, lat)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{RED}" stroke="#fff" stroke-width="1.5"/>')
    out.append("</svg>")
    return "".join(out)
