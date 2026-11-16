# -*- coding: utf-8 -*-
"""
build.py — ГЕНЕРАТОР всего сайта винной энциклопедии.

Запуск (из папки portal):   python3 build.py
Результат:                  папка site/ — готовый сайт. Откройте site/index.html
                            двойным щелчком: всё работает и без интернета.

Что делает программа, по шагам:
  1. Читает папку content/ — одна папка = одна страница (lib/content.py).
  2. Для каждой страницы склеивает данные (page.yaml), тексты (text.md)
     и оформление (шаблоны templates/*.html) → site/<путь>/index.html.
  3. Собирает сквозные разделы из данных всех страниц:
     История, Туризм, Статистика, Сорта, Словарь, Регионы.
  4. Строит индекс для поиска (static/search-index.js).
  5. Проверяет страницы AOC: все ли разделы шаблона на месте, нет ли
     сносок на несуществующие источники — и печатает список замечаний.

Нужные библиотеки (один раз):  pip install pyyaml markdown jinja2
"""
import os
import re
import shutil
import sys
import json
sys.dont_write_bytecode = True   # не создавать служебные папки __pycache__ рядом с данными
from collections import defaultdict
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))       # чтобы Python нашёл наши модули в lib/

from jinja2 import Environment, FileSystemLoader     # noqa: E402
import charts as C                                   # noqa: E402
from content import load_tree, TYPE_NAMES            # noqa: E402
from markup import Notes, render_text, split_sections, md_inline, fill, fmt, pct, bottles_mln  # noqa: E402
from blocks import PageBlocks                        # noqa: E402
from articles import load_articles                   # noqa: E402

CONTENT = os.path.join(HERE, "content")
ARTICLES = os.path.join(HERE, "articles")
OUT = os.path.join(HERE, "site")
SITE_NAME = "Винная энциклопедия"

# Разделы страницы AOC по шаблону v1.0 (template/region-template.md).
# Генератор проверяет, что все они есть в text.md, и сам ставит их в этом порядке в оглавление.
AOC_SECTIONS = [
    ("short", "Коротко"), ("grapes", "Сорта"), ("rules", "Правила"), ("style", "Вина и стиль"),
    ("history", "История"), ("geo", "География и терруар"), ("craft", "Традиции"),
    ("vintages", "Года урожая"), ("legend", "Легендарные вина"), ("people", "Люди и хозяйства"),
    ("compare", "Сравнение"), ("food", "Гастрономия"), ("travel", "Туризм"), ("glossary", "Словарик"),
]

# Верхнее меню сайта: (адрес от корня, подпись)
# «Туризм» как сквозной раздел пока убран по решению Дениса (2026-11-13); раздел «Туризм»
# на страницах AOC остаётся (он часть шаблона v1.0). Вернуть — добавить строку обратно.
MENU = [("regions.html", "Регионы"), ("history.html", "История"), ("stats.html", "Статистика"),
        ("grapes.html", "Сорта"), ("glossary.html", "Словарь"), ("articles.html", "Статьи")]

MONTHS_FULL = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
               "сентябрь", "октябрь", "ноябрь", "декабрь"]
COLOR_NAMES = {"red": "красное", "rose": "розовое", "white": "белое", "sparkling": "игристое", "sweet": "сладкое"}

problems = []          # сюда складываем замечания проверки


# =============================================================================
# Вспомогательное
# =============================================================================
def rel_root(depth):
    """Относительный путь до корня сайта: со страницы глубины 3 — «../../../».
    Относительные ссылки работают везде: в интернете, на диске, в любой папке."""
    return "../" * depth


def write(path, html):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(html)


MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
              "сентября", "октября", "ноября", "декабря"]


def ru_date(d):
    """Дата из page.yaml (2026-11-09) → «9 ноября 2026»."""
    if hasattr(d, "month"):
        return f"{d.day} {MONTHS_GEN[d.month - 1]} {d.year}"
    return str(d or "—")


def plural(n, one, few, many):
    """Русские окончания: plural(1, "аппелласьон", "аппелласьона", "аппелласьонов") → «1 аппелласьон»,
    2 → «2 аппелласьона», 5 → «5 аппелласьонов», 21 → «21 аппелласьон»."""
    if n % 10 == 1 and n % 100 != 11:
        w = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        w = few
    else:
        w = many
    return f"{n} {w}"


