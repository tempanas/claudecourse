# PythonAnywhere Free Deployment

## Почему PythonAnywhere

PythonAnywhere Free подходит для этого проекта, потому что бот может работать
через Telegram webhook. Не нужен постоянно запущенный polling-процесс:
Telegram отправляет POST-запрос на Flask-приложение, а приложение просыпается,
обрабатывает команду и отвечает через Telegram Bot API.

Банковская карта для Free account не нужна.

## 1. Создать free account

1. Откройте https://www.pythonanywhere.com/.
2. Создайте бесплатный аккаунт.
3. Запомните username. Он понадобится для URL вида:
   `https://<username>.pythonanywhere.com/`.

## 2. Загрузить проект из GitHub

В Bash console на PythonAnywhere:

```bash
git clone https://github.com/tempanas/claudecourse.git
cd claudecourse/zerocoder19-daily-meeting-bot
```

## 3. Создать virtualenv

```bash
python3.10 -m venv ~/.virtualenvs/zerocoder19-bot
source ~/.virtualenvs/zerocoder19-bot/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Если на аккаунте доступна другая версия Python 3, используйте её и выберите ту
же версию в настройках Web app.

## 4. Создать `.env` на PythonAnywhere

В корне проекта создайте файл `.env` вручную. Не публикуйте его в Git.

```dotenv
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
WEBHOOK_SECRET=your_long_random_secret
PYTHONANYWHERE_USERNAME=your_pythonanywhere_username
GOOGLE_CALENDAR_ID_1=primary
GOOGLE_CALENDAR_ID_2=
GOOGLE_CALENDAR_ID_3=
GOOGLE_CALENDAR_ID_4=
GOOGLE_CALENDAR_ID_5=
TIMEZONE=Europe/Minsk
USE_DEMO_MODE=true
```

Для Google Calendar режима установите `USE_DEMO_MODE=false`.

## 5. Загрузить `credentials.json` и `token.json`

Файлы `credentials.json` и `token.json` нельзя коммитить.

Вариант для демо:

- оставить `USE_DEMO_MODE=true`;
- не загружать Google-файлы.

Вариант для Google Calendar:

1. Локально пройти OAuth и получить `token.json`.
2. Загрузить `credentials.json` и `token.json` в корень проекта на
   PythonAnywhere через Files или Bash.
3. Проверить, что файлы лежат рядом с `README.md`.

## 6. Настроить Web app

1. Откройте вкладку **Web**.
2. Нажмите **Add a new web app**.
3. Выберите manual configuration.
4. Выберите Python 3.
5. В поле virtualenv укажите:

```text
/home/<username>/.virtualenvs/zerocoder19-bot
```

## 7. Настроить WSGI file

В Web app откройте WSGI configuration file и замените содержимое на шаблон:

```python
import sys

project_path = "/home/<username>/claudecourse/zerocoder19-daily-meeting-bot"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from src.webhook_app import app as application
```

Замените `<username>` на ваш PythonAnywhere username.

## 8. Установить Telegram webhook

В Bash console выполните:

```bash
cd ~/claudecourse/zerocoder19-daily-meeting-bot
source ~/.virtualenvs/zerocoder19-bot/bin/activate
set -a
source .env
set +a
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://${PYTHONANYWHERE_USERNAME}.pythonanywhere.com/${WEBHOOK_SECRET}"
```

Проверить webhook:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

## 9. Проверить команды

1. Откройте Telegram.
2. Напишите боту `/health`.
3. Ожидаемый ответ:

```text
✅ Бот работает через PythonAnywhere webhook
```

4. Проверьте `/today`.
5. Проверьте `/tomorrow`.

Если сообщение длинное, webhook делит его на части до 3900 символов.

## 10. Обновлять код через `git pull`

```bash
cd ~/claudecourse
git pull
cd zerocoder19-daily-meeting-bot
source ~/.virtualenvs/zerocoder19-bot/bin/activate
pip install -r requirements.txt
```

После обновления нажмите **Reload** на вкладке Web.

## 11. Что нельзя публиковать

Нельзя коммитить и отправлять в публичные места:

- `.env`;
- `credentials.json`;
- `token.json`;
- реальные Telegram-токены;
- реальные Zoom-ссылки;
- ФИО, телефоны и email;
- скриншоты с секретами.

Секреты должны храниться только на локальной машине или в приватных файлах на
PythonAnywhere.
