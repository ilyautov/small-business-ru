# Зонтичный пак + паритет дистрибуции — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить `small-business-ru` в зонтичный пак, ставящий 3 плагина (операционка + humanizer-ru + marketplaces-mcp-ru) из одного маркетплейса, и подтянуть его дистрибуцию до уровня `humanizer-ru`.

**Architecture:** Мета-маркетплейс. Корневой `.claude-plugin/marketplace.json` перечисляет 3 плагина: локальный (`./small-business-ru`) и два внешних github-source, пиннутых на теги. Ноль вендоринга. MCP-обвязка WB/Ozon приезжает вместе с плагином `marketplaces-mcp-ru` (его собственный `.mcp.json` c `${CLAUDE_PLUGIN_ROOT}/serve.py`); в SBR-шаблон `.mcp.example.json` добавляется документированный альтернативный способ через `uvx`.

**Tech Stack:** Claude Code plugin marketplace (marketplace.json schema), JSON, Markdown, Python (`scripts/lint_skills.py`), `jq`.

**Спека:** `docs/superpowers/specs/2026-07-03-umbrella-pack-and-distribution-design.md`

**Факты, снятые до плана (не перепроверять):**
- Внешний github-source в marketplace.json **поддерживается** официально: `{"source":"github","repo":"owner/name","ref":"tag"}`. Маркетплейс и плагин могут быть в разных репо.
- `scripts/lint_skills.py` уже пропускает нестроковые (github/url) source — правка линтера не нужна.
- Теги для пиннинга: `humanizer-ru` → `v3.12.0` (MIT, category writing), `marketplaces-mcp-ru` → `v0.3.2` (MIT, category productivity).
- `marketplaces-mcp-ru/.mcp.json` запускает серверы через `python3 ${CLAUDE_PLUGIN_ROOT}/serve.py {wb|ozon|ozon-perf}`; токены: `WB_API_TOKEN`, `OZON_CLIENT_ID`, `OZON_API_KEY` (+ опц. `OZON_PERF_*`).

**Общее правило верификации:** после любой правки JSON — `jq . <файл>` должен пройти без ошибки; после правок в паке — `python3 scripts/lint_skills.py` должен вернуть 0.

---

## Фаза 1 — Пак (ядро запроса)

### Task 1: Внести humanizer-ru и marketplaces-mcp-ru в marketplace.json

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Verify current state (baseline)**

Run: `jq '.plugins | length' .claude-plugin/marketplace.json`
Expected: `1`

- [ ] **Step 2: Add the two external plugin entries**

В `.claude-plugin/marketplace.json` массив `plugins` сейчас содержит одну запись (`small-business-ru`, source `./small-business-ru`). Добавь после неё две записи. Итоговый `plugins` должен выглядеть так (первую запись НЕ меняй, только добавь две):

```json
"plugins": [
  {
    "name": "small-business-ru",
    "source": "./small-business-ru",
    "description": "Операционка малого бизнеса РФ: УСН-налоги, деньги, дебиторка, маржа, CRM, контент, проверка контрагента по ИНН. Локализация пака Anthropic small-business + killer-скиллы под РФ.",
    "category": "business"
  },
  {
    "name": "humanizer-ru",
    "source": { "source": "github", "repo": "ilyautov/humanizer-ru", "ref": "v3.12.0" },
    "description": "Убивает запах нейросети в русском тексте: 52 паттерна в 12 категориях, 20 жёстких банов, 3 режима, калибровка голоса, quad-pass аудит. Пригодится, чтобы очеловечить ответы клиентам, посты и письма из контентных скиллов пака. | Kills AI smell in Russian text.",
    "category": "writing"
  },
  {
    "name": "marketplaces-mcp-ru",
    "source": { "source": "github", "repo": "ilyautov/marketplaces-mcp-ru", "ref": "v0.3.2" },
    "description": "Два MCP-сервера над Seller API Wildberries (307 методов) и Ozon (441) + Ozon Performance (45): продажи, остатки, цены, финансы, отзывы напрямую из API, safety-гейт на запись, мультикабинет. | Wildberries & Ozon Seller APIs over MCP.",
    "category": "productivity"
  }
]
```

