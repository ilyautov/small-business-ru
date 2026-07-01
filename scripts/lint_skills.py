#!/usr/bin/env python3
"""
lint_skills.py — структурный линт монорепо ru-business-packs. Только stdlib.

Проверяет (НЕ содержание, а структуру/гигиену):
  • каждый skills/<name>/SKILL.md: есть frontmatter с name, name == имя папки,
    есть description, тело < 500 строк (стандарт качества разд. A);
  • каждый плагин: валидный .claude-plugin/plugin.json с полем name;
  • marketplace.json: валидный JSON; каждый локальный source существует и
    содержит .claude-plugin/plugin.json; имя в записи == name плагина;
  • относительные ссылки во всех отслеживаемых git *.md ведут на существующие
    файлы (битая ссылка на scripts/reference — ошибка);
  • каждый скилл skills/<name>/ упомянут в README своего пака.

Запуск:  python3 scripts/lint_skills.py
Код возврата 1 при любой ошибке (для CI). Предупреждения не валят сборку.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_LINES = 500

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def parse_frontmatter(path):
    """Возвращает dict верхнеуровневых ключей frontmatter (грубо, без YAML-депа)."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return None, len(lines)
    fm, body_start = {}, None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        # верхнеуровневый ключ: начинается не с пробела, формат key:
        if lines[i] and not lines[i][0].isspace() and ":" in lines[i]:
            k, _, v = lines[i].partition(":")
            fm[k.strip()] = v.strip()
    if body_start is None:
        return None, len(lines)
    return fm, len(lines)


def lint_skill(skill_md, expected_name):
    rel = os.path.relpath(skill_md, ROOT)
    fm, nlines = parse_frontmatter(skill_md)
    if fm is None:
        err(f"{rel}: нет валидного YAML-frontmatter (--- ... ---)")
        return
    name = fm.get("name", "").strip().strip('"').strip("'")
    if not name:
        err(f"{rel}: нет поля name в frontmatter")
    elif name != expected_name:
        err(f"{rel}: name='{name}' ≠ имя папки '{expected_name}'")
    if "description" not in fm:
        err(f"{rel}: нет поля description")
    if nlines > MAX_LINES:
        err(f"{rel}: {nlines} строк > {MAX_LINES} (стандарт A)")


