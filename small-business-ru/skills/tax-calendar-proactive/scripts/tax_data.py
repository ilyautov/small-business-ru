#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ВЕНДОР-КОПИЯ канона из finance-ru/skills/nalog-ru/scripts/tax_data.py (пак Никиты Утова).
# Единый источник правды по налоговым цифрам РФ для всех паков RU Business Packs.
# НЕ форкать здесь: правки вносить в канон finance-ru и синхронизировать сюда.
"""
tax_data — ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ для налоговых констант РФ + их провенанс.

Зачем: цифры не разбросаны по calc_*.py и references/*.md, а собраны здесь с
привязкой к НПА (первоисточнику) и проверочной ссылке. verify_data.py сверяет,
что код не разошёлся с реестром, и сигналит, когда цифра пора пересверить.

Поля записи:
  value, unit, year   — значение и период
  npa                 — ПЕРВОИСТОЧНИК: статья НК / номер ФЗ / постановление
  src_tier            — "НПА"  : ссылка ведёт на официальный текст акта
                        "обзор": ссылка на разбор (НПА указан в npa, текст сверь)
  source              — URL для проверки
  verified, tier      — дата веб-сверки; online/reference
  code_const          — "<модуль>.<ИМЯ>": с чем сверяется код
  future              — известное расписание изменений {год: значение}
"""

SCHEMA = "tax-data/v2"
DATA_YEAR = 2026

