# -*- coding: utf-8 -*-
"""
markup.py — превращает тексты из text.md и page.yaml в готовый HTML.

Что здесь происходит с текстом (по порядку):
  1. Убираем HTML-комментарии <!-- ... --> (там пояснения для человека).
  2. Подставляем числа: {{ fmt(s.area_ha) }} → «1 400». Это делает Jinja2 —
     библиотека шаблонов: она находит {{ ... }} и вычисляет выражение внутри.
  3. Находим свои значки:
       [[chart:имя]], [[timeline]] … — места, куда вставить готовые блоки;
       ::: cards … :::              — карточки в две колонки;
       ~ текст                      — мелкое примечание.
  4. Превращаем Markdown в HTML (библиотека markdown): **жирный**, таблицы, списки.
  5. Блок-цитату (> текст) оформляем как «Понятными словами».
  6. Сноски [1, 6] превращаем в маленькие ссылки на список источников.
"""
import re
import markdown as md_lib
from jinja2 import Environment, StrictUndefined

# ---------------------------------------------------------------------------
# Числа «по-русски» и пересчёты единиц. Эти функции доступны внутри {{ ... }}.
# ---------------------------------------------------------------------------
HL_TO_BOTTLES = 133.33          # 1 гл = 100 л = 133,3 бутылки по 0,75 л
PITCH_M2 = 105 * 68             # футбольное поле FIFA, м²


def fmt(n, d=0):
    """Число по-русски: пробел между тысячами, запятая в дробях (63 089; 42,5)."""
    if n is None:
        return "—"
    return f"{n:,.{d}f}".replace(",", " ").replace(".", ",")


def pct(share, d=0):
    """Доля 0..1 → проценты: pct(0.953) → «95»."""
    return fmt(share * 100, d)


def bottles(hl):
    """Гектолитры → число бутылок по 0,75 л."""
    return hl * HL_TO_BOTTLES


def bottles_mln(hl):
    return bottles(hl) / 1e6


def liters_mln(hl):
    return hl * 100 / 1e6


def pitches(ha):
    """Гектары → сколько это футбольных полей."""
    return ha * 10000 / PITCH_M2


HELPERS = dict(fmt=fmt, pct=pct, bottles=bottles, bottles_mln=bottles_mln,
               liters_mln=liters_mln, pitches=pitches, round=round)

# Jinja2 по умолчанию считает «{#» началом комментария. У нас «{#id}» стоит
# в заголовках разделов, поэтому меняем знаки комментария на редкие «{##  ##}».
# StrictUndefined — если в {{ }} опечатка (s.aera_ha), сборка остановится с ошибкой,
# а не тихо вставит пустоту.
_jinja = Environment(comment_start_string="{##", comment_end_string="##}",
                     undefined=StrictUndefined, autoescape=False)


def fill(text, ctx):
    """Шаг 2: подставить числа в {{ ... }}."""
    if "{{" not in text and "{%" not in text:
        return text
    return _jinja.from_string(text).render(**HELPERS, **ctx)


