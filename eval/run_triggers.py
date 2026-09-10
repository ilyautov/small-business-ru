#!/usr/bin/env python3
"""Trigger-eval пака small-business-ru: проверяет, что описания РАЗЛИЧАЮТ скиллы.

Зачем отдельно от lint_skills.py. Линтер ловит буквальное совпадение фраз у двух
скиллов. Этого мало: «кассовый разрыв» у cash-flow-snapshot и «закрой кассовый
разрыв» у invoice-chase не совпадают как строки, но живой запрос про кассовый
разрыв задевает оба. Здесь проверяется не текст описаний, а их РАЗДЕЛЯЮЩАЯ СИЛА
на реалистичных запросах.

Как считается. По описанию каждого скилла собирается набор заявленных триггерных
фраз (та же функция, что в линтере). Для запроса скилл получает балл за каждую
свою фразу, встреченную в запросе, весом в длину фразы: более длинная и более
конкретная формулировка должна побеждать свою же подстроку. Ожидаемый скилл
обязан стать ЕДИНСТВЕННЫМ лидером. Ничья это провал, потому что ничья и есть та
самая неоднозначность, ради которой всё затевалось.

Чем это НЕ является. Живое решение «какой скилл звать» принимает модель по
смыслу запроса, и скриптом это не воспроизвести. Здесь честный поверхностный
прокси той части решения, что видна в тексте: заявленные автором формулировки.
Прокси ловит регресс описаний (кто-то расширил формулировку и залез в соседа) и
не ловит семантику. Так же устроен eval/run_triggers.py в humanizer-ru.

Гейт (код возврата):
  - обычный скилл без единой триггерной фразы          -> exit 1 (недобор);
  - ожидаемый скилл не стал единственным лидером       -> exit 1;
  - отрицательный кейс задел хоть один скилл           -> exit 1.

Запуск:
    python3 eval/run_triggers.py            # гоняется в CI
    python3 eval/run_triggers.py --verbose  # показать баллы по каждому кейсу
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import lint_skills as L  # noqa: E402  (нужен ROOT в sys.path)

CORPUS = os.path.join(ROOT, "eval", "triggers.json")


def load_skills():
    """{имя скилла: набор триггерных фраз} только для обычной формы.

    Командную форму (allowed-tools) сюда не берём: её вызывают по имени, фраз у
    неё быть не должно, и за это отвечает lint_skills.lint_command_form_triggers.
    """
    out = {}
    for pack in sorted(os.listdir(ROOT)):
        skills_dir = os.path.join(ROOT, pack, "skills")
        if not os.path.isdir(skills_dir):
            continue
        for sk in sorted(os.listdir(skills_dir)):
            smd = os.path.join(skills_dir, sk, "SKILL.md")
            if not os.path.isfile(smd):
                continue
            fm, _ = L.parse_frontmatter(smd)
            if not fm or "allowed-tools" in fm:
                continue
            out[sk] = L._trigger_phrases(L._description_of(smd))
    return out


# Русский язык ломает сравнение подстрокой: «закрой месяц» из описания и
# «надо закрыть месяц» из живого запроса это одно и то же намерение и разные
# строки, «сверка» и «сделай сверку» тоже. Модель разницы не заметит, скрипт
# заметит и соврёт. Поэтому и фраза, и запрос приводятся к последовательности
# усечённых основ. Стеммер намеренно тупой и без зависимостей: режем только
# длинный хвост у длинного слова, коротким словам не трогаем ничего. Он даёт
# ложные сближения («налог» и «налоговый»), и это осознанный размен: пропущенное
# совпадение прячет реальную неоднозначность, лишнее совпадение её показывает.
_ENDINGS = (
    "ениями", "ениям", "ением", "ения", "ение", "ений",
    "ываешь", "ываете", "ывают", "ывает", "ывать",
    "ишься", "ется", "ются", "ться", "тесь",
    "ами", "ями", "ого", "его", "ому", "ему", "ыми", "ими",
    "ая", "яя", "ое", "ее", "ые", "ие", "ой", "ей", "ый", "ий",
    "ам", "ям", "ах", "ях", "ом", "ем", "ов", "ев", "ью",
    "ла", "ло", "ли", "ть", "ти", "чь", "ит", "ет", "ут", "ют", "ат", "ят",
    "а", "я", "о", "е", "у", "ю", "ы", "и", "й", "ь",
)


def _stem(word):
    for e in _ENDINGS:
        if len(word) - len(e) >= 4 and word.endswith(e):
            return word[: -len(e)]
    return word


def _stems(text):
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower())
    return [_stem(w) for w in cleaned.split()]


def _contains(haystack, needle):
    """Последовательность основ needle встречается в haystack подряд."""
    if not needle or len(needle) > len(haystack):
        return False
    for i in range(len(haystack) - len(needle) + 1):
        if haystack[i:i + len(needle)] == needle:
            return True
    return False


def score(prompt, phrases):
    """Балл скилла на запросе: сумма длин его фраз, встреченных в запросе."""
    hay = _stems(prompt)
    hits = [p for p in phrases if _contains(hay, _stems(p))]
    return sum(len(p) for p in hits), hits


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    skills = load_skills()
    failures = []

    empty = sorted(n for n, ph in skills.items() if not ph)
    if empty:
        failures.append("обычная форма без триггерных фраз: " + ", ".join(empty))

    with open(args.corpus, encoding="utf-8") as fh:
        cases = json.load(fh)["cases"]

    passed = 0
    for c in cases:
        scored = {}
        for name, phrases in skills.items():
            s, hits = score(c["prompt"], phrases)
            if s:
                scored[name] = (s, hits)
        top = sorted(scored.items(), key=lambda kv: -kv[1][0])
        expect = c["expect"]

        if expect == "none":
            ok = not scored
            detail = "задет: " + ", ".join(n for n, _ in top) if scored else "чисто"
        else:
            ok = bool(top) and top[0][0] == expect and (
                len(top) == 1 or top[0][1][0] > top[1][1][0])
            if not top:
                detail = "не сработал никто"
            elif top[0][0] != expect:
                detail = f"победил {top[0][0]} вместо {expect}"
            elif len(top) > 1 and top[0][1][0] == top[1][1][0]:
                detail = f"ничья: {top[0][0]} и {top[1][0]}"
            else:
                detail = f"{expect} по фразам {top[0][1][1]}"

        passed += ok
        if not ok:
            failures.append(f"[{c['id']}] {detail} | {c['prompt'][:70]}")
        if args.verbose:
            mark = "✓" if ok else "✗"
            print(f"{mark} [{c['id']:>2}] {c['category']:<16} {detail}")

    print(f"\n[инфо] кейсов {len(cases)}, сошлось {passed}, скиллов в разборе {len(skills)}")
    if failures:
        print("\n[ПРОВАЛ] trigger-eval:")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("[gate] ✓ каждый запрос уходит ровно в один скилл, отрицательные чисты")
    return 0


if __name__ == "__main__":
    sys.exit(main())