> **Почему `ref` на тег, а не `main`:** пак должен «просто работать» и не ломаться, когда в humanizer/MCP прилетит breaking change. Пиннинг на тег фиксирует известно-рабочую версию. Поднять версию потом — правка одной строки `ref`. Если хочешь всегда-свежую версию вместо стабильности — поставь `"ref": "main"`.

- [ ] **Step 3: Verify JSON validity + entry count**

Run: `jq '.plugins | length' .claude-plugin/marketplace.json`
Expected: `3`

Run: `jq -r '.plugins[].name' .claude-plugin/marketplace.json`
Expected: три строки — `small-business-ru`, `humanizer-ru`, `marketplaces-mcp-ru`

- [ ] **Step 4: Verify linter passes**

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0 (внешние source не проверяются структурно — это ожидаемо)

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat(marketplace): зонтичный пак — humanizer-ru и marketplaces-mcp-ru как плагины"
```

---

### Task 2: Добавить сервер WB/Ozon в шаблон .mcp.example.json

**Files:**
- Modify: `small-business-ru/.mcp.example.json`

- [ ] **Step 1: Verify baseline**

Run: `jq '.mcpServers | keys | length' small-business-ru/.mcp.example.json`
Expected: `11` (текущие плейсхолдеры-коннекторы)

- [ ] **Step 2: Add the marketplaces server block**

В `small-business-ru/.mcp.example.json` в объект `mcpServers` добавь новый ключ (в конец, после `yandex-metrika`). В отличие от прочих плейсхолдеров с пустым `url`, у этого — рабочая команда через `uvx` (пакет опубликован в PyPI):

```json
"marketplaces": {
  "_category": "~~маркетплейс",
  "_options": "Wildberries + Ozon Seller API. Отдельный пакет marketplaces-mcp-ru (PyPI). Ставится и как плагин: /plugin install marketplaces-mcp-ru@small-business-ru",
  "_env": "WB_API_TOKEN, OZON_CLIENT_ID, OZON_API_KEY (опц. OZON_PERF_CLIENT_ID / OZON_PERF_CLIENT_SECRET)",
  "command": "uvx",
  "args": ["marketplaces-mcp-ru"]
}
```

- [ ] **Step 3: Update the `_comment` header to mention the working server**

В `small-business-ru/.mcp.example.json` найди значение ключа `_comment`. В конец его строки допиши предложение:

```
 Исключение — сервер marketplaces (Wildberries/Ozon): у него рабочая команда uvx, а не пустой url; заполните токены кабинетов в окружении.
```

(Дописать внутрь существующей строки `_comment`, сохранив её как одну строку.)

- [ ] **Step 4: Verify JSON validity + key present**

Run: `jq -r '.mcpServers.marketplaces.command' small-business-ru/.mcp.example.json`
Expected: `uvx`

Run: `jq '.mcpServers | keys | length' small-business-ru/.mcp.example.json`
Expected: `12`

- [ ] **Step 5: Commit**

```bash
git add small-business-ru/.mcp.example.json
git commit -m "feat(mcp): шаблон подключения WB/Ozon MCP (uvx marketplaces-mcp-ru)"
```

---

### Task 3: Научить smb-router маршрутизировать в humanizer и маркетплейсы

**Files:**
- Modify: `small-business-ru/skills/smb-router/SKILL.md`

Роутер только предлагает/вызывает — он не форкает логику плагинов. Правки в трёх местах существующего файла.

- [ ] **Step 1: Add a routing category after the "Продажи и маркетинг" table**

В `small-business-ru/skills/smb-router/SKILL.md` найди блок `**Продажи и маркетинг:**` с его таблицей. Сразу после его таблицы (перед `**Клиенты и операции:**`) вставь новый блок:

```markdown
**Текст и маркетплейсы (расширенный пак):**
| Владелец говорит что-то вроде… | Направить к |
|---|---|
| «перепиши живее» / «убери канцелярит» / «звучит как робот» / «очеловечь» / «сделай текст человечным» | плагин `humanizer-ru` |
| «продажи на WB / Ozon» / «остатки» / «что дозаказать» / «мои цены на маркетплейсе» / «отзывы на WB» / «юнит-экономика Ozon» | плагин `marketplaces-mcp-ru` (сценарии кабинета) |