def first_sentence(text):
    """Первое предложение описания — для карточек в списках. Сноски [1] убираем."""
    text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", str(text or "")).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", text, flags=re.S)
    return (m.group(1) if m else text).replace("**", "")


# =============================================================================
# Шаблоны
# =============================================================================
env = Environment(loader=FileSystemLoader(os.path.join(HERE, "templates")), autoescape=False,
                  trim_blocks=True, lstrip_blocks=True)
env.globals.update(fmt=fmt, pct=pct, SITE_NAME=SITE_NAME, MENU=MENU, TYPE_NAMES=TYPE_NAMES,
                   TODAY=date.today().strftime("%d.%m.%Y"))


def render(template, out_path, depth, **ctx):
    html = env.get_template(template).render(root=rel_root(depth), **ctx)
    write(out_path, html)


# =============================================================================
# Шаг 2. Страницы дерева: страны, регионы, AOC
# =============================================================================
def group_dots(page, prefix):
    """Точки для карты хаба. Чтобы на карте Франции не было сотен точек, рисуем ОДНУ точку
    на каждого ребёнка страницы: на странице Франции — по точке на регион (в центре его готовых AOC,
    с подписью «Долина Луары · 12»), на странице региона — по точке на субрегион, и т.д.
    Точка ведёт на страницу этого ребёнка."""
    dots = []
    for child in page.children:
        aocs = [p for p in [child] + child.descendants() if p.type == "aoc" and p.data.get("position")]
        if not aocs:
            continue
        lon = sum(p.data["position"][0] for p in aocs) / len(aocs)
        lat = sum(p.data["position"][1] for p in aocs) / len(aocs)
        label = child.name if child.type == "aoc" else f"{child.name} · {len(aocs)}"
        dots.append((label, lon, lat, prefix + child.url))
    return dots


def build_page(page, all_pages, articles):
    d = page.data
    notes = Notes(len(d.get("sources", [])), "/".join(page.slugs))
    ctx = {"s": d.get("stats", {}), "d": d}
    blocks = PageBlocks(page, ctx, notes)

    body = render_text(page.text, ctx, notes, blocks.as_dict()) if page.text else ""
    sections = split_sections(body)

    # «Выше / Рядом / Ниже» — из дерева папок
    related = {
        "up": page.parent,
        "side": page.siblings(),
        "see_also": d.get("see_also", []),
        # «Рядом» одной строкой: готовые соседи (ссылки), запланированные (серым), «см. также»
        "side_items": [(c.name, c.url, "") for c in page.siblings()]
                      + [(x["name"], None, "страница пока не готова")
                         for x in (page.parent.data.get("planned", []) if page.parent else [])]
                      + [(x["name"], None, x.get("note", "")) for x in d.get("see_also", [])],
        "down": page.children,
        "down_note": d.get("below_note", ""),
    }

    # Источники: тоже через Markdown (ссылки [текст](адрес))
    sources = [md_inline(fill(str(s), ctx)) for s in d.get("sources", [])]

    if page.type == "aoc":
        # проверка: все ли разделы шаблона на месте
        have = [sid for sid, _, _ in sections]
        for sid, title in AOC_SECTIONS:
            if sid not in have:
                problems.append(f"{'/'.join(page.slugs)}: нет раздела «{title}» ({{#{sid}}}) — "
                                "если данных нет, напишите «нет надёжных данных»")
        toc = [(sid, t) for sid, t in AOC_SECTIONS if sid in have]
        render("aoc.html", page.url, page.depth, page=page, d=d, sections=sections, toc=toc,
               related=related, sources=sources, blocks=blocks,
               articles=[a for a in articles if a.about(page)])
    else:
        # Хаб (страна / регион / субрегион): список детей, карта — по одной точке на каждого ребёнка
        dots = group_dots(page, rel_root(page.depth))
        hub_map = ""
        # Карта есть, если у страны лежит контур (geo/country.geojson) и в её page.yaml есть блок map:
        cfg = page.country().data.get("map")
        if dots and cfg and os.path.exists(os.path.join(page.geo_dir(), "country.geojson")):
            hub_map = C.country_map(page.geo_dir(), dots, cfg, highlight=d.get("highlight_deps", []),
                                    title=f"{page.name}: страницы на карте", W=380)
        aocs = [p for p in page.descendants() if p.type == "aoc"]
        summary = blocks.t(d.get("summary", ""))
        # Одна строка для читателя: сколько готово и сколько ещё будет (с правильными окончаниями)
        planned_all = sum(len(p.data.get("planned", [])) for p in [page] + page.descendants())
        count_line = ("В энциклопедии пока " + plural(len(aocs), "готовый аппелласьон", "готовых аппелласьона",
                                                        "готовых аппелласьонов")
                      + (f"; ещё {plural(planned_all, 'страница', 'страницы', 'страниц')} в планах." if planned_all else "."))
        render("hub.html", page.url, page.depth, page=page, d=d, sections=sections, body=body,
               related=related, sources=sources, hub_map=hub_map, summary=summary, aocs=aocs, count_line=count_line,
               first_sentence=first_sentence, planned=d.get("planned", []),
               path="/".join(page.slugs), articles=[a for a in articles if a.about(page)])

    problems.extend(notes.problems)
    unused = set(range(1, notes.n + 1)) - notes.used
    if unused:
        problems.append(f"{'/'.join(page.slugs)}: источники {sorted(unused)} нигде не упомянуты сноской")

    # Файлы страницы (PDF, картинки) копируем рядом с index.html
    for name in os.listdir(page.folder):
        if os.path.splitext(name)[1].lower() in (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".webp"):
            dst = os.path.join(OUT, *page.slugs, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(page.folder, name), dst)


