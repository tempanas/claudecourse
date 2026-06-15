---
name: zerocoder19-calendar-bot
description: Maintain and extend the Zerocoder19 Daily Meeting Bot repository. Use when an AI agent needs to inspect the project structure, run or test demo mode, add Telegram commands, implement Google Calendar access, update anonymized demo events, maintain documentation, or prepare the repository for safe publication.
---

# Zerocoder19 Calendar Bot

## Preserve the product contract

- Treat "Zerocoder19" as a job title, not a person's name.
- Keep demo mode working without Google credentials.
- Never add real names, phones, emails, Telegram tokens, or Zoom meetings.
- Never send test messages to real work chats.
- Keep `.env`, `credentials.json`, and `token.json` untracked.

## Understand the structure

- Use `src/bot.py` for Telegram handlers and application wiring.
- Use `src/config.py` for environment settings.
- Keep calendar providers behind the interface in `src/calendar_service.py`.
- Use `src/demo_calendar_service.py` and `data/sample_events.json` for demos.
- Use `src/zoom_parser.py` only for Zoom URL extraction.
- Use `src/formatter.py` for user-facing Telegram messages.
- Update `README.md` and `reports/demo_result.md` when behavior changes.

## Run and verify

1. Create `.env` from `.env.example` and keep `USE_DEMO_MODE=true`.
2. Install dependencies from `requirements.txt`.
3. Run `python -m src.bot`.
4. Test `/health`, `/demo`, `/today`, and `/tomorrow` in a private test chat.
5. Run local module checks with `PYTHONPATH=src python -m compileall src`.
6. Verify that events with Zoom show `Zoom: найден ✅`.
7. Verify that events without Zoom show `Zoom: не найден ⚠️` and a calendar
   check action.

## Add a command

1. Add an async handler in `src/bot.py`.
2. Register it in `build_application`.
3. Add it to `HELP_TEXT` and the README command table.
4. Keep command output HTML-safe when using Telegram HTML parse mode.
5. Test without contacting production chats.

## Maintain Google Calendar

1. Keep Google OAuth and event normalization in `src/calendar_service.py`.
2. Preserve the normalized event shape used by the demo provider.
3. Query only the requested local day using the configured `TIMEZONE`.
4. Read the calendar ID from `GOOGLE_CALENDAR_ID`.
5. Search Zoom links in description, location, `hangoutLink`, and conference
   entry points.
6. Handle all-day events, missing fields, pagination, and API errors.
7. Keep OAuth files local and ignored by Git.
8. Retain demo mode as the default fallback and test surface.

## Prepare publication

1. Review `git status` and staged changes.
2. Search for tokens, credentials, personal data, and real meeting URLs.
3. Confirm `.gitignore` protects all secret files.
4. Run syntax and behavior checks.
5. Ensure README setup steps match the current implementation.
