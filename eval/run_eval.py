#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_eval.py — прогон контрольных точек для детерминированных калькуляторов.

Зачем: killer-фича пака — «числа считаются кодом, сверены на контрольных точках».
Этот харнес и есть та сверка: гоняет tax_calc.py на наборе сценариев с заранее
выверенными вручную результатами и падает, если расчёт разъехался.

Покрыт пока tax_calc.py (УСН/ИП). Это НЕ eval поведения LLM — только детерминированной
арифметики, которая и должна считаться кодом, а не моделью.

Запуск из корня репо:   python3 eval/run_eval.py
Код выхода: 0 — все точки сошлись, 1 — есть расхождения.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = json.loads((Path(__file__).parent / "control_points.json").read_text(encoding="utf-8"))


def num(s):
    """'345 610 ₽' -> 345610"""
    return int(re.sub(r"[^0-9]", "", s or "") or 0)


def run_case(script, args):
    out = subprocess.run(
        [sys.executable, str(ROOT / script), *args, "--json"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return None, out.stderr.strip()
    return json.loads(out.stdout), None


def run_error_case(script, c):
    """Кейс, где скрипт ОБЯЗАН упасть с кодом ≠ 0 и внятной ошибкой."""
    out = subprocess.run(
        [sys.executable, str(ROOT / script), *c["args"], "--json"],
        capture_output=True, text=True,
    )
    fails = []
    if out.returncode == 0:
        fails.append(f"ждали код выхода ≠ 0, получили 0 (ошибка замаскирована под успех)")
    combined = out.stdout + out.stderr
    want = c.get("error_contains")
    if want and want not in combined:
        fails.append(f"нет подстроки «{want}» в выводе ошибки: {combined.strip()[:80]!r}")
    return fails


def check(result, expect):
    fails = []
    for key, want in expect.items():
        if key == "warn":
            got = len(result.get("предупреждения", []))
            if got != want:
                fails.append(f"warn: ждали {want}, получили {got}")
        elif key == "ндс_contains":
            got = result.get("ндс") or ""
            if want not in got:
                fails.append(f"ндс: нет подстроки «{want}» (получили: {got[:50]!r})")
        elif key == "ндс":
            got = result.get("ндс")
            if want is None and got is not None:
                fails.append(f"ндс: ждали пусто, получили {got[:50]!r}")
        else:
            got = num(result.get(key))
            if got != want:
                fails.append(f"{key}: ждали {want}, получили {got}")
    return fails


def check_mirror_sync(script):
    """Встроенное зеркало 2026 в tax_calc обязано побайтово совпадать с каноном tax_data.
    Ловит дрейф: канон обновили, зеркало забыли."""
    scripts_dir = ROOT / Path(script).parent
    sys.path.insert(0, str(scripts_dir))
    try:
        import tax_data as td
        import tax_calc as tc
        canon = {
            "fix": td.get("ip_fixed_vznosy"),
            "cap": td.get("ip_1pct_cap"),
            "porog_1pct": td.get("ip_1pct_threshold"),
            "nds_porog": td.get("usn_nds_exempt_threshold"),
            "usn_limit": td.get("usn_income_limit"),
        }
        mirror = getattr(tc, "_MIRROR_2026", None)
        if mirror is None:
            return ["в tax_calc.py нет _MIRROR_2026 — зеркало канона не проверяемо"]
        diffs = [f"{k}: канон {canon[k]}, зеркало {mirror.get(k)}"
                 for k in canon if mirror.get(k) != canon[k]]
        return diffs
    finally:
        sys.path.pop(0)


def main():
    cases = SPEC["cases"]
    script = SPEC["script"]
    passed = 0
    print(f"eval: {script}\n{'='*64}")
    for c in cases:
        if c.get("expect_error"):
            fails = run_error_case(script, c)
        else:
            result, err = run_case(script, c["args"])
            if err:
                print(f"✗ ОШИБКА ЗАПУСКА  {c['name']}\n    {err}")
                continue
            fails = check(result, c["expect"])
        if not fails:
            passed += 1
            print(f"✓ {c['name']}")
        else:
            print(f"✗ {c['name']}")
            for f in fails:
                print(f"    {f}")
    mirror_fails = check_mirror_sync(script)
    total = len(cases) + 1
    if not mirror_fails:
        passed += 1
        print("✓ зеркало канона 2026 в tax_calc совпадает с tax_data")
    else:
        print("✗ зеркало канона 2026 разошлось с tax_data:")
        for f in mirror_fails:
            print(f"    {f}")
    print("=" * 64)
    print(f"итог: {passed}/{total} контрольных точек сошлись")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