> Эти два — отдельные плагины зонтичного пака. Если они не установлены, подскажи: `/plugin install humanizer-ru@small-business-ru` или `/plugin install marketplaces-mcp-ru@small-business-ru`.
```

- [ ] **Step 2: Extend the "что ты умеешь?" catalogue (Шаг 4)**

В том же файле, в разделе `### Шаг 4 — Обработать «что ты умеешь?»`, после строки `**Настройка:** \`smb-onboard\`` добавь две строки:

```markdown
**Ваш текст:** плагин `humanizer-ru` — очеловечить ответы клиентам, посты, письма
**Ваши маркетплейсы:** плагин `marketplaces-mcp-ru` — WB + Ozon: продажи, остатки, цены, финансы, отзывы
```

- [ ] **Step 3: Add a cross-module hint to complaint/content flows**

В том же файле, в разделе `### Шаг 8 — Когда совпадения нет` найди конец раздела (перед `### Шаг 9`). Добавь абзац:

```markdown
**Сшивка модулей.** Когда операционный скилл выдаёт текст для клиента (ответ на жалобу через `/handle-complaint`, пост через `/run-campaign`, письмо): предложи финальный проход через `humanizer-ru`, чтобы текст не звучал роботом. Когда владелец говорит про продажи/остатки/отзывы на Wildberries или Ozon — это `marketplaces-mcp-ru`, а его выгрузку отзывов удобно затем разобрать теми же клиентскими скиллами.
```

- [ ] **Step 4: Verify skill still lints (body < 500 lines, frontmatter intact)**

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0

Run: `wc -l small-business-ru/skills/smb-router/SKILL.md`
Expected: < 500 строк (сейчас 233 + ~20)

- [ ] **Step 5: Commit**

```bash
git add small-business-ru/skills/smb-router/SKILL.md
git commit -m "feat(smb-router): маршрутизация в humanizer-ru и marketplaces-mcp-ru + сшивка модулей"
```

---

### Task 4: Секция «Что входит в пак» в README.md и USAGE.md

**Files:**
- Modify: `README.md`
- Modify: `USAGE.md`

- [ ] **Step 1: Add pack composition section to README.md**

В `README.md` найди заголовок `## Что внутри`. Сразу перед ним вставь новый раздел:

```markdown
## Что входит в зонтичный пак

С одного маркетплейса ставятся три модуля — берите нужные:

| Модуль | Что делает | Установка |
|---|---|---|
| **small-business-ru** | 34 скилла операционки: деньги, УСН-налоги, дебиторка, маржа, CRM, контент, найм, договоры, проверка контрагента | `/plugin install small-business-ru@small-business-ru` |
| **humanizer-ru** | Убирает запах нейросети из русского текста: ответы клиентам, посты, письма звучат по-человечески | `/plugin install humanizer-ru@small-business-ru` |
| **marketplaces-mcp-ru** | MCP-серверы Wildberries + Ozon: продажи, остатки, цены, финансы, отзывы прямо из Seller API | `/plugin install marketplaces-mcp-ru@small-business-ru` |

**Модули работают в связке.** Пример сквозного сценария:

> «Собери отзывы на Wildberries ниже 4★ за неделю» (marketplaces-mcp-ru) → «сгруппируй жалобы и подготовь ответы» (клиентские скиллы) → «очеловечь ответы» (humanizer-ru).

marketplaces-mcp-ru просит токены кабинетов (`WB_API_TOKEN`, `OZON_CLIENT_ID`, `OZON_API_KEY`); без них операционные скиллы всё равно работают через выгрузки CSV/Excel.
```

- [ ] **Step 2: Update the pack count line in README lead**

В `README.md` в первом абзаце и в бейджах фигурирует «34 скилла». Это по-прежнему верно для модуля small-business-ru — не меняй число скиллов. Вместо этого убедись, что новый раздел «Что входит в зонтичный пак» стоит выше `## Что внутри`, чтобы читатель сначала видел структуру пака из 3 модулей. (Проверка глазами, правок числа не требуется.)

