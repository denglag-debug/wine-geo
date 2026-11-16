# -*- coding: utf-8 -*-
"""
blocks.py — готовые блоки страницы, которые собираются из page.yaml.

В text.md пишется значок, например [[chart:map]] или [[climate]], а здесь
лежат функции, которые по этому значку возвращают кусок HTML.

  [[short]]        — описание, три факта, паспорт, мини-карта
  [[chart:имя]]    — диаграмма из раздела charts
  [[timeline]]     — лента истории + список событий
  [[climate]]      — 4 «плитки» и 4 графика климата
  [[tourism]]      — что посмотреть, как добраться, праздники, когда ехать
  [[glossary]]     — словарик
"""
import importlib.util
import os
from html import escape

import charts as C
from markup import fmt, fill, md_inline

# Имена цветов, которые можно писать в page.yaml вместо кодов
COLORS = {"red": C.RED, "red2": C.RED2, "rose": C.ROSE, "muted": C.MUTED,
          "light": "#c9bdb0", "mid": "#a99c8e", "blue": C.BLUE, "sun": C.SUN,
          "white": "#e9d98b"}


def color(name):
    return COLORS.get(name, name)


class PageBlocks:
    """Набор блоков для одной страницы. Создаётся генератором для каждой страницы."""

    def __init__(self, page, ctx, notes):
        self.page = page
        self.d = page.data
        self.ctx = ctx          # данные для {{ }}
        self.notes = notes      # сноски

    # Строка из YAML → HTML: подставить числа, Markdown, сноски
    def t(self, text):
        return self.notes.sub(md_inline(fill(str(text), self.ctx)))

    def src(self, nums):
        if not nums:
            return ""
        return " " + self.notes.sub("[" + ", ".join(str(n) for n in nums) + "]")

    def figure(self, svg, caption="", src=(), cls=""):
        cap = f"<figcaption>{self.t(caption)}{self.src(src)}</figcaption>" if caption else ""
        return f'<figure class="{cls}">{svg}{cap}</figure>'

    def as_dict(self):
        """Словарь «значок → функция» для markup.render_text."""
        return {"short": self.short, "chart": self.chart, "timeline": self.timeline,
                "climate": self.climate, "tourism": self.tourism, "glossary": self.glossary}

    # ------------------------------------------------------------------
    def minimap(self):
        pos = self.d.get("position")
        if not pos:
            return ""
        cfg = self.page.country().data.get("map")      # настройки карты из page.yaml страны
        if not cfg or not os.path.exists(os.path.join(self.page.geo_dir(), "country.geojson")):
            return ""
        svg = C.country_map(self.page.geo_dir(), [(self.page.name, pos[0], pos[1], None)], cfg,
                            highlight=self.d.get("highlight_deps", []),
                            title=f"{self.page.name} на карте")
        return self.figure(svg, self.d.get("minimap_caption", ""), cls="minimap")

    def short(self):
        """Верх страницы: «Коротко»."""
        d = self.d
        out = [f'<p class="lead">{self.t(d.get("summary", ""))}</p>']
        for f in d.get("facts", []):
            if not isinstance(f, str):
                self.notes.problems.append(f"{self.notes.where}: факт «{f}» прочитан не как текст — "
                                           "скорее всего, в нём есть «: ». Возьмите строку в кавычки.")
        if d.get("facts"):
            out.append('<div class="facts3">' + "".join(
                f"<div><b>{i}.</b> {self.t(f)}</div>" for i, f in enumerate(d["facts"], 1)) + "</div>")
        if d.get("passport"):
            rows = "".join(f"<tr><th>{escape(str(k))}</th><td>{self.t(v)}</td></tr>" for k, v in d["passport"])
            # заголовок можно задать в page.yaml (passport_title) — у грузинских PDO это «Паспорт наименования»
            title = d.get("passport_title") or ("Паспорт аппелласьона" if self.page.type == "aoc" else "Паспорт")
            out.append(f'<div class="passport-wrap"><div><p class="cap">{title}</p>'
                       f'<table class="passport">{rows}</table></div>{self.minimap()}</div>')
        return "\n".join(out)

    # ------------------------------------------------------------------
    def chart(self, name):
        """Диаграмма по описанию из page.yaml → charts → name."""
        spec = self.d.get("charts", {}).get(name)
        if spec is None:
            self.notes.problems.append(f"{self.notes.where}: нет диаграммы charts.{name}")
            return ""
        kind = spec["type"]
        num = lambda v: float(fill(str(v), self.ctx))   # число может быть выражением {{ }}
        if kind == "size_squares":
            svg = C.size_squares([tuple(i) for i in spec["items"]])
        elif kind == "sunburst":
            svg = C.sunburst(inner=[(n, num(v), color(c)) for n, v, c in spec["inner"]],
                             outer=[(n, num(v), color(c), h) for n, v, c, h in spec["outer"]],
                             title=spec.get("title", ""))
        elif kind == "stacked_years":
            svg = C.stacked_years([tuple(r) for r in spec["rows"]], spec.get("title", ""))
        elif kind == "simple_bars":
            svg = C.simple_bars([tuple(r) for r in spec["rows"]], spec.get("title", ""),
                                spec.get("unit", ""), step=spec.get("step", 100000),
                                decimals=spec.get("decimals", 0))
        elif kind == "hbars":
            svg = C.hbars([(l, v, color(c), n) for l, v, c, n in spec["rows"]], spec.get("title", ""),
                          spec.get("unit", ""), maxv=spec.get("max"), decimals=spec.get("decimals", 0))
        elif kind == "detail_map":
            svg = C.detail_map(os.path.join(self.page.folder, "geo"),
                               aoc_codes=set(spec.get("aoc_codes", [])),
                               partial_codes=set(spec.get("partial_codes", [])),
                               own_aoc_codes=set(spec.get("own_aoc_codes", [])),
                               towns=[tuple(t) for t in spec.get("towns", [])],
                               bbox=tuple(spec["bbox"]),
                               river_labels=[tuple(r) for r in spec.get("river_labels", [])],
                               title=spec.get("title", "Карта"))
        elif kind == "points_map":
            # карта зоны «точками»: когда границ участков нет, показываем сёла зоны на контуре региона
            svg = C.points_map(os.path.join(self.page.folder, "geo"), tuple(spec["bbox"]),
                               [tuple(p) for p in spec["points"]],
                               river_labels=[tuple(r) for r in spec.get("river_labels", [])],
                               main_river=spec.get("main_river"), title=spec.get("title", "Карта"))
        elif kind == "custom":
            svg = self._custom(spec["function"])
        else:
            self.notes.problems.append(f"{self.notes.where}: неизвестный тип диаграммы {kind}")
            return ""
        return self.figure(svg, spec.get("caption", ""), spec.get("src", []))

    def _custom(self, func_name):
        """Вызов функции из custom.py в папке страницы (рисунки «ручной работы»)."""
        path = os.path.join(self.page.folder, "custom.py")
        spec = importlib.util.spec_from_file_location("custom_" + "_".join(self.page.slugs), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, func_name)()

    # ------------------------------------------------------------------
    def timeline(self):
        events = self.d.get("history", [])
        on_chart = [e for e in events if e.get("chart")]
        out = []
        if on_chart:
            n = len(on_chart)
            # точки на ленте ставим через равные промежутки (интервалы не в масштабе)
            svg = C.timeline([(str(e["chart"]), i / (n - 1) if n > 1 else 0.5, e.get("short", ""), e.get("key", False))
                              for i, e in enumerate(on_chart)],
                             title=f"Таймлайн истории: {self.page.name}")
            out.append(self.figure(svg, self.d.get("timeline_caption", ""), self.d.get("timeline_src", [])))
        out.append('<ul class="tl">' + "".join(
            f'<li><b>{escape(str(e["date"]))}.</b> {self.t(e["text"])}</li>' for e in events) + "</ul>")
        return "\n".join(out)

    # ------------------------------------------------------------------
    def climate(self):
        """Климат: 4 плитки с годовыми цифрами + одна картинка с графиками по месяцам.
        Не у всех метеостанций есть все ряды (у Телави, например, нет солнечных часов и заморозков),
        поэтому каждую плитку и каждый график показываем, только если для него есть данные.
        Недостающую плитку можно задать вручную: climate → tiles: [[«2 300+ ч», «солнца за год [3]»]]."""
        c = self.d["climate"]
        where = f'{c["station"]}, {c["period"]}'
        src = c.get("src", [])
        # средняя температура: готовый ряд tmean или середина между ночной и дневной
        tmean = c.get("tmean") or [(a + b) / 2 for a, b in zip(c["tmin"], c["tmax"])]
        tiles = [(f"{fmt(sum(tmean) / 12, 1)} °C", "средняя за год")]
        if c.get("rain"):
            tiles.append((f'{fmt(sum(c["rain"]))} мм', "осадков за год"))
        if c.get("sun"):
            tiles.append((f'{fmt(sum(c["sun"]))} ч', "солнца за год"))
        if c.get("frost"):
            tiles.append((fmt(sum(c["frost"])), "дней с заморозком"))
        tiles += [(self.t(v), self.t(lbl)) for v, lbl in c.get("tiles", [])]
        out = ['<div class="stats4">' + "".join(f"<div><b>{a}</b><span>{b}</span></div>" for a, b in tiles[:4]) + "</div>"]
        # подпись перечисляет только те графики, которые реально нарисованы
        rows = [n for k, n in (("rain", "осадки"), ("sun", "солнечные часы"), ("frost", "дни с заморозком")) if c.get(k)]
        below = f"Ниже — {', '.join(rows)}. " if rows else ""
        mean_note = "чёрная линия — средняя" if c.get("tmean") else "чёрная линия — середина между ними"
        out.append(self.figure(C.climate_panel(c, title=f"Климат по месяцам, {where}"),
                               "Климат по месяцам. Сверху — температура: полоса от средней ночной до средней дневной, "
                               f"{mean_note}. {below}{where}. "
                               "Наведите мышь на месяц — появятся точные цифры.", src))
        return "\n".join(out)

    # ------------------------------------------------------------------
    def tourism(self):
        tr = self.d.get("tourism", {})
        out = []
        if tr.get("sights"):
            out.append(f"<h3>Что посмотреть в {self.d.get('name_prep', self.page.name)} и рядом</h3><ul>")
            out += [f'<li><b>{escape(s["name"])}</b> — {self.t(s["text"])}</li>' for s in tr["sights"]]
            if tr.get("nearby"):
                out.append(f"<li>{self.t(tr['nearby'])}</li>")
            out.append("</ul>")
        items = [f'<li><b>{escape(g["how"])}:</b> {self.t(g["text"])}</li>' for g in tr.get("getting_there", [])]
        for f in tr.get("festivals", []):
            note = f" ({f['note']})" if f.get("note") else ""
            items.append(f'<li><b>Праздник:</b> {escape(f["name"])} — {escape(str(f["date"]))}{escape(note)}.{self.src(f.get("src")).strip()}</li>')
        if tr.get("best_time"):
            items.append(f'<li><b>Лучшее время:</b> {self.t(tr["best_time"]["text"])}</li>')
        if items:
            out.append("<h3>Как добраться и когда ехать</h3><ul>" + "".join(items) + "</ul>")
        return "\n".join(out)

    def glossary(self):
        rows = "".join(f'<dt>{escape(g["term"])}</dt><dd>{self.t(g["def"])}</dd>' for g in self.d.get("glossary", []))
        return f'<dl class="gloss">{rows}</dl>'
