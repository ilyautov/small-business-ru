# Дизайн: `small-business-ru` как зонтичный пак + паритет дистрибуции

**Дата:** 2026-07-03
**Статус:** утверждён (дефолты приняты пользователем)
**Автор:** Илья Утов (через Claude Code)

## Цель

Две связанные задачи:

1. **Расширить пак** — сделать `small-business-ru` зонтичным паком, который ставит не только 34 операционных скилла, но и сам `humanizer-ru`, и MCP-серверы Wildberries/Ozon (`marketplaces-mcp-ru`).
2. **Паритет дистрибуции** — подтянуть каналы дистрибуции `small-business-ru` до уровня самого зрелого репозитория линейки, `humanizer-ru` (RU+EN README, полный набор адаптеров/манифестов, SEO-лендинги, PRIVACY_POLICY, регистрация в skills.sh).

## Контекст (три репозитория)

| Репо | Что это | Дистрибуция сейчас |
|---|---|---|
| `small-business-ru` | 34 скилла операционки РФ, роутер `smb-router` | `docs/` сайт (aifrontier.tech), `.claude-plugin/marketplace.json`, `adapters/` (3 killer-скилла), CHANGELOG. Частичная. |
| `humanizer-ru` | 1 большой скилл (SKILL.md, v3.12.0) + сканер | Эталон: RU+EN README, `.claude-plugin` + `.codex-plugin` + `.cursor-plugin` + `gemini-extension.json`, docs/ с SEO-лендингами + sitemap + robots, eval/, specs/, CHANGELOG/SECURITY/PRIVACY. Маркетплейс `ilyautov-plugins`. |
| `marketplaces-mcp-ru` | 2 MCP-сервера над Seller API WB (307) + Ozon (441) + Ozon Perf (45), 793 метода | PyPI (`marketplaces-mcp-ru`) + MCP Registry (`server.json`) + `.mcpb`-бандл + install-скрипты + мульти-платформенные плагины. Маркетплейс `marketplaces-mcp-ru`. |

Все три под `github.com/ilyautov/*`, владелец один.

## Модель пака: A — мета-маркетплейс

`marketplace.json` в `small-business-ru` перечисляет **три плагина**, каждый живёт в своём репозитории. Ноль дублирования кода.

```
small-business-ru/.claude-plugin/marketplace.json
  plugins:
    - small-business-ru    → ./small-business-ru        (локальный source)
    - humanizer-ru         → github: ilyautov/humanizer-ru
    - marketplaces-mcp-ru  → github: ilyautov/marketplaces-mcp-ru
```

### Почему A (а не вендоринг/гибрид)

- **Против вендоринга:** humanizer уже v3.12.0 и активно обновляется — копия SKILL.md в `skills/` протухнет за дни. MCP — это сервер (PyPI-пакет + токены кабинета), а не скилл; копировать его код в скилл-пак неправильно.
- **Готовность:** у всех трёх уже есть валидные `.claude-plugin/plugin.json` — они складываются в один маркетплейс без переделки внутренностей.
- **Лицензии не конфликтуют:** SBR под Apache-2.0, humanizer и MCP под MIT — каждый плагин несёт свою лицензию, смешение в одном маркетплейсе допустимо.

### Пользовательский путь

```
/plugin marketplace add ilyautov/small-business-ru
/plugin install small-business-ru@small-business-ru      # операционка
/plugin install humanizer-ru@small-business-ru           # очеловечивание текста
/plugin install marketplaces-mcp-ru@small-business-ru    # WB + Ozon
```

Плюс `.mcp.example.json` в SBR получает категорию `~~маркетплейс` с готовой строкой подключения MCP (`uvx marketplaces-mcp-ru`), чтобы связать сервер в один шаг.

### Технический риск (проверить первым)

Поддерживает ли `marketplace.json` внешний git-source для плагина
(`{"source":"github","repo":"ilyautov/humanizer-ru"}` или git-URL-форма).