- [ ] **Step 3: Add cross-module usage examples to USAGE.md**

В `USAGE.md` в конец файла добавь раздел:

```markdown
## Сквозные сценарии (модули пака вместе)

Когда установлены все три модуля, проси по-русски связки:

```
собери отзывы WB ниже 4 звёзд за неделю, сгруппируй жалобы по товару и подготовь ответы — потом очеловечь их
покажи продажи на WB и Ozon за месяц и посчитай маржу с учётом комиссий
что пора дозаказать на маркетплейсах, посчитай дни покрытия по остаткам
```

Первая часть каждой связки идёт через `marketplaces-mcp-ru` (реальные цифры из API), финальная шлифовка текста — через `humanizer-ru`, а расчёты маржи/налогов — через операционные скиллы.
```

- [ ] **Step 4: Verify markdown links intact**

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0 (линтер проверяет относительные ссылки в *.md)

- [ ] **Step 5: Commit**

```bash
git add README.md USAGE.md
git commit -m "docs: секция «Что входит в зонтичный пак» + сквозные сценарии"
```

---

### Task 5: CHANGELOG + бамп версии + smoke-проверка установки

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `.claude-plugin/marketplace.json` (metadata.version)
- Modify: `small-business-ru/.claude-plugin/plugin.json` (version)

- [ ] **Step 1: Bump versions 0.3.1-ru.1 → 0.4.0-ru.1**

В `.claude-plugin/marketplace.json` в объекте `metadata` замени `"version": "0.3.1-ru.1"` на `"version": "0.4.0-ru.1"`.

В `small-business-ru/.claude-plugin/plugin.json` замени `"version": "0.3.1-ru.1"` на `"version": "0.4.0-ru.1"`.

- [ ] **Step 2: Add CHANGELOG entry**

В `CHANGELOG.md` в самый верх (после заголовка файла, перед предыдущей записью) добавь:

```markdown
## 0.4.0-ru.1

### Добавлено
- **Зонтичный пак.** Маркетплейс `small-business-ru` теперь ставит три модуля: операционку, `humanizer-ru` (очеловечивание текста) и `marketplaces-mcp-ru` (Wildberries + Ozon через Seller API). Каждый — отдельный плагин, ставится по выбору.
- **Шаблон MCP WB/Ozon** в `.mcp.example.json` (`uvx marketplaces-mcp-ru`).
- **smb-router** маршрутизирует запросы очеловечивания и маркетплейсов и подсказывает сшивку модулей.
```

- [ ] **Step 3: Verify JSON validity of both changed manifests**

Run: `jq -r '.metadata.version' .claude-plugin/marketplace.json`
Expected: `0.4.0-ru.1`

Run: `jq -r '.version' small-business-ru/.claude-plugin/plugin.json`
Expected: `0.4.0-ru.1`

- [ ] **Step 4: Full lint gate**

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0

- [ ] **Step 5: Manual smoke-test of the marketplace (interactive — run yourself in Claude Code)**

Это ручная проверка вживую (не автотест). В Claude Code выполни:

```
/plugin marketplace add /Users/ilyautov/personal/small-business-ru
/plugin
```

