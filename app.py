import os
import sqlite3
from functools import wraps
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_from_directory, abort)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production-please')

# --- CONFIG ---
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATABASE     = os.path.join(BASE_DIR, 'journal.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXT  = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USER     = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')


# ── DB helpers ──────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS issues (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                title     TEXT    NOT NULL,
                volume    TEXT,
                number    TEXT,
                year      TEXT,
                published TEXT,
                created   TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS articles (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id   INTEGER REFERENCES issues(id) ON DELETE CASCADE,
                title      TEXT NOT NULL,
                authors    TEXT NOT NULL,
                abstract   TEXT,
                pages      TEXT,
                filename   TEXT,
                created    TEXT DEFAULT (datetime('now'))
            );
        """)
        # seed a default issue if empty
        row = db.execute("SELECT id FROM issues LIMIT 1").fetchone()
        if not row:
            db.execute("""
                INSERT INTO issues (title, volume, number, year, published)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "Yangi O'zbekiston taraqqiyotida tadqiqotlarni o'rni va rivojlanish omillari",
                "3", "1", "2024", "2023-12-26"
            ))
            db.commit()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# ── Auth ─────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── PUBLIC ROUTES ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    issues = db.execute("SELECT * FROM issues ORDER BY id DESC").fetchall()
    latest = issues[0] if issues else None
    articles = []
    if latest:
        articles = db.execute(
            "SELECT * FROM articles WHERE issue_id=? ORDER BY id", (latest['id'],)
        ).fetchall()
    return render_template('index.html', issue=latest, articles=articles, issues=issues)


@app.route('/issue/<int:issue_id>')
def issue(issue_id):
    db = get_db()
    iss = db.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    if not iss:
        abort(404)
    articles = db.execute(
        "SELECT * FROM articles WHERE issue_id=? ORDER BY id", (issue_id,)
    ).fetchall()
    issues = db.execute("SELECT * FROM issues ORDER BY id DESC").fetchall()
    return render_template('index.html', issue=iss, articles=articles, issues=issues)


@app.route('/article/<int:article_id>')
def article(article_id):
    db  = get_db()
    art = db.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
    if not art:
        abort(404)
    iss = db.execute("SELECT * FROM issues WHERE id=?", (art['issue_id'],)).fetchone()
    return render_template('article.html', article=art, issue=iss)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ── ADMIN AUTH ────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_USER and
                request.form['password'] == ADMIN_PASSWORD):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash('Неверный логин или пароль', 'error')
    return render_template('login.html')


@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ── ADMIN PANEL ───────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin():
    db = get_db()
    issues   = db.execute("SELECT * FROM issues ORDER BY id DESC").fetchall()
    articles = db.execute("""
        SELECT a.*, i.title AS issue_title
        FROM articles a JOIN issues i ON a.issue_id=i.id
        ORDER BY a.id DESC
    """).fetchall()
    return render_template('admin.html', issues=issues, articles=articles)


# ── ISSUES CRUD ───────────────────────────────────────────────────────────

@app.route('/admin/issue/add', methods=['POST'])
@login_required
def add_issue():
    db = get_db()
    db.execute("""
        INSERT INTO issues (title, volume, number, year, published)
        VALUES (?,?,?,?,?)
    """, (
        request.form['title'],
        request.form['volume'],
        request.form['number'],
        request.form['year'],
        request.form['published'],
    ))
    db.commit()
    flash('Выпуск добавлен', 'ok')
    return redirect(url_for('admin'))


@app.route('/admin/issue/delete/<int:issue_id>', methods=['POST'])
@login_required
def delete_issue(issue_id):
    db = get_db()
    # delete PDFs of articles in this issue
    rows = db.execute("SELECT filename FROM articles WHERE issue_id=?", (issue_id,)).fetchall()
    for r in rows:
        if r['filename']:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, r['filename']))
            except FileNotFoundError:
                pass
    db.execute("DELETE FROM issues WHERE id=?", (issue_id,))
    db.commit()
    flash('Выпуск удалён', 'ok')
    return redirect(url_for('admin'))


# ── ARTICLES CRUD ─────────────────────────────────────────────────────────

@app.route('/admin/article/add', methods=['POST'])
@login_required
def add_article():
    db   = get_db()
    file = request.files.get('pdf_file')
    filename = None

    if file and file.filename and allowed_file(file.filename):
        safe = secure_filename(file.filename)
        # avoid collisions
        unique = f"{int(datetime.now().timestamp())}_{safe}"
        file.save(os.path.join(UPLOAD_FOLDER, unique))
        filename = unique

    db.execute("""
        INSERT INTO articles (issue_id, title, authors, abstract, pages, filename)
        VALUES (?,?,?,?,?,?)
    """, (
        request.form['issue_id'],
        request.form['title'],
        request.form['authors'],
        request.form.get('abstract', ''),
        request.form.get('pages', ''),
        filename,
    ))
    db.commit()
    flash('Статья добавлена', 'ok')
    return redirect(url_for('admin'))


@app.route('/admin/article/delete/<int:article_id>', methods=['POST'])
@login_required
def delete_article(article_id):
    db  = get_db()
    row = db.execute("SELECT filename FROM articles WHERE id=?", (article_id,)).fetchone()
    if row and row['filename']:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, row['filename']))
        except FileNotFoundError:
            pass
    db.execute("DELETE FROM articles WHERE id=?", (article_id,))
    db.commit()
    flash('Статья удалена', 'ok')
    return redirect(url_for('admin'))


# ── MAIN ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
