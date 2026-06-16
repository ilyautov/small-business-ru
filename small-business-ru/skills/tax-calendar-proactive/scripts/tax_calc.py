#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tax_calc.py — точный калькулятор налогов ИП/УСН РФ. Считает КОДОМ, не «в уме»
(числа = реальные деньги клиента, ошибка дороже всего). Только stdlib.

Ставки/потолки берутся из реестра-канона tax_data.py (вендор-копия
finance-ru/nalog-ru, провенанс по НПА); значения совпадают с RULES.md раздел 4 (2026).
НЕ налоговая консультация — результат проверяет бухгалтер.

Запуск:
    python3 tax_calc.py --year 2026 --rejim usn6 --dohod 8000000 [опции]

Опции:
    --year       2025 | 2026 (год, за который считаем)
    --rejim      usn6 (Доходы 6%) | usn15 (Доходы-расходы 15%)
    --dohod      годовой доход, ₽
    --rashod     расходы за год (для usn15), ₽
    --rabotniki  есть ли работники: 0/1 (влияет на уменьшение аванса: без=100%, с=50%)
    --vznosy-uplacheno  сколько фикс.взносов уже уплачено, ₽ (по умолчанию 0)
    --vznosy-rabotniki  страховые взносы за работников за период, ₽ (usn6 с работниками:
                        входят в вычет вместе со своими, общий потолок 50% налога)