# =============================================================================
# Шаг 3. Сквозные разделы
# =============================================================================
def chain(page):
    """«Франция → Долина Луары → Турень» — строка для таблиц."""
    return " → ".join(p.name for p in page.ancestors())


def place_list(countries):
    """Все места сайта в порядке дерева — для выпадающего фильтра «Где»:
    [{"path": "france/loire", "name": "Долина Луары", "depth": 2}, …]"""
    out = []

    def walk(p):
        out.append({"path": "/".join(p.slugs), "name": p.name, "depth": p.depth, "type": p.type})
        for c in p.children:
            walk(c)
    for c in countries:
        walk(c)
    return out


def build_cross(countries, pages, articles):
    aocs = [p for p in pages if p.type == "aoc"]

    # --- История: события всех страниц в одной ленте, по векам ---------------
    events = []
    for p in pages:
        for e in p.data.get("history", []):
            events.append({"year": e.get("year", 0), "date": e["date"], "page": p,
                           "text": re.sub(r"\[\d+(?:,\s*\d+)*\]", "", md_inline(str(e["text"]))),
                           "key": e.get("key", False)})
    events.sort(key=lambda e: e["year"])
    by_century = defaultdict(list)
    for e in events:
        by_century[century(e["year"])].append(e)
    render("history.html", "history.html", 0, centuries=list(by_century.items()), n=len(events),
           n_pages=len({id(e["page"]) for e in events}), active="history.html")

    # --- Туризм: сквозной раздел пока отключён (см. MENU). Код сборки — в build_tourism ниже.
    # build_tourism(pages)

    # --- Статистика: таблица всех AOC с сортировкой ----------------------------
    rows = []
    for p in aocs:
        s = p.data.get("stats", {})
        prod = s.get("production", {})
        cols = s.get("colors", {})
        rows.append({"page": p, "chain": chain(p), "area": s.get("area_ha"), "hl": prod.get("avg_hl"),
                     "period": prod.get("avg_period", ""),
                     "bottles": bottles_mln(prod["avg_hl"]) if prod.get("avg_hl") else None,
                     "colors": ", ".join(f"{COLOR_NAMES.get(k, k)} {pct(v)}\u00a0%" for k, v in cols.items()) or s.get("colors_text", ""),
                     "grape": (s.get("grapes") or [{}])[0].get("name", ""),
                     "year": s.get("status_year"), "status": s.get("status", ""), "yield_legal": s.get("yield_legal")})
    render("stats.html", "stats.html", 0, rows=rows, active="stats.html")

    # --- Сорта: где какой сорт растёт ------------------------------------------
    grapes = defaultdict(list)
    info = {}
    for p in aocs:
        for g in p.data.get("stats", {}).get("grapes", []):
            grapes[g["name"]].append((p, g.get("role", "")))
            info[g["name"]] = g
    grape_list = sorted(grapes.items(), key=lambda kv: kv[0])
    render("grapes.html", "grapes.html", 0, grapes=grape_list, info=info, COLOR_NAMES=COLOR_NAMES,
           active="grapes.html")

    # --- Словарь: термины со всех страниц ---------------------------------------
    terms = {}
    for p in pages:
        for g in p.data.get("glossary", []):
            key = g["term"].lower()
            if key not in terms:
                terms[key] = {"term": g["term"], "def": md_inline(str(g["def"])), "pages": []}
            terms[key]["pages"].append(p)
    render("glossary.html", "glossary.html", 0, terms=sorted(terms.values(), key=lambda t: t["term"].lower()),
           active="glossary.html")

    # --- Регионы: всё дерево целиком --------------------------------------------
    render("regions.html", "regions.html", 0, countries=countries, active="regions.html",
           first_sentence=first_sentence, n_aoc=len(aocs))

    # --- Статьи --------------------------------------------------------------------
    build_articles(articles, pages)

    # --- Главная ------------------------------------------------------------------
    # По одной мини-карте на каждую страну, у которой есть контур и блок map: в page.yaml.
    # На карте страны — по точке на регион (а не на каждую AOC), чтобы не было «перебора точек».
    home_maps = []
    for c in countries:
        cfg = c.data.get("map")
        dots = group_dots(c, "")
        if cfg and dots and os.path.exists(os.path.join(c.folder, "geo", "country.geojson")):
            home_maps.append((c, C.country_map(os.path.join(c.folder, "geo"), dots, cfg,
                                               title=f"{c.name}: готовые страницы на карте", W=420)))
    recent = sorted(aocs, key=lambda p: str(p.data.get("updated", "")), reverse=True)[:6]
    render("home.html", "index.html", 0, countries=countries, home_maps=home_maps, recent=recent,
           articles=articles[:3],
           n_aoc=len(aocs), n_pages=len(pages), first_sentence=first_sentence, active="")

    return terms