Ожидается: в списке маркетплейса `small-business-ru` видны **три** плагина. Установка `humanizer-ru@small-business-ru` тянет внешний репо на теге v3.12.0. Если внешний источник не резолвится — проверь сеть/доступ к github и что тег существует (`git -C /Users/ilyautov/humanizer-ru tag | grep v3.12.0`).

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md .claude-plugin/marketplace.json small-business-ru/.claude-plugin/plugin.json
git commit -m "chore(release): 0.4.0-ru.1 — зонтичный пак из 3 модулей"
```

**✅ Конец Фазы 1. Пак собран и ставится. Дальше — паритет дистрибуции (можно как отдельная сессия).**

---

## Фаза 2 — Паритет дистрибуции с humanizer-ru

> Эталон структуры — репозиторий `humanizer-ru` (`/Users/ilyautov/humanizer-ru`). Сверяйся с его файлами при написании.

### Task 6: README.en.md

**Files:**
- Create: `README.en.md`

- [ ] **Step 1: Author English README mirroring README.md structure**

Создай `README.en.md` — структурный паритет с `README.md`: заголовок, «Why», «What's in the umbrella pack» (та же таблица из 3 модулей на английском), install, usage, «before/after», FAQ, disclaimers. Ориентир по тону и длине — `humanizer-ru/README.en.md` (`/Users/ilyautov/humanizer-ru/README.en.md`). Числа (34 скилла, 307/441/45 методов) сохрани.

- [ ] **Step 2: Add EN link to README.md top**

В `README.md` под первым заголовком добавь строку: `> 🇬🇧 [English version](README.en.md)` (как сделано в `marketplace-mcp/README.md`).

- [ ] **Step 3: Verify links**

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0

- [ ] **Step 4: Commit**

```bash
git add README.en.md README.md
git commit -m "docs: README.en.md (паритет с RU)"
```

---

### Task 7: Расширить секцию установки до уровня humanizer

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Extend the install section**

В `README.md` в разделе `## Установка` добавь недостающие пути (ориентир — раздел «Установка» в `/Users/ilyautov/humanizer-ru/README.md`), сохранив уже существующие блоки Claude Code / skills.sh / adapters:

- **Claude.ai (веб):** скачать ZIP репо → Settings → Capabilities → Skills → Upload skill.
- **Организации (Enterprise/Team):** Admin Console → Workspace Skills → Add skill.
- **API (`/v1/messages`):** передать скилл параметром `container.skills`.
- **Таблица «другие агенты»** (Copilot, Cline, Roo, Goose, OpenCode и т.п. читают `SKILL.md` нативно — скопировать папку скилла в каталог агента).

- [ ] **Step 2: Verify links**

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: полная секция установки (Claude.ai, Enterprise, API, другие агенты)"
```

---

### Task 8: Манифесты .codex-plugin, .cursor-plugin, gemini-extension.json

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `.cursor-plugin/plugin.json`
- Create: `gemini-extension.json`

Ориентиры — одноимённые файлы в `/Users/ilyautov/humanizer-ru/` (структуру полей бери оттуда).

- [ ] **Step 1: Create .codex-plugin/plugin.json**

Скопируй структуру из `/Users/ilyautov/humanizer-ru/.codex-plugin/plugin.json`, заменив контент под small-business-ru: name `small-business-ru`, version `0.4.0-ru.1`, описание пака, `"skills": "./small-business-ru/skills/"`, homepage `https://small-business-ru.aifrontier.tech/`, license `Apache-2.0`, поля `interface` (displayName «Small Business RU», category «Business», defaultPrompt «настрой меня»).

- [ ] **Step 2: Create .cursor-plugin/plugin.json**

Скопируй структуру из `/Users/ilyautov/humanizer-ru/.cursor-plugin/plugin.json`, адаптируй поля под small-business-ru (name, version, description, keywords, author).

- [ ] **Step 3: Create gemini-extension.json**

Скопируй структуру из `/Users/ilyautov/humanizer-ru/gemini-extension.json`, адаптируй name/version/description под small-business-ru.

- [ ] **Step 4: Verify all three are valid JSON**

Run: `for f in .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json; do echo "$f:"; jq -e . "$f" >/dev/null && echo OK || echo FAIL; done`
Expected: три `OK`

- [ ] **Step 5: Commit**

```bash
git add .codex-plugin .cursor-plugin gemini-extension.json
git commit -m "feat(dist): манифесты Codex, Cursor, Gemini"
```

---

### Task 9: PRIVACY_POLICY.md

**Files:**
- Create: `PRIVACY_POLICY.md`

- [ ] **Step 1: Author privacy policy**

Создай `PRIVACY_POLICY.md` по образцу `/Users/ilyautov/humanizer-ru/PRIVACY_POLICY.md`, адаптировав под small-business-ru: скилл — инструкция для агента пользователя, данные обрабатываются там, где работает его Claude/Cursor; коннекторы (1С, банк, CRM, WB/Ozon-токены) — на стороне пользователя; ничего не отправляется авторам пака.

- [ ] **Step 2: Verify links**

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0

- [ ] **Step 3: Commit**

