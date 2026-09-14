#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карта сайта: lastmod считается по git, а не правится руками.

Дата, которую правит человек, отстаёт молча: у соседнего сайта humanizer-ru
она отстала на два месяца и поисковик всё это время читал «ничего не
менялось». Здесь пока сходится, и пусть сходится дальше само.

    python3 scripts/build_sitemap.py            # записать
    python3 scripts/build_sitemap.py --check    # сверить, ничего не трогая
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = "https://small-business-ru.aifrontier.tech"
# Частота и приоритет это подсказка обходчику, а не факт из файла, поэтому
# живут здесь. Порядок тот же, что был в карте, собранной руками.
PAGES = [
    ("index.html", "/", "monthly", "1.0"),
    ("kak-proverit-kontragenta-po-inn.html", "/kak-proverit-kontragenta-po-inn.html", "monthly", "0.9"),
    ("sroki-uplaty-usn-2026.html", "/sroki-uplaty-usn-2026.html", "monthly", "0.9"),
    ("nds-usn-porog-20-millionov.html", "/nds-usn-porog-20-millionov.html", "monthly", "0.9"),
    ("rabota-s-debitorskoy-zadolzhennostyu.html", "/rabota-s-debitorskoy-zadolzhennostyu.html", "monthly", "0.9"),
    ("vnedrenie.html", "/vnedrenie.html", "monthly", "0.6"),
]


def last_commit(rel: str) -> str:
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", f"docs/{rel}"],
                         cwd=ROOT, capture_output=True, text=True, check=True)
    return out.stdout.strip() or "1970-01-01"


def build() -> str:
    missing = [rel for rel, *_ in PAGES if not (DOCS / rel).exists()]
    if missing:
        raise SystemExit(f"в docs нет страниц из списка: {', '.join(missing)}")
    body = "\n".join(
        f"  <url>\n    <loc>{SITE}{url}</loc>\n"
        f"    <lastmod>{last_commit(rel)}</lastmod>\n"
        f"    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>"
        for rel, url, freq, pri in PAGES
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}\n</urlset>\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    target = DOCS / "sitemap.xml"
    fresh = build()
    if a.check:
        if not target.exists() or target.read_text(encoding="utf-8") != fresh:
            print("карта сайта разошлась с датами коммитов", file=sys.stderr)
            sys.exit(1)
        print("карта сайта совпадает с датами коммитов")
        return
    target.write_text(fresh, encoding="utf-8")
    print(f"записано: docs/sitemap.xml ({len(PAGES)} адресов)")


if __name__ == "__main__":
    main()
