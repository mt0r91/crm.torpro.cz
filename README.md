# TORPRO CRM — Python/Flask

## Локальный запуск

```bash
pip install -r requirements.txt
python app.py
```

Открыть: http://localhost:3000

## Логины

| Email | Пароль | Роль |
|-------|--------|------|
| admin@torpro.cz | admin123 | Администратор |
| marek@torpro.cz | sales123 | Менеджер |
| jana@torpro.cz | sales123 | Продажи |

## Деплой на Railway (бесплатно, 5 минут)

1. Зарегистрироваться: https://railway.app (через GitHub)
2. New Project → Deploy from GitHub → выбрать этот репозиторий
3. Railway сам найдёт Procfile и запустит
4. Settings → Variables → добавить `SECRET_KEY=ваш_секрет`
5. Получить ссылку: Settings → Domains → Generate Domain

## Деплой на Render (альтернатива, тоже бесплатно)

1. https://render.com → New Web Service
2. Подключить GitHub репозиторий
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Add env var: `SECRET_KEY=ваш_секрет`

## Переменные окружения

- `SECRET_KEY` — секрет сессий (важно поменять!)
- `DB_PATH` — путь к SQLite (по умолчанию `crm.db`)
- `PORT` — порт (ставится автоматически)