- **Если да** — схема выше работает как есть.
- **Если нет** — фолбэк: git-submodule двух репозиториев внутрь SBR, source остаётся `./`. Это единственная развилка реализации; её надо снять до всего остального.

## Объём: обе цели, фазами

### Фаза 1 — Пак (ядро запроса)

1. `.claude-plugin/marketplace.json` → 3 плагина (после снятия риска внешнего source).
2. `small-business-ru/.mcp.example.json` → добавить сервер WB/Ozon: категория `~~маркетплейс`, команда `uvx marketplaces-mcp-ru`, ссылка на `.env.example` за токенами.
3. README.md + USAGE.md → секция «Что входит в пак»: три модуля (операционка / очеловечивание / маркетплейсы) + сквозные сценарии, где модули работают вместе. Пример: «собери отзывы WB ниже 4★ (MCP) → напиши ответы клиентам → очеловечь их (humanizer)».
4. `smb-router` → научить распознавать запросы про очеловечивание текста и про WB/Ozon и маршрутизировать в соответствующий плагин (см. решение по роутингу ниже).

### Фаза 2 — Паритет дистрибуции с `humanizer-ru`

| Канал | SBR сейчас | Цель |
|---|---|---|
| `README.en.md` | ✗ | добавить |
| Секция установки (Claude.ai ZIP-upload, Enterprise admin console, API `container.skills`, ручная, таблица «другие агенты») | лёгкая | до уровня humanizer |
| `.codex-plugin/` + `.cursor-plugin/` + `gemini-extension.json` (манифесты, не только `adapters/`) | только `adapters/` | добавить манифесты |
| `docs/` SEO-лендинги + `sitemap.xml` + `robots.txt` | index + vnedrenie | расширить |
| `PRIVACY_POLICY.md` | ✗ | добавить |
| skills.sh листинг | частично | зарегистрировать |

## Решение по роутингу

`smb-router` **активно** предлагает humanizer и MCP-сценарии внутри операционных потоков (не оставляет их отдельными «немыми» вызовами). Конкретно:

- Триггеры очеловечивания («перепиши живее», «убери канцелярит», «звучит как робот») → предложить/вызвать humanizer-ru.
- Триггеры маркетплейсов («продажи на WB», «остатки Ozon», «отзывы», «что дозаказать») → предложить/вызвать сценарии marketplaces-mcp-ru.
- Внутри контентных/клиентских скиллов SBR (ответы на жалобы, посты, кампании) — предлагать финальный проход humanizer как опцию.

Роутер только предлагает и вызывает; он не форкает логику плагинов.

## YAGNI (сознательно НЕ делаем)

- Не вендорим humanizer/MCP внутрь SBR (протухнет; нарушает разделение репозиториев).
- Не публикуем SBR в PyPI / MCP Registry — там нет Python-пакета, это скилл-пак.
- Не форкаем логику под стеки — тело одно (`SKILL.md`), меняются только обёртки, как уже заведено в `adapters/`.
- Не трогаем внутренности humanizer-ru и marketplaces-mcp-ru — они подключаются как есть.

## Критерии готовности

**Фаза 1:**
- `/plugin marketplace add ilyautov/small-business-ru` показывает все 3 плагина.
- Каждый из трёх ставится и активируется.
- `.mcp.example.json` содержит рабочий (после подстановки токенов) блок WB/Ozon.
- README/USAGE описывают пак из 3 модулей и минимум 1 сквозной сценарий.
- `smb-router` распознаёт и маршрутизирует запросы очеловечивания и маркетплейсов.

**Фаза 2:**
- Все строки таблицы паритета закрыты.
- README.en.md паритетен README.md по структуре.
- Манифесты `.codex-plugin` / `.cursor-plugin` / `gemini-extension.json` присутствуют и валидны.

## Открытые вопросы к реализации

1. Снять риск внешнего git-source в `marketplace.json` (главная развилка Фазы 1).
2. Точная форма подключения MCP в `.mcp.example.json`: `uvx` vs `.mcpb`-бандл vs http — выбрать по тому, что стабильнее для конечного пользователя-непрограммиста.