```bash
git add PRIVACY_POLICY.md
git commit -m "docs: PRIVACY_POLICY.md"
```

---

### Task 10: SEO-лендинги docs/ + sitemap.xml + robots.txt

**Files:**
- Create: `docs/sitemap.xml`
- Create: `docs/robots.txt`
- Create: `docs/<2-3 SEO-страницы>.html`
- Modify: `docs/index.html` (перелинковка)

Ориентир — `/Users/ilyautov/humanizer-ru/docs/` (`sitemap.xml`, `robots.txt`, тематические HTML-лендинги под поисковые запросы).

- [ ] **Step 1: Pick 2-3 SEO topics and create landing pages**

Темы под реальные запросы малого бизнеса РФ, например: «как проверить контрагента по ИНН», «сроки уплаты УСН 2026», «как не влететь в НДС на 20 млн». Каждый HTML — по образцу тематических страниц в `humanizer-ru/docs/`, стиль из `docs/styles.css`, внутренние ссылки на index.html и GitHub.

- [ ] **Step 2: Create sitemap.xml and robots.txt**

`docs/sitemap.xml` — перечисли `index.html`, `vnedrenie.html` и новые лендинги (домен `https://small-business-ru.aifrontier.tech/`). `docs/robots.txt` — по образцу humanizer (`Allow: /`, ссылка на sitemap).

- [ ] **Step 3: Cross-link from index.html**

В `docs/index.html` добавь блок ссылок на новые лендинги (внизу или в разделе «Часто ищут»).

- [ ] **Step 4: Verify HTML/XML well-formedness**

Run: `xmllint --noout docs/sitemap.xml && echo "sitemap OK"`
Expected: `sitemap OK` (well-formedness). `xmllint` идёт с macOS. Если его нет — `python3 -c "import defusedxml.ElementTree as ET; ET.parse('docs/sitemap.xml'); print('OK')"` (defusedxml, не stdlib-парсер — защита от XXE/billion-laughs).

Run: `python3 scripts/lint_skills.py`
Expected: код возврата 0

- [ ] **Step 5: Commit**

```bash
git add docs/
git commit -m "feat(site): SEO-лендинги + sitemap + robots"
```

---

### Task 11: Регистрация в skills.sh (ручной внешний шаг)

**Files:** нет (внешнее действие).

- [ ] **Step 1: Register the pack on skills.sh**

Это действие вне репозитория. Проверь, что `npx skills add ilyautov/small-business-ru` резолвится, и при необходимости обнови листинг на skills.sh (как сделано для humanizer-ru: `skills.sh/ilyautov/humanizer-ru`). Если требуется файл-манифест для skills.sh — добавь его по образцу humanizer-ru и закоммить отдельно.

- [ ] **Step 2: Note completion**

Отметь в CHANGELOG под 0.4.0-ru.1 строку «Зарегистрировано в skills.sh», если листинг обновлён.

**✅ Конец Фазы 2. Дистрибуция на уровне humanizer-ru.**

---

## Self-Review (проведено при написании плана)

- **Покрытие спеки:** Модель A → Task 1. `.mcp.example` → Task 2. Роутинг → Task 3. README/USAGE секция пака → Task 4. Релиз → Task 5. Паритет: EN README (T6), install-секция (T7), манифесты Codex/Cursor/Gemini (T8), PRIVACY (T9), SEO+sitemap+robots (T10), skills.sh (T11). Все строки таблицы паритета из спеки покрыты.
- **Риск внешнего source:** снят до плана (docs + линтер) — зафиксировано в шапке.
- **Плейсхолдеры:** JSON-вставки даны целиком; для README-прозы указан файл-ориентир и точный якорь вставки. HTML-лендинги Фазы 2 намеренно оставлены как авторская работа с точным ориентиром (`humanizer-ru/docs/`) — не код-плейсхолдер.
- **Консистентность имён:** имена плагинов (`humanizer-ru`, `marketplaces-mcp-ru`), теги (`v3.12.0`, `v0.3.2`), команды установки (`plugin@small-business-ru`), версия бампа (`0.4.0-ru.1`) — совпадают во всех тасках.
