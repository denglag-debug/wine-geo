# -*- coding: utf-8 -*-
"""
custom.py — «особая» картинка страницы «Грузия»: карта винных регионов.

Генератор вызывает функцию regions_map(), потому что в page.yaml у диаграммы
charts.regions написано  type: custom  и  function: regions_map.

Как устроена карта:
  1. Берём контуры краёв Грузии из geo/regions.geojson (у каждого есть код, напр. GE-KA).
  2. Для каждого винного региона знаем, из каких краёв он состоит и сколько в нём
     наименований места происхождения (PDO) — таблица WINE_REGIONS ниже.
  3. Закрашиваем: чем больше PDO, тем темнее цвет. Подписываем название и число.
Чтобы добавить или поправить регион, достаточно изменить строку в WINE_REGIONS.
"""
import json
import os
from html import escape

from charts import _svg_open, _proj, _rings, _poly_path, INK, INK2, PAPER, BLUE

HERE = os.path.dirname(os.path.abspath(__file__))

# (название, коды краёв, число PDO, [долгота, широта] подписи)
WINE_REGIONS = [
    ("Кахетия", ["GE-KA"], 20, [45.75, 41.62]),
    ("Картли", ["GE-SK", "GE-KK", "GE-TB", "GE-MM"], 4, [44.25, 41.98]),
    ("Имерети", ["GE-IM"], 3, [42.95, 42.17]),
    ("Рача-Лечхуми", ["GE-RL"], 5, [43.10, 42.72]),
    ("Самегрело", ["GE-SZ"], 1, [42.05, 42.52]),
    ("Гурия", ["GE-GU"], 0, [42.10, 41.97]),
    ("Аджария", ["GE-AJ"], 0, [42.15, 41.60]),
    ("Месхети", ["GE-SJ"], 0, [43.30, 41.48]),
]


def _fill(n):
    """Цвет заливки по числу PDO: 0 — светлый беж, дальше всё темнее."""
    if n == 0:
        return "#efe9df"
    if n <= 1:
        return "#f1d9de"
    if n <= 5:
        return "#e2aab7"
    return "#b9516c"


def regions_map():
    W = 760
    # рамка карты (долгота от/до, широта от/до) — та же, что в блоке map: страницы «Грузия».
    # Контур страны дан без Абхазии и Южной Осетии — решение Дениса от 17.11.2026.
    x0, x1, y0, y1 = 41.4, 46.8, 41.0, 43.3
    P, H, _ = _proj(x0, x1, y0, y1, W)                 # P(долгота, широта) → точка на картинке
    feats = json.load(open(os.path.join(HERE, "geo", "regions.geojson"), encoding="utf-8"))["features"]
    by_code = {f["properties"]["code"]: f for f in feats}
    out = [_svg_open(W, round(H), "Карта винных регионов Грузии")]

    # 1) заливка регионов
    for name, codes, n, _pos in WINE_REGIONS:
        for c in codes:
            out.append(f'<path d="{_poly_path(P, _rings(by_code[c]["geometry"]))}" fill="{_fill(n)}" '
                       f'stroke="#fff" stroke-width="1.2"><title>{escape(name)}: PDO — {n}</title></path>')

    # 2) реки (Кура и Алазани) — для ориентира
    riv = json.load(open(os.path.join(HERE, "geo", "rivers.geojson"), encoding="utf-8"))["features"]
    from charts import _lines
    shape = " ".join(_poly_path(P, _rings(f["geometry"])) for f in feats)
    out.append(f'<defs><clipPath id="georeg"><path d="{shape}"/></clipPath></defs>')
    for f in riv:
        if f["properties"]["name"] in ("Kura", "Alazani"):
            for ln in _lines(f["geometry"]):
                out.append('<path d="M' + " L".join("%.1f,%.1f" % P(*p) for p in ln)
                           + f'" fill="none" stroke="{BLUE}" stroke-width="1.4" opacity=".8" clip-path="url(#georeg)"/>')

    # 3) столица
    px, py = P(44.834, 41.691)
    out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{INK}"/>'
               f'<text x="{px + 7:.1f}" y="{py + 15:.1f}" font-size="12" fill="{INK2}" stroke="{PAPER}" '
               f'stroke-width="3" paint-order="stroke">Тбилиси</text>')

    # 4) подписи регионов: название и число PDO
    for name, _codes, n, (lon, lat) in WINE_REGIONS:
        x, y = P(lon, lat)
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="{INK}" '
                   f'stroke="{PAPER}" stroke-width="3" paint-order="stroke">{escape(name)}</text>')
        sub = f"PDO: {n}" if n else "PDO пока нет"
        out.append(f'<text x="{x:.1f}" y="{y + 15:.1f}" text-anchor="middle" font-size="11.5" fill="{INK2}" '
                   f'stroke="{PAPER}" stroke-width="3" paint-order="stroke">{sub}</text>')
    out.append("</svg>")
    return "".join(out)