TAX_DATA = {
    "ip_fixed_vznosy": {
        "value": 57390, "unit": "руб/год", "year": 2026,
        "npa": "НК РФ ст.430 п.1.2", "src_tier": "НПА",
        "source": "https://www.consultant.ru/document/cons_doc_LAW_28165/c03008a92ccba28226abe4034e9aa43e3a2ffeb4/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_vznosy.FIX_IP_2026",
        "note": "Срок 28.12.2026. Суммы по годам прямо в ст.430 (2025: 53 658).",
    },
    "ip_1pct_cap": {
        "value": 321818, "unit": "руб/год", "year": 2026,
        "npa": "НК РФ ст.430 п.1.2 (потолок доп. взноса)", "src_tier": "НПА",
        "source": "https://www.consultant.ru/document/cons_doc_LAW_28165/c03008a92ccba28226abe4034e9aa43e3a2ffeb4/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_vznosy.EXTRA_CAP_2026",
        "note": "Макс всего за год = 57 390 + 321 818 = 379 208.",
    },
    "ip_1pct_threshold": {
        "value": 300000, "unit": "руб", "year": 2026,
        "npa": "НК РФ ст.430 п.1 (1% сверх 300 тыс)", "src_tier": "НПА",
        "source": "https://www.consultant.ru/document/cons_doc_LAW_28165/c03008a92ccba28226abe4034e9aa43e3a2ffeb4/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_vznosy.EXTRA_THRESHOLD",
        "note": "Порог стабилен много лет.",
    },
    "emp_base_limit": {
        "value": 2979000, "unit": "руб/год", "year": 2026,
        "npa": "Постановление Правительства РФ от 31.10.2025 N 1705", "src_tier": "НПА",
        "source": "https://www.consultant.ru/document/cons_doc_LAW_518016/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_vznosy.BASE_LIMIT_2026",
        "note": "Единая предельная база. Сверх — тариф 30%→15.1% (в коде упрощено, см. assumptions).",
    },
    "mrot": {
        "value": 27093, "unit": "руб/мес", "year": 2026,
        "npa": "ФЗ от 28.11.2025 N 429-ФЗ (ст.1 ФЗ-82)", "src_tier": "НПА",
        "source": "https://www.consultant.ru/law/ref/mrot/2026/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_vznosy.MROT_2026",
        "note": "С 01.01.2026. 1.5×МРОТ = 40 639.5 — порог МСП-тарифа.",
    },
    "nds_general_rate": {
        "value": 0.22, "unit": "доля", "year": 2026,
        "npa": "НК РФ ст.164 п.3 (ред. ФЗ от 28.11.2025 N 425-ФЗ)", "src_tier": "обзор",
        "source": "https://www.buhgalteria.ru/article/obzor-izmeneniy-v-nk-rf-s-2026-goda-po-zakonu-425-fz-ot-28-11-2025",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_nds.GENERAL",
        "note": "Ставка НДС 20→22% с 01.01.2026. Льготная 10% сохранена.",
    },
    "usn_nds_exempt_threshold": {
        "value": 20000000, "unit": "руб/год", "year": 2026,
        "npa": "НК РФ ст.145 (ред. ФЗ N 425-ФЗ)", "src_tier": "обзор",
        "source": "https://www.garant.ru/news/1913232/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_nds.EXEMPT_THRESHOLD",
        "note": "Порог дохода, с которого УСН платит НДС.",
        "future": {2027: 15000000, 2028: 10000000},
    },
    "nds_5pct_income_max": {
        "value": 272500000, "unit": "руб/год", "year": 2026,
        "npa": "НК РФ ст.164 п.8 + Приказ Минэк от 06.11.2025 N 734 (дефлятор 1.09)", "src_tier": "НПА",
        "source": "https://www.garant.ru/products/ipo/prime/doc/412941387/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_nds.R5_MAX",
        "note": "Ставка 5% — доход 20…272.5 млн (250 млн × 1.09).",
    },
    "nds_7pct_income_max": {
        "value": 490500000, "unit": "руб/год", "year": 2026,
        "npa": "НК РФ ст.164 п.8 + Приказ Минэк от 06.11.2025 N 734 (дефлятор 1.09)", "src_tier": "НПА",
        "source": "https://www.garant.ru/products/ipo/prime/doc/412941387/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_nds.R7_MAX",
        "note": "Ставка 7% — доход 272.5…490.5 млн; совпадает с лимитом УСН.",
    },
    "usn_income_limit": {
        "value": 490500000, "unit": "руб/год", "year": 2026,
        "npa": "НК РФ ст.346.13 п.4 + Приказ Минэк от 06.11.2025 N 734 (дефлятор 1.09)", "src_tier": "НПА",
        "source": "https://www.garant.ru/products/ipo/prime/doc/412941387/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "compare_regimes.USN_LIMIT",
        "note": "490.5 млн = 450 млн × 1.09.",
    },
    "psn_income_limit": {
        "value": 20000000, "unit": "руб/год", "year": 2026,
        "npa": "НК РФ ст.346.45 п.6 (ред. ФЗ N 425-ФЗ)", "src_tier": "обзор",
        "source": "https://www.kontur-extern.ru/info/37547-vse_o_patente_dlya_ip",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "compare_regimes.PSN_INCOME_LIMIT",
        "note": "Лимит ПСН 2026 — 20 млн; расписание 2027 — 15, 2028 — 10.",
        "future": {2027: 15000000, 2028: 10000000},
    },
    "npd_limit": {
        "value": 2400000, "unit": "руб/год", "year": 2026,
        "npa": "ФЗ от 27.11.2018 N 422-ФЗ ст.4 п.2 п.8", "src_tier": "обзор",
        "source": "https://www.consultant.ru/law/podborki/predelnyj_dohod_samozanyatogo/",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "compare_regimes.NPD_LIMIT",
        "note": "2.4 млн, заморожен до конца эксперимента (2028).",
    },
    "ausn_limit": {
        "value": 60000000, "unit": "руб/год", "year": 2026,
        "npa": "ФЗ от 25.02.2022 N 17-ФЗ (АУСН)", "src_tier": "обзор",
        "source": "https://kontur.ru/articles/4535",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "compare_regimes.AUSN_LIMIT",
        "note": "Лимит 60 млн + не более 5 сотрудников. Обсуждалось снижение — пересверяй.",
    },
    "ausn_travm_fixed": {
        "value": 2959, "unit": "руб/год", "year": 2026,
        "npa": "ФЗ от 25.02.2022 N 17-ФЗ ст.18 (фикс. травматизм, индексируется)", "src_tier": "обзор",
        "source": "https://kontur.ru/articles/4535",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "compare_regimes.AUSN_TRAVM",
        "note": "2 959 руб/год, не зависит от числа работников.",
    },
    "psn_rate": {
        "value": 0.06, "unit": "доля", "year": 2026,
        "npa": "НК РФ ст.346.50 (ставка 6%)", "src_tier": "обзор",
        "source": "https://www.kontur-extern.ru/info/47099-kriterii_sroki_i_poryadok_uplaty_dlya_psn",
        "verified": "2026-06-16", "tier": "online",
        "code_const": "calc_psn.RATE",
        "note": "Базовая ставка ПСН 6% сохранена на 2026 (регион может 0%).",
    },
}


def get(key):
    return TAX_DATA[key]["value"]


def stale(key, today_year):
    fut = TAX_DATA[key].get("future") or {}
    return any(y <= today_year for y in fut)


def current_value(key, today_year):
    fut = TAX_DATA[key].get("future") or {}
    applicable = [y for y in fut if y <= today_year]
    return fut[max(applicable)] if applicable else TAX_DATA[key]["value"]


if __name__ == "__main__":
    import json
    npa = sum(1 for v in TAX_DATA.values() if v["src_tier"] == "НПА")
    print(json.dumps({"schema": SCHEMA, "data_year": DATA_YEAR,
                      "keys": len(TAX_DATA), "src_НПА": npa,
                      "src_обзор": len(TAX_DATA) - npa}, ensure_ascii=False, indent=2))