def lint_plugin(pack_dir):
    pj = os.path.join(pack_dir, ".claude-plugin", "plugin.json")
    name = os.path.basename(pack_dir)
    if not os.path.isfile(pj):
        err(f"{name}: нет .claude-plugin/plugin.json")
        return None
    try:
        with open(pj, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        err(f"{name}/.claude-plugin/plugin.json: невалидный JSON ({e})")
        return None
    if "name" not in data:
        err(f"{name}/.claude-plugin/plugin.json: нет поля name")
    if "description" not in data:
        warn(f"{name}/.claude-plugin/plugin.json: нет description")
    # скиллы пака
    skills_dir = os.path.join(pack_dir, "skills")
    n_skills = 0
    if os.path.isdir(skills_dir):
        for sk in sorted(os.listdir(skills_dir)):
            smd = os.path.join(skills_dir, sk, "SKILL.md")
            if os.path.isfile(smd):
                n_skills += 1
                lint_skill(smd, sk)
    if n_skills == 0:
        warn(f"{name}: нет skills/<name>/SKILL.md (пак пустой?)")
    return data.get("name")


def lint_marketplace(plugin_names):
    mp = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(mp):
        err("нет корневого .claude-plugin/marketplace.json")
        return
    try:
        with open(mp, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        err(f"marketplace.json: невалидный JSON ({e})")
        return
    for entry in data.get("plugins", []):
        nm = entry.get("name", "?")
        src = entry.get("source")
        if isinstance(src, str):  # локальный путь
            sp = os.path.normpath(os.path.join(ROOT, src))
            pj = os.path.join(sp, ".claude-plugin", "plugin.json")
            if not os.path.isdir(sp):
                err(f"marketplace: '{nm}' source '{src}' — папки нет")
            elif not os.path.isfile(pj):
                err(f"marketplace: '{nm}' source '{src}' — нет .claude-plugin/plugin.json")
            else:
                actual = plugin_names.get(os.path.basename(sp))
                if actual and actual != nm:
                    warn(f"marketplace: запись '{nm}' ≠ plugin.json name '{actual}' ({src})")
        # внешние source (github/url) — не проверяем структуру


MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def tracked_md_files():
    """Все отслеживаемые git markdown-файлы (пустой список, если git недоступен)."""
    try:
        out = subprocess.run(["git", "-C", ROOT, "ls-files", "*.md"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode != 0:
            return []
        return out.stdout.splitlines()
    except Exception:
        return []


def lint_md_links():
    """Относительная ссылка в markdown обязана вести на существующий файл.
    Внешние (http/mailto) и якоря не проверяем."""
    for rel in tracked_md_files():
        path = os.path.join(ROOT, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        # ссылки внутри код-блоков и инлайн-кода — иллюстрации, не проверяем
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`\n]*`", "", text)
        for target in MD_LINK_RE.findall(text):
            if "://" in target or target.startswith(("mailto:", "#", "tel:")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            base = ROOT if target.startswith("/") else os.path.dirname(path)
            resolved = os.path.normpath(os.path.join(base, target.lstrip("/") if target.startswith("/") else target))
            if not os.path.exists(resolved):
                err(f"{rel}: битая ссылка «{target}» — файла нет")


def lint_readme_skill_sync(pack_dir):
    """Каждая папка skills/<name> должна быть упомянута в README пака."""
    readme = os.path.join(pack_dir, "README.md")
    pack = os.path.basename(pack_dir)
    skills_dir = os.path.join(pack_dir, "skills")
    if not os.path.isdir(skills_dir):
        return
    if not os.path.isfile(readme):
        warn(f"{pack}: нет README.md — сверка списка скиллов пропущена")
        return
    with open(readme, encoding="utf-8") as fh:
        text = fh.read()
    for sk in sorted(os.listdir(skills_dir)):
        if not os.path.isfile(os.path.join(skills_dir, sk, "SKILL.md")):
            continue
        if sk not in text:
            err(f"{pack}/README.md: скилл «{sk}» существует, но не упомянут в README")


def tracked_top_dirs():
    """Топ-уровневые папки, отслеживаемые git. None если git недоступен —
    тогда линтим всё на ФС. Так стрэй-папки вне репо не попадают в линт."""
    try:
        out = subprocess.run(["git", "-C", ROOT, "ls-files"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode != 0:
            return None
        return {line.split("/", 1)[0] for line in out.stdout.splitlines() if "/" in line}
    except Exception:
        return None


def main():
    plugin_names = {}
    packs = []
    tracked = tracked_top_dirs()
    for d in sorted(os.listdir(ROOT)):
        full = os.path.join(ROOT, d)
        if tracked is not None and d not in tracked:
            continue  # стрэй-папка вне git-репо — не линтим
        if os.path.isdir(full) and os.path.isdir(os.path.join(full, ".claude-plugin")) \
                and os.path.isfile(os.path.join(full, ".claude-plugin", "plugin.json")):
            packs.append(full)
    for pack in packs:
        nm = lint_plugin(pack)
        if nm:
            plugin_names[os.path.basename(pack)] = nm
        lint_readme_skill_sync(pack)
    lint_marketplace(plugin_names)
    lint_md_links()

    print(f"Проверено паков: {len(packs)}")
    for w in warnings:
        print(f"  ⚠️  {w}")
    for e in errors:
        print(f"  ❌ {e}")
    if errors:
        print(f"\nFAIL: {len(errors)} ошибок, {len(warnings)} предупреждений")
        return 1
    print(f"\nOK: 0 ошибок, {len(warnings)} предупреждений")
    return 0


if __name__ == "__main__":
    sys.exit(main())
