# -*- coding: utf-8 -*-
"""
content.py — читает папку content/ и строит из неё «дерево» страниц.

Правило простое: одна папка = одна страница.
    content/france/                         → страница «Франция»
    content/france/loire/                   → «Долина Луары» (ребёнок Франции)
    content/france/loire/touraine/bourgueil → «Бургёй»
В каждой папке должен лежать page.yaml (данные), может лежать text.md (тексты).
Папка geo/ внутри — это не страница, а файлы для карт.

Из положения папок генератор сам понимает: кто родитель (блок «Выше»),
кто соседи («Рядом»), кто дети («Ниже»), какие хлебные крошки.
"""
import os
import yaml

# Папки внутри страницы, которые сами страницами не являются
NOT_PAGES = {"geo", "__pycache__", "img"}

# Как называть уровни по-русски (для подписей)
TYPE_NAMES = {"country": "Страна", "region": "Регион", "subregion": "Субрегион", "aoc": "Аппелласьон"}


class Page:
    """Одна страница сайта. Хранит данные из page.yaml и связи с соседями по дереву."""

    def __init__(self, folder, slugs, parent):
        self.folder = folder                  # папка на диске
        self.slugs = slugs                    # путь, напр. ("france", "loire", "touraine", "bourgueil")
        self.parent = parent                  # родительская страница (или None у страны)
        self.children = []
        with open(os.path.join(folder, "page.yaml"), encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {}
        text_path = os.path.join(folder, "text.md")
        self.text = open(text_path, encoding="utf-8").read() if os.path.exists(text_path) else ""

    # --- удобные «свойства»: обращаемся как page.name вместо page.data["name"] ---
    @property
    def name(self):
        return self.data.get("name", self.slugs[-1])

    @property
    def latin(self):
        return self.data.get("latin", "")

    @property
    def type(self):
        return self.data.get("type", "region")

    @property
    def url(self):
        """Адрес страницы от корня сайта. index.html пишем явно — так ссылки работают
        и в интернете, и при открытии файлов прямо с диска (двойным щелчком)."""
        return "/".join(self.slugs) + "/index.html"

    @property
    def depth(self):
        return len(self.slugs)

    def ancestors(self):
        """Цепочка от страны до родителя: [Франция, Долина Луары, Турень]."""
        chain, p = [], self.parent
        while p:
            chain.insert(0, p)
            p = p.parent
        return chain

    def siblings(self):
        """Соседи того же уровня (без самой страницы)."""
        if not self.parent:
            return []
        return [c for c in self.parent.children if c is not self]

    def descendants(self):
        """Все страницы ниже по дереву (дети, внуки…)."""
        out = []
        for c in self.children:
            out.append(c)
            out += c.descendants()
        return out

    def country(self):
        return (self.ancestors() + [self])[0]

    def geo_dir(self):
        """Папка geo/ страны: там контур страны и регионов для мини-карт."""
        return os.path.join(self.country().folder, "geo")

    def __repr__(self):
        return f"<Page {'/'.join(self.slugs)}>"


def load_tree(content_dir):
    """Обходит content/ и возвращает (список стран, список всех страниц)."""
    all_pages = []

    def walk(folder, slugs, parent):
        page = Page(folder, slugs, parent)
        all_pages.append(page)
        for name in sorted(os.listdir(folder)):
            sub = os.path.join(folder, name)
            if name in NOT_PAGES or not os.path.isdir(sub):
                continue
            if not os.path.exists(os.path.join(sub, "page.yaml")):
                print(f"  ! папка {sub} без page.yaml — пропускаю")
                continue
            page.children.append(walk(sub, slugs + (name,), page))
        # порядок детей: поле order в page.yaml, иначе по алфавиту названия
        page.children.sort(key=lambda c: (c.data.get("order", 999), c.name))
        return page

    countries = []
    for name in sorted(os.listdir(content_dir)):
        sub = os.path.join(content_dir, name)
        if os.path.isdir(sub) and os.path.exists(os.path.join(sub, "page.yaml")):
            countries.append(walk(sub, (name,), None))
    return countries, all_pages
