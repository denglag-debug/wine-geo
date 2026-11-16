# -*- coding: utf-8 -*-
"""
articles.py — читает статьи из папки articles/.

Статья — это один файл .md. Вверху, между двумя строками «---», — «шапка» в формате YAML
(название, дата, теги, к каким местам относится), ниже — обычный текст в той же разметке,
что и text.md страниц: сноски [1], блоки «> Понятными словами», [[chart:…]] пока не поддерживаются.

    ---
    title: Почему Каберне Фран на Луаре такой разный
    date: 2026-11-20
    summary: Одно-два предложения для списка статей.
    tags: [сорта, терруар]
    places: [france/loire]          # к каким страницам относится (папки из content/)
    sources:
      - "Источник 1. [сайт](https://…)"
    ---
    Текст статьи…

Имя файла становится адресом: articles/cabernet-franc-loire.md → site/articles/cabernet-franc-loire.html
"""
import os
import yaml


class Article:
    def __init__(self, path):
        raw = open(path, encoding="utf-8").read()
        if not raw.startswith("---"):
            raise ValueError(f"{path}: статья должна начинаться со строки --- (шапка)")
        _, head, body = raw.split("---", 2)        # делим на «до шапки», шапку и текст
        self.data = yaml.safe_load(head) or {}
        self.text = body
        self.slug = os.path.splitext(os.path.basename(path))[0]
        self.url = f"articles/{self.slug}.html"

    title = property(lambda self: self.data.get("title", self.slug))
    date = property(lambda self: self.data.get("date"))
    summary = property(lambda self: self.data.get("summary", ""))
    tags = property(lambda self: self.data.get("tags", []))
    places = property(lambda self: self.data.get("places", []))

    def about(self, page):
        """Относится ли статья к странице: статья о «france/loire» показывается на странице
        Долины Луары и на всех страницах ниже (Турень, Бургёй…)."""
        path = "/".join(page.slugs)
        return any(path == pl or path.startswith(pl + "/") for pl in self.places)


def load_articles(folder):
    if not os.path.isdir(folder):
        return []
    arts = [Article(os.path.join(folder, f)) for f in sorted(os.listdir(folder)) if f.endswith(".md")]
    arts.sort(key=lambda a: str(a.date or ""), reverse=True)       # новые сверху
    return arts
