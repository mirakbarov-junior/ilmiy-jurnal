import os

# gunicorn config — runs init_db before workers start
def on_starting(server):
    from app import init_db
    init_db()

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 2