def build_articles(articles, pages):
    """Список статей (articles.html) и страница каждой статьи (articles/<имя>.html)."""
    by_path = {"/".join(p.slugs): p for p in pages}
    for a in articles:
        notes = Notes(len(a.data.get("sources", [])), "articles/" + a.slug)
        body = render_text(a.text, {"d": a.data}, notes, {})
        sources = [md_inline(str(x)) for x in a.data.get("sources", [])]
        places = [by_path[pl] for pl in a.places if pl in by_path]
        for pl in a.places:
            if pl not in by_path:
                problems.append(f"articles/{a.slug}: место «{pl}» не найдено в content/")
        render("article.html", a.url, 1, a=a, body=body, sources=sources, places=places, active="articles.html")
        problems.extend(notes.problems)
    tags = sorted({t for a in articles for t in a.tags})
    render("articles.html", "articles.html", 0, articles=articles, tags=tags, active="articles.html")


def build_tourism(pages):
    """Календарь праздников и «когда ехать». Сейчас не вызывается (раздел убран из меню)."""
    fests = defaultdict(list)
    best = defaultdict(list)
    sights = []
    for p in pages:
        tr = p.data.get("tourism", {})
        for f in tr.get("festivals", []):
            fests[f["month"]].append({"page": p, **f})
        for m in tr.get("best_time", {}).get("months", []):
            best[m].append(p)
        if tr.get("sights"):
            sights.append((p, tr["sights"]))
    months = [{"n": i, "name": MONTHS_FULL[i - 1], "fests": fests.get(i, []), "best": best.get(i, [])}
              for i in range(1, 13)]
    render("tourism.html", "tourism.html", 0, months=months, sights=sights, active="tourism.html",
           strip=lambda t: re.sub(r"\[\d+(?:,\s*\d+)*\]", "", md_inline(str(t))))


def century(year):
    """Год → «XIX век». До нашей эры — «до н. э.»."""
    if year <= 0:
        return "До нашей эры"
    n = (year - 1) // 100 + 1
    roman = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV",
             "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII"][n]
    return f"{roman} век"


