# -*- coding: utf-8 -*-
"""
custom.py — «особые» картинки только для этой страницы.

Большинство диаграмм описываются данными в page.yaml и рисуются общими
функциями из lib/charts.py. Но некоторые картинки рисуются вручную под
конкретное место (например, разрез склона Бургёя). Такие функции кладём
сюда, в папку страницы. Генератор сам найдёт этот файл и вызовет функцию,
если в page.yaml у диаграммы написано  type: custom  и  function: <имя>.
"""
import random
from html import escape
from charts import _svg_open, INK, INK2, MUTED, BLUE, GREEN


def cross_section(fs=1.0):
    """fs — множитель размера подписей (в маленькой карточке подписи крупнее)."""
    W, H = 760, 330
    out = [_svg_open(W, H, "Схематичный разрез: от Луары к лесу на плато")]
    # небо/фон
    # рельеф: слева Луара (юг), справа плато с лесом (север)
    surf = [(0, 250), (90, 250), (120, 244), (300, 236), (420, 228), (470, 205), (540, 150), (600, 112), (660, 98), (760, 96)]
    pts = " ".join(f"{x},{y}" for x, y in surf)
    # слои снизу вверх: туф (мел) — основа всего
    out.append(f'<polygon points="0,330 760,330 760,128 560,140 540,150 470,205 420,262 0,276" fill="#e9dfc4"/>')
    # сенонские глины и пески на верхнем склоне и плато
    out.append(f'<polygon points="540,150 600,112 660,98 760,96 760,128 560,140" fill="#c9a77a"/>')
    # террасы: пески и гравий
    out.append(f'<polygon points="0,276 420,262 470,205 420,228 300,236 120,244 90,250 0,250" fill="#d8c7a6"/>')
    # Луара
    out.append(f'<path d="M0,250 L90,250 L92,262 L0,262 Z" fill="{BLUE}" opacity=".85"/>')
    # линия поверхности
    out.append(f'<polyline points="{pts}" fill="none" stroke="{INK2}" stroke-width="1.5"/>')
    # лозы — маленькие вертикальные чёрточки на террасе и склоне
    random.seed(4)
    for x0, x1 in ((140, 410), (480, 600)):
        for x in range(x0, x1, 9):
            # найдём высоту поверхности в точке x линейной интерполяцией
            for (ax, ay), (bx, by) in zip(surf, surf[1:]):
                if ax <= x <= bx:
                    y = ay + (by - ay) * (x - ax) / (bx - ax)
                    break
            out.append(f'<line x1="{x}" y1="{y:.1f}" x2="{x}" y2="{y - 9:.1f}" stroke="{GREEN}" stroke-width="2"/>')
    # лес на плато
    for x in range(625, 760, 14):
        y = 98 if x < 660 else 96
        out.append(f'<circle cx="{x}" cy="{y - 12}" r="9" fill="#5f7a45"/>')
    # подписи
    lab = [
        (45, 240, "Луара", "middle", BLUE),
        (260, 222, "Терраса: пески и гравий", "middle", INK),
        (260, 300, "лёгкие, фруктовые вина, пьются молодыми", "middle", INK2),
        (505, 150, "Склон (кото)", "end", INK),
        (580, 240, "Туф (туффо) — мягкий известняк", "middle", INK),
        (580, 240 + 17 * fs, "плотные вина для выдержки", "middle", INK2),
        (690, 70, "Лес на плато", "middle", "#4a6236"),
        (755, 122, "глины, кремни, пески", "end", INK2),
    ]
    for x, y, t, a, c in lab:
        out.append(f'<text x="{x}" y="{y}" text-anchor="{a}" font-size="{13 * fs:.1f}" fill="{c}" font-weight="{600 if c == INK else 400}">{escape(t)}</text>')
    out.append(f'<text x="8" y="20" font-size="11" fill="{MUTED}">ЮГ</text><text x="752" y="20" text-anchor="end" font-size="11" fill="{MUTED}">СЕВЕР</text>')
    out.append(f'<text x="380" y="20" text-anchor="middle" font-size="11" fill="{MUTED}">схема, без масштаба</text>')
    out.append("</svg>")
    return "".join(out)