"""
import sys, json, argparse

# --- КОНСТАНТЫ ---
# Цифры 2026 берутся из единого канона tax_data.py (вендор-копия реестра Никиты
# Утова с привязкой к НПА и провенансом) — чтобы налоговые цифры не расходились
# между паками семьи. Историю 2024/2025 держим локально (в каноне только 2026).
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import tax_data as _td
    _C2026 = {
        "fix": _td.get("ip_fixed_vznosy"),       # 57390
        "cap": _td.get("ip_1pct_cap"),           # 321818
        "porog_1pct": _td.get("ip_1pct_threshold"),       # 300000
        "nds_porog": _td.get("usn_nds_exempt_threshold"), # 20_000_000
        "usn_limit": _td.get("usn_income_limit"),         # 490_500_000
    }
    _CANON = "tax_data.py (канон finance-ru/nalog-ru)"
except Exception:  # канон недоступен — зеркало тех же выверенных значений
    _C2026 = {"fix": 57390, "cap": 321818, "porog_1pct": 300_000,
              "nds_porog": 20_000_000, "usn_limit": 490_500_000}
    _CANON = "встроенное зеркало канона (tax_data.py не найден)"

FIX_VZNOS = {2024: 49500, 2025: 53658, 2026: _C2026["fix"]}     # фикс. взносы ИП «за себя»
CAP_1PCT  = {2024: 277571, 2025: 300888, 2026: _C2026["cap"]}   # потолок доп. взноса 1% по году
NDS_POROG = _C2026["nds_porog"]   # порог НДС для УСН (доход > → плательщик НДС)
USN_LIMIT = _C2026["usn_limit"]   # лимит дохода для применения УСН (2026)
POROG_1PCT = _C2026["porog_1pct"] # доход, свыше которого считается доп. 1%

def calc(year, rejim, dohod, rashod, rabotniki, vznosy_uplacheno, vznosy_rabotniki=0):
    warn = []
    if year not in FIX_VZNOS:
        return {"ошибка": f"нет выверенных ставок за {year} (есть 2024-2026)"}

    fix = FIX_VZNOS[year]

    # доп. взнос 1%
    if rejim == "usn6":
        baza_1pct = max(0, dohod - POROG_1PCT)
    elif rejim == "usn15":
        baza_1pct = max(0, dohod - rashod - POROG_1PCT)
        warn.append("usn15: с 2026 база 1% — за минусом взносов ОПС/ОМС; формула упрощена, уточнить у бухгалтера")
    else:
        return {"ошибка": "rejim: usn6 | usn15"}
    vznos_1pct_raw = round(baza_1pct * 0.01)
    cap = CAP_1PCT[year]
    vznos_1pct = min(vznos_1pct_raw, cap)
    if vznos_1pct_raw > cap:
        warn.append(f"доп.1% упёрся в потолок {cap:,} ₽ за {year} (сырой расчёт {vznos_1pct_raw:,})".replace(",", " "))

    vznosy_vsego = fix + vznos_1pct

    # налог УСН
    if rejim == "usn6":
        nalog_do_vycheta = round(dohod * 0.06)
        # уменьшение на взносы (с 2025 фикс. взносы уменьшают аванс независимо от факта уплаты):
        #  - без работников: на свои взносы (фикс + 1%) до 100% налога;
        #  - с работниками: на свои + за работников, но не более 50% налога.
        if rabotniki == 0:
            vychet = min(vznosy_vsego, nalog_do_vycheta)
        else:
            deductible = vznosy_vsego + vznosy_rabotniki
            predel = round(nalog_do_vycheta * 0.5)
            vychet = min(deductible, predel)
            if vznosy_rabotniki == 0:
                warn.append("указаны работники, но взносы за них = 0 — вычет посчитан только по своим взносам; если платите зарплаты, добавьте --vznosy-rabotniki для точного расчёта")
        nalog_k_uplate = max(0, nalog_do_vycheta - vychet)
    else:  # usn15
        baza = max(0, dohod - rashod)
        nalog_raschet = round(baza * 0.15)
        min_nalog = round(dohod * 0.01)
        nalog_k_uplate = max(nalog_raschet, min_nalog)
        nalog_do_vycheta = nalog_raschet
        vychet = 0
        if min_nalog > nalog_raschet:
            warn.append(f"сработал минимальный налог 1% от доходов ({min_nalog:,} ₽ > расчётного {nalog_raschet:,})".replace(",", " "))

    # НДС-порог
    nds = None
    if dohod > NDS_POROG:
        nds = f"⚠️ доход {dohod:,} ₽ > порога {NDS_POROG:,} ₽ → плательщик НДС (ставки 5/7/22%, выбор с бухгалтером)".replace(",", " ")
    else:
        ost = NDS_POROG - dohod
        if ost < 5_000_000:
            nds = f"приближение к НДС-порогу: осталось {ost:,} ₽ до 20 млн".replace(",", " ")

    if dohod > USN_LIMIT:
        warn.append(f"⚠️ доход превысил лимит УСН {USN_LIMIT:,} ₽ → слёт с УСН на ОСНО".replace(",", " "))

    if dohod == 0:
        warn.append(f"доход 0, но фикс. взнос {fix:,} ₽ платится ВСЁ РАВНО (пока ИП открыт)".replace(",", " "))

    def rub(x): return f"{x:,} ₽".replace(",", " ")
    return {
        "год": year, "режим": rejim, "доход": rub(dohod),
        "фикс_взнос": rub(fix),
        "доп_взнос_1пр": rub(vznos_1pct),
        "взносы_всего": rub(vznosy_vsego),
        "налог_усн_до_вычета": rub(nalog_do_vycheta),
        "уменьшение_на_взносы": rub(vychet),
        "налог_усн_к_уплате": rub(nalog_k_uplate),
        "итого_налоги_взносы": rub(nalog_k_uplate + vznosy_vsego),
        "ндс": nds,
        "предупреждения": warn,
        "_источник_цифр": _CANON,
        "_свежесть": _freshness_note(year),
        "_дисклеймер": "не налоговая консультация; сверьте с бухгалтером и ЛК ФНС; ставки на " + str(year),
    }


def _freshness_note(year):
    """Проактивно: известные плановые изменения налоговых порогов (из канона tax_data)."""
    try:
        if _td.stale("usn_nds_exempt_threshold", year + 1):
            nv = _td.current_value("usn_nds_exempt_threshold", year + 1)
            return f"порог НДС на УСН меняется со следующего года на {nv:,} ₽ — учтите заранее".replace(",", " ")
    except Exception:
        pass
    return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--rejim", default="usn6")
    p.add_argument("--dohod", type=float, required=True)
    p.add_argument("--rashod", type=float, default=0)
    p.add_argument("--rabotniki", type=int, default=0)
    p.add_argument("--vznosy-uplacheno", type=float, default=0)
    p.add_argument("--vznosy-rabotniki", type=float, default=0,
                   help="страховые взносы за работников за период, ₽ (для usn6 с работниками: входят в вычет, потолок 50%)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    res = calc(a.year, a.rejim, int(a.dohod), int(a.rashod), a.rabotniki, int(a.vznosy_uplacheno), int(a.vznosy_rabotniki))
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for k, v in res.items():
            if k == "предупреждения":
                for w in v: print("  ⚠️", w)
            elif v is not None and not k.startswith("_"):
                print(f"{k:24}: {v}")
        print(res["_дисклеймер"])

if __name__ == "__main__":
    main()