# =============================================================================
# Шаг 4. Поиск
# =============================================================================
def build_search(pages, terms, articles):
    """Индекс поиска — список «что искать → куда вести». Кладём его в .js-файл, а не .json:
    так поиск работает даже при открытии сайта с диска (браузер не даёт читать .json с диска)."""
    idx = []
    for p in pages:
        s = p.data.get("stats", {})
        words = [p.name, p.latin, p.data.get("kicker", ""), chain(p)]
        words += [g["name"] for g in s.get("grapes", [])] + [g.get("latin", "") for g in s.get("grapes", [])]
        idx.append({"t": p.name, "l": p.latin, "u": p.url, "k": TYPE_NAMES.get(p.type, ""),
                    "c": chain(p), "w": " ".join(words)})
    for t in terms.values():
        idx.append({"t": t["term"], "l": "", "u": "glossary.html#" + slug(t["term"]), "k": "Термин",
                    "c": re.sub("<[^>]+>", "", t["def"])[:90], "w": t["term"]})
    for p in pages:
        for g in p.data.get("stats", {}).get("grapes", []):
            idx.append({"t": g["name"], "l": g.get("latin", ""), "u": "grapes.html#" + slug(g["name"]),
                        "k": "Сорт", "c": "", "w": g["name"] + " " + g.get("latin", "")})
    for a in articles:
        idx.append({"t": a.title, "l": "", "u": a.url, "k": "Статья", "c": a.summary[:90],
                    "w": a.title + " " + " ".join(a.tags) + " " + a.summary})
    # убираем дубли (один сорт встречается на многих страницах)
    seen, uniq = set(), []
    for i in idx:
        if i["u"] not in seen:
            seen.add(i["u"])
            uniq.append(i)
    write("static/search-index.js", "window.SEARCH_INDEX = " + json.dumps(uniq, ensure_ascii=False) + ";\n")


def slug(text):
    """«Каберне Фран» → «каберне-фран» — для якорей #… в адресах."""
    return re.sub(r"[^\w]+", "-", text.lower()).strip("-")


env.globals["slug"] = slug
env.globals["ru_date"] = ru_date


# =============================================================================
# Запуск
# =============================================================================
def main():
    print("Читаю content/ …")
    countries, pages = load_tree(CONTENT)
    print(f"  страниц: {len(pages)} (AOC: {sum(p.type == 'aoc' for p in pages)})")

    if os.path.exists(OUT):
        shutil.rmtree(OUT)                       # собираем каждый раз с нуля — так не остаётся «мусора»
    shutil.copytree(os.path.join(HERE, "static"), os.path.join(OUT, "static"))

    articles = load_articles(ARTICLES)
    # Список мест для фильтров «Где». Кладём в «глобальные» данные шаблонов ДО сборки страниц:
    # Jinja2 запоминает глобальные данные в момент первой загрузки шаблона.
    env.globals["PLACES"] = place_list(countries)
    for p in pages:
        build_page(p, pages, articles)
        print("  ✓", p.url)
    # Список заданий для tools/make_pdf.js: какие страницы превратить в PDF и как назвать файл
    jobs = [{"html": p.url, "pdf": "/".join(p.slugs) + "/" + f["file"], "title": f"{p.name} ({p.latin})"}
            for p in pages for f in p.data.get("downloads", []) if f.get("auto")]
    write("static/pdf-jobs.json", json.dumps(jobs, ensure_ascii=False, indent=1))
    terms = build_cross(countries, pages, articles)
    build_search(pages, terms, articles)
    print("  ✓ сквозные разделы и поиск")

    make_pdfs(pages)

    print("\nПроверка:" if problems else "\nПроверка: замечаний нет.")
    for msg in problems:
        print("  !", msg)
    print(f"\nГотово: {os.path.join(OUT, 'index.html')}")


def make_pdfs(pages):
    """PDF теперь делается автоматически в конце сборки (раньше — отдельной командой, и её легко
    было забыть: сборка стирает папку site/, и кнопка «Полный PDF» вела в никуда).
    Нужны Node.js и Playwright. Если их нет — сайт всё равно собирается, а здесь будет замечание."""
    import subprocess
    if shutil.which("node"):
        r = subprocess.run(["node", os.path.join(HERE, "tools", "make_pdf.js")], capture_output=True, text=True)
        print(r.stdout.strip() or "  (PDF не заказаны)")
        if r.returncode != 0:
            problems.append("PDF не сделаны: " + (r.stderr.strip().splitlines() or ["ошибка node"])[-1])
    else:
        problems.append("PDF не сделаны: не найден Node.js (нужен для tools/make_pdf.js)")
    # проверка: каждая кнопка скачивания ведёт на существующий файл
    for p in pages:
        for f in p.data.get("downloads", []):
            if not os.path.exists(os.path.join(OUT, *p.slugs, f["file"])):
                problems.append(f"{'/'.join(p.slugs)}: кнопка «{f['title']}» ведёт на файл {f['file']}, которого нет")


if __name__ == "__main__":
    main()
