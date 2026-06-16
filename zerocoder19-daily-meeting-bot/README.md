# Zerocoder19 Daily Meeting Bot

## 1. Название проекта

**Zerocoder19 Daily Meeting Bot**

## 2. Краткое описание

Telegram-бот для ежедневного контроля встреч из календаря. Бот показывает
расписание на сегодня и завтра, ищет Zoom-ссылки в событиях и помечает встречи,
которые нужно проверить вручную.

> Зерокодер19 - название должности, а не имя человека.

## 3. Проблема

В работе Зерокодер19 нужно контролировать консультации, Q&A, Zoom-встречи и
другие живые созвоны. Перед началом дня важно быстро понять:

- какие встречи стоят в календаре;
- во сколько они начинаются;
- есть ли в событии ссылка для подключения;
- какие события требуют ручной проверки.

Если проверять календарь вручную, можно потратить лишнее время или поздно
заметить встречу без Zoom-ссылки.

## 4. Пользователь

Основной пользователь - специалист в должности Зерокодер19, который отвечает за
контроль живых встреч, консультаций, Q&A и своевременность проведения созвонов.

## 5. Основная функция

Бот по команде в Telegram показывает список встреч на выбранный день и для
каждой встречи сообщает, найдена ли Zoom-ссылка.

Если Zoom-ссылка не найдена, бот добавляет действие: проверить событие в
календаре.

## 6. MVP-функции

- команда `/today` показывает встречи на сегодня;
- команда `/tomorrow` показывает встречи на завтра;
- команда `/demo` показывает работу на обезличенных демо-данных;
- демо-режим работает без Google Calendar и секретных ключей;
- Google Calendar режим читает реальные события через Calendar API;
- бот поддерживает до 5 Google Calendar ID отдельными строками в `.env`;
- бот использует часовой пояс из `TIMEZONE`;
- Zoom-ссылки ищутся в `description`, `location`, `hangoutLink` и
  `conferenceData.entryPoints`;
- события без Zoom помечаются как требующие проверки;
- локальные секреты не должны попадать в Git.

## 7. Команды бота

| Команда | Назначение |
| --- | --- |
| `/start` | Приветствие и краткое описание |
| `/help` | Справка по командам |
| `/health` | Проверка статуса, режима и часового пояса |
| `/demo` | Демонстрация на `data/sample_events.json` |
| `/caldebug` | Диагностика календаря, диапазона и первых событий |
| `/calendars` | Список календарей Google аккаунта |
| `/today` | Встречи на сегодня |
| `/tomorrow` | Встречи на завтра |

## 8. Технологии

- Python 3.9+
- python-telegram-bot
- Google Calendar API
- google-auth-oauthlib
- python-dotenv
- JSON для демо-событий
- Markdown-документация

## 9. Структура проекта

```text
zerocoder19-daily-meeting-bot/
├── .claude/skills/zerocoder19-calendar-bot/skill.md
├── data/sample_events.json
├── images/.gitkeep
├── reports/demo_result.md
├── reports/final-demo-script.md
├── reports/final-project-description.md
├── deploy/PYTHONANYWHERE_DEPLOYMENT.md
├── src/__init__.py
├── src/bot.py
├── src/calendar_service.py
├── src/config.py
├── src/demo_calendar_service.py
├── src/formatter.py
├── src/webhook_app.py
├── src/zoom_parser.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

Локальные файлы `.env`, `credentials.json`, `token.json` и `.venv/` могут быть
в проекте во время запуска, но не должны публиковаться.

## 10. Как запустить локально

Создайте виртуальное окружение и установите зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_CALENDAR_ID_1=primary
GOOGLE_CALENDAR_ID_2=
GOOGLE_CALENDAR_ID_3=
GOOGLE_CALENDAR_ID_4=
GOOGLE_CALENDAR_ID_5=
TIMEZONE=Europe/Minsk
USE_DEMO_MODE=true
```

Запустите бота из корня проекта:

```bash
python3 -m src.bot
```

Проверяйте бота только в личном тестовом чате, не в реальных рабочих чатах.

## 11. Как включить демо-режим

Демо-режим нужен для показа проекта без Google Calendar, OAuth и секретных
ключей.

В `.env` установите:

```dotenv
USE_DEMO_MODE=true
```

Демо-сервис читает `data/sample_events.json`. Поле `day_offset` делает события
многоразовыми:

- `0` - текущий день;
- `1` - следующий день.

Для проверки используйте команды:

```text
/demo
/today
/tomorrow
```

## 12. Как подключить Google Calendar

Интеграция использует OAuth 2.0 и scope только на чтение:

```text
https://www.googleapis.com/auth/calendar.readonly
```

Шаги подключения:

1. Откройте [Google Cloud Console](https://console.cloud.google.com/).
2. Создайте проект или выберите тестовый проект.
3. Включите **Google Calendar API**.
4. Настройте OAuth consent screen.
5. Создайте OAuth Client ID типа **Desktop app**.
6. Скачайте JSON-файл.
7. Переименуйте файл в `credentials.json`.
8. Положите `credentials.json` в корень проекта.
9. В `.env` установите `USE_DEMO_MODE=false`.
10. Запустите бота командой `python3 -m src.bot`.
11. Выполните `/today` или `/tomorrow`.
12. При первом запросе откроется браузер для авторизации.
13. После успешной авторизации будет создан локальный `token.json`.

Пример настроек:

```dotenv
GOOGLE_CALENDAR_ID_1=primary
GOOGLE_CALENDAR_ID_2=
GOOGLE_CALENDAR_ID_3=
GOOGLE_CALENDAR_ID_4=
GOOGLE_CALENDAR_ID_5=
TIMEZONE=Europe/Minsk
USE_DEMO_MODE=false
```

Если `credentials.json` отсутствует, бот вернёт сообщение:

```text
credentials.json не найден в корне проекта. Скачайте OAuth Client ID типа Desktop app из Google Cloud Console и положите файл в корень проекта.
```

Официальная инструкция:
[Google Calendar Python quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python).

## Как подключить 5 календарей

Бот поддерживает до 5 календарей отдельными строками в `.env`.

1. Включите Google Calendar режим: `USE_DEMO_MODE=false`.
2. Запустите бота: `python3 -m src.bot`.
3. Отправьте команду `/calendars`.
4. Бот покажет доступные календари: `summary`, `id`, `primary`,
   `accessRole`.
5. Скопируйте `id` нужных календарей.
6. Вставьте их в `.env`:

```dotenv
GOOGLE_CALENDAR_ID_1=primary
GOOGLE_CALENDAR_ID_2=calendar_id_2@group.calendar.google.com
GOOGLE_CALENDAR_ID_3=calendar_id_3@group.calendar.google.com
GOOGLE_CALENDAR_ID_4=calendar_id_4@group.calendar.google.com
GOOGLE_CALENDAR_ID_5=calendar_id_5@group.calendar.google.com
```

Пустые строки можно оставить пустыми:

```dotenv
GOOGLE_CALENDAR_ID_1=primary
GOOGLE_CALENDAR_ID_2=
GOOGLE_CALENDAR_ID_3=
GOOGLE_CALENDAR_ID_4=
GOOGLE_CALENDAR_ID_5=
```

После изменения `.env` перезапустите бота.

Приоритет настройки календарей:

1. `GOOGLE_CALENDAR_ID_1` ... `GOOGLE_CALENDAR_ID_5`;
2. `GOOGLE_CALENDAR_IDS=primary,calendar_id_2,calendar_id_3`;
3. `GOOGLE_CALENDAR_ID=primary`;
4. fallback `primary`.

## Бесплатный деплой на PythonAnywhere через webhook

Локально проект можно запускать через polling:

```bash
python3 -m src.bot
```

Для бесплатного деплоя на PythonAnywhere используется отдельное Flask webhook
приложение:

```text
src/webhook_app.py
```

Почему webhook:

- на PythonAnywhere Free не нужен постоянно работающий polling-процесс;
- бот просыпается по команде Telegram;
- Python остаётся основной технологией проекта;
- банковская карта для Free account не нужна;
- секреты хранятся только в `.env` на PythonAnywhere и не публикуются.

Webhook принимает POST-запросы Telegram по секретному URL:

```text
https://<PYTHONANYWHERE_USERNAME>.pythonanywhere.com/<WEBHOOK_SECRET>
```

Поддерживаемые webhook-команды:

- `/start`;
- `/help`;
- `/health`;
- `/today`;
- `/tomorrow`.

Для `/today` и `/tomorrow` используется та же логика проекта:

- `USE_DEMO_MODE=true` - события из `data/sample_events.json`;
- `USE_DEMO_MODE=false` - события из Google Calendar;
- Zoom-ссылки очищаются через `zoom_parser.py`;
- длинные ответы делятся на части до 3900 символов.

Подробная инструкция:
[deploy/PYTHONANYWHERE_DEPLOYMENT.md](deploy/PYTHONANYWHERE_DEPLOYMENT.md).

## 13. Как создать Telegram-бота через BotFather

1. Откройте Telegram.
2. Найдите официального бота `@BotFather`.
3. Отправьте команду `/newbot`.
4. Укажите название бота.
5. Укажите username бота, который заканчивается на `bot`.
6. Скопируйте выданный token.
7. Вставьте token только в локальный `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

Не публикуйте токен в README, GitHub, скриншотах или сообщениях.

## 14. Какие файлы нельзя публиковать

Нельзя коммитить и отправлять в публичные места:

- `.env`;
- `.env.local`;
- `credentials.json`;
- `token.json`;
- реальные Telegram-токены;
- реальные Zoom-ссылки;
- ФИО, телефоны и email участников;
- скриншоты с личными данными.

`credentials.json` содержит OAuth client ID и client secret приложения.
`token.json` содержит пользовательские access/refresh tokens. Эти файлы уже
указаны в `.gitignore`.

## Почему проект полезен для Зерокодер19

Проект закрывает ежедневную операционную боль: быстро понять, какие встречи
запланированы и какие из них не готовы к проведению из-за отсутствия
Zoom-ссылки.

Вместо ручного просмотра календаря Зерокодер19 получает короткую сводку прямо в
Telegram. Это помогает заранее заметить проблемные события, открыть календарь и
добавить недостающую ссылку до начала созвона.

## 15. Скриншоты

Скриншоты демо можно хранить в `images/`. Перед добавлением изображения нужно
убедиться, что на нём нет токенов, реальных профилей, личных данных и настоящих
ссылок на встречи.

Пример будущих файлов:

```text
images/demo_today.png
images/demo_tomorrow.png
```

## 16. Планы развития

- добавить автоматические напоминания о встречах без Zoom;
- добавить фильтр по типу события: консультация, Q&A, внутренняя встреча;
- добавить ежедневную утреннюю сводку по расписанию;
- добавить тесты для Google Calendar нормализации;
- улучшить обработку ошибок API;
- добавить Dockerfile для развёртывания;
- добавить деплой на сервер или облачную платформу.

## Дополнительные материалы

- [Ожидаемый результат демо](reports/demo_result.md)
- [Описание финального проекта](reports/final-project-description.md)
- [Сценарий защиты](reports/final-demo-script.md)
