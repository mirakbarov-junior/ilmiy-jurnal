# Ilmiy Jurnal — инструкция по запуску

## Локальный запуск (для теста)

```bash
pip install -r requirements.txt
python run.py
```
Открой http://localhost:5000

**Админ-панель:** http://localhost:5000/admin/login  
Логин: `admin` / Пароль: `admin123`

---

## Деплой на Railway (бесплатно)

1. Зарегистрируйся на https://railway.app
2. Нажми **New Project → Deploy from GitHub repo**
3. Залей эту папку на GitHub (или используй Railway CLI)
4. В разделе **Variables** добавь:

   | Переменная       | Значение              |
   |------------------|-----------------------|
   | `SECRET_KEY`     | любая длинная строка  |
   | `ADMIN_USER`     | твой логин            |
   | `ADMIN_PASSWORD` | твой пароль           |

5. Railway сам найдёт `Procfile` и задеплоит.

> ⚠️ **Важно:** На бесплатном Railway файлы (PDF) сбрасываются при перезапуске.  
> Для постоянного хранения PDF нужен S3 / Cloudflare R2 (скажи — добавлю).

---

## Деплой на Render (бесплатно)

1. https://render.com → **New Web Service**
2. Подключи GitHub репозиторий
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app -c gunicorn_config.py`
5. Добавь те же переменные окружения (`SECRET_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD`)

---

## Структура проекта

```
journal/
├── app.py              # основное приложение Flask
├── run.py              # запуск локально
├── requirements.txt    # зависимости
├── Procfile            # для Railway/Render
├── gunicorn_config.py  # конфиг gunicorn (инициализация БД)
├── journal.db          # SQLite база (создаётся автоматически)
├── static/
│   └── uploads/        # загруженные PDF
└── templates/
    ├── base.html
    ├── index.html
    ├── article.html
    ├── login.html
    └── admin.html
```