# ---------------------------------------------------------------------------
# Сноски
# ---------------------------------------------------------------------------
# [1] или [1, 6, 12] — но не [текст](ссылка) из Markdown.
FN_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\](?!\()")


class Notes:
    """Собирает номера использованных сносок — чтобы проверить, что все они есть в списке источников."""
    def __init__(self, n_sources, where):
        self.n = n_sources
        self.where = where
        self.used = set()
        self.problems = []

    def sub(self, html):
        def rep(m):
            nums = [int(x) for x in re.split(r"\s*,\s*", m.group(1))]
            for k in nums:
                self.used.add(k)
                if not 1 <= k <= self.n:
                    self.problems.append(f"{self.where}: сноска [{k}], а источников всего {self.n}")
            return '<sup class="fn">[' + ", ".join(f'<a href="#s{k}">{k}</a>' for k in nums) + "]</sup>"
        return FN_RE.sub(rep, html)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
_MD_EXT = ["tables", "attr_list", "md_in_html", "sane_lists"]


def md(text):
    """Markdown → HTML (целый блок: абзацы, списки, таблицы)."""
    return md_lib.markdown(text, extensions=_MD_EXT)


def md_inline(text):
    """Markdown → HTML для одной строки (без обёртки <p>…</p>)."""
    html = md(text).strip()
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return html


def _label_table(m):
    """Таблице из 3+ столбцов даём класс «stack» и каждой ячейке — подпись её столбца (data-label).
    На телефоне такая таблица показывается карточками: «Значение: …», «Что это значит: …»,
    а не узкими столбцами, которые обрезаются за краем экрана."""
    t = m.group(0)
    heads = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", t, flags=re.S)]
    if len(heads) < 3:
        return t.replace("<table>", '<table class="data">')
    body_start = t.find("<tbody>")

    def row(rm):
        cells = iter(heads)
        return re.sub(r"<td([^>]*)>", lambda c: f'<td{c.group(1)} data-label="{next(cells, "")}">', rm.group(0))
    t = t[:body_start] + re.sub(r"<tr>.*?</tr>", row, t[body_start:], flags=re.S)
    return t.replace("<table>", '<table class="data stack">')


def _tables_and_quotes(html):
    """Шаг 5: таблицам — класс оформления, цитатам — вид «Понятными словами»."""
    html = re.sub(r"<table>.*?</table>", _label_table, html, flags=re.S)
    html = re.sub(r"<blockquote>\s*<p>(.*?)</p>\s*</blockquote>",
                  r'<div class="plain"><span class="plain-tag">Понятными словами</span>\1</div>',
                  html, flags=re.S)
    return html


def render_text(text, ctx, notes, blocks):
    """
    Главная функция: text.md → HTML.
      ctx    — данные для {{ }} (s = stats и т.п.);
      notes  — объект Notes (сноски);
      blocks — словарь «имя значка → функция, которая вернёт HTML блока».
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)                 # шаг 1
    text = fill(text, ctx)                                             # шаг 2

    # шаг 3а: значки [[...]] на отдельной строке → временная метка; HTML блока вставим в конце,
    # чтобы Markdown не испортил SVG-картинки.
    ready = {}

    def put(html):
        key = f"BLOCK{len(ready)}X"
        ready[key] = html
        return f"\n\n{key}\n\n"

    def marker(m):
        name = m.group(1).strip()
        kind, _, arg = name.partition(":")
        fn = blocks.get(kind)
        if fn is None:
            notes.problems.append(f"{notes.where}: неизвестный значок [[{name}]]")
            return ""
        return put(fn(arg) if arg else fn())

    text = re.sub(r"^\[\[([^\]]+)\]\]\s*$", marker, text, flags=re.M)

    # шаг 3б: карточки ::: cards … :::
    def cards(m):
        parts = re.split(r"^#### ", m.group(1).strip(), flags=re.M)
        out = []
        for p in parts:
            if not p.strip():
                continue
            title, _, body = p.partition("\n")
            out.append(f'<div class="card"><h4>{md_inline(title)}</h4>{_tables_and_quotes(md(body))}</div>')
        return put(notes.sub('<div class="cards2">' + "".join(out) + "</div>"))

    text = re.sub(r"^::: cards\s*\n(.*?)^:::\s*$", cards, text, flags=re.S | re.M)

    # шаг 3в: примечания «~ текст»
    text = re.sub(r"^~ (.*)$", lambda m: put(f'<p class="note">{notes.sub(md_inline(m.group(1)))}</p>'),
                  text, flags=re.M)

    html = md(text)                                                    # шаг 4
    html = _tables_and_quotes(html)                                    # шаг 5
    html = notes.sub(html)                                             # шаг 6
    for key, block in ready.items():
        html = html.replace(f"<p>{key}</p>", block).replace(key, block)
    return html


def split_sections(html):
    """Разрезает готовый HTML по заголовкам <h2 id=…> → список (id, заголовок, html раздела)."""
    parts = re.split(r'(<h2 id="[^"]+">.*?</h2>)', html, flags=re.S)
    out = []
    for i in range(1, len(parts), 2):
        m = re.match(r'<h2 id="([^"]+)">(.*?)</h2>', parts[i], flags=re.S)
        out.append((m.group(1), m.group(2), parts[i + 1]))
    return out
