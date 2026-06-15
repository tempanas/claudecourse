# Урок 7: альтернатива MCP через Codex и Playwright

Демонстрация подключения браузерного инструмента к desktop Codex для проверки локального лендинга.

## Состав

- `index.html`, `styles.css`, `script.js` — проверяемый локальный лендинг;
- `scripts/check_landing_with_playwright.js` — автоматизированная браузерная проверка;
- `reports/2026-06-playwright-consultation-landing-audit.md` — отчёт по SEO, UX и безопасности данных;
- `reports/2026-06-mcp-alternative-implementation-note.md` — пояснение альтернативы Claude Code MCP;
- `temp/consultation-landing-screenshot.png` — полноэкранный скриншот результата.

## Локальный запуск сайта

Из папки `cln07-mcp-audit`:

```bash
python3 -m http.server 8080
```

Открыть:

```text
http://127.0.0.1:8080
```

## Запуск проверки

В desktop Codex, где доступен bundled Playwright:

```bash
node scripts/check_landing_with_playwright.js
```

Скрипт сначала открывает локальный сервер на порту `8080`. Если сервер недоступен, он использует локальный `index.html`. Никакие данные не отправляются во внешние сервисы.
