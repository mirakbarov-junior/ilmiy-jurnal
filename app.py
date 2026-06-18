import os
import sqlite3
from functools import wraps
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_from_directory, abort, g)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production-please')

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATABASE      = os.path.join(BASE_DIR, 'journal.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXT   = {'pdf'}
ALLOWED_IMG   = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USER     = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# ── TRANSLATIONS ─────────────────────────────────────────────────────────────
TRANSLATIONS = {
    'uz': {
        'lang_name': "O'zbek",
        'current': 'Joriy son',
        'archives': 'Arxiv',
        'about': 'Haqida',
        'login': 'Kirish',
        'logout': 'Chiqish',
        'admin': 'Admin',
        'articles': 'Maqolalar',
        'published': 'Nashr etilgan',
        'for_readers': 'Kitobxonlar uchun',
        'for_authors': 'Mualliflar uchun',
        'for_librarians': 'Kutubxonachilar uchun',
        'current_issue': 'Joriy son',
        'information': 'Ma\'lumot',
        'no_articles': 'Bu sonda hali maqola yo\'q.',
        'no_issues': 'Hali son yo\'q.',
        'download_pdf': 'PDF yuklab olish',
        'no_pdf': 'PDF yuklanmagan',
        'back_to_issue': '← Songa qaytish',
        'abstract': 'Annotatsiya',
        'no_abstract': 'Annotatsiya qo\'shilmagan.',
        'pages': 'bet',
        'admin_panel': 'Admin paneli',
        'add_issue': 'Yangi son qo\'shish',
        'add_article': 'Maqola qo\'shish',
        'issue_title': 'Son nomi',
        'volume': 'Tom',
        'number': 'Son',
        'year': 'Yil',
        'pub_date': 'Nashr sanasi',
        'create_issue': 'Son yaratish',
        'select_issue': 'Son',
        'article_title': 'Maqola nomi',
        'authors': 'Muallif(lar)',
        'annotation': 'Annotatsiya',
        'pdf_file': 'PDF fayl',
        'cover_image': 'Muqova rasmi (JPG/PNG)',
        'add_article_btn': 'Maqola qo\'shish',
        'issues_table': 'Sonlar',
        'articles_table': 'Barcha maqolalar',
        'delete': 'O\'chirish',
        'delete_issue_confirm': 'Son va uning barcha maqolalarini o\'chirasizmi?',
        'delete_article_confirm': 'Maqolani o\'chirasizmi?',
        'id': 'ID',
        'actions': 'Amallar',
        'no_issues_table': 'Sonlar yo\'q',
        'no_articles_table': 'Maqolalar yo\'q',
        'issue_added': 'Son qo\'shildi',
        'issue_deleted': 'Son o\'chirildi',
        'article_added': 'Maqola qo\'shildi',
        'article_deleted': 'Maqola o\'chirildi',
        'wrong_login': 'Login yoki parol noto\'g\'ri',
        'login_title': 'Admin kirish',
        'username': 'Login',
        'password': 'Parol',
        'login_btn': 'Kirish',
        'footer': '© 2025 Yangi O\'zbekiston Ilmiy Jurnali',
        'archives_sidebar': 'Arxiv',
        'vol': 'Tom',
        'no': '№',
    },
    'ru': {
        'lang_name': 'Русский',
        'current': 'Текущий',
        'archives': 'Архив',
        'about': 'О журнале',
        'login': 'Войти',
        'logout': 'Выйти',
        'admin': 'Админ',
        'articles': 'Статьи',
        'published': 'Опубликовано',
        'for_readers': 'Для читателей',
        'for_authors': 'Для авторов',
        'for_librarians': 'Для библиотекарей',
        'current_issue': 'Текущий выпуск',
        'information': 'Информация',
        'no_articles': 'В этом выпуске пока нет статей.',
        'no_issues': 'Выпусков пока нет.',
        'download_pdf': 'Скачать PDF',
        'no_pdf': 'PDF не загружен',
        'back_to_issue': '← Назад к выпуску',
        'abstract': 'Аннотация',
        'no_abstract': 'Аннотация не добавлена.',
        'pages': 'стр.',
        'admin_panel': 'Панель администратора',
        'add_issue': 'Добавить новый выпуск',
        'add_article': 'Добавить статью',
        'issue_title': 'Название выпуска',
        'volume': 'Том',
        'number': 'Номер',
        'year': 'Год',
        'pub_date': 'Дата публикации',
        'create_issue': 'Создать выпуск',
        'select_issue': 'Выпуск',
        'article_title': 'Название статьи',
        'authors': 'Автор(ы)',
        'annotation': 'Аннотация',
        'pdf_file': 'PDF-файл',
        'cover_image': 'Обложка (JPG/PNG)',
        'add_article_btn': 'Добавить статью',
        'issues_table': 'Выпуски',
        'articles_table': 'Все статьи',
        'delete': 'Удалить',
        'delete_issue_confirm': 'Удалить выпуск и все его статьи?',
        'delete_article_confirm': 'Удалить статью?',
        'id': 'ID',
        'actions': 'Действия',
        'no_issues_table': 'Выпусков нет',
        'no_articles_table': 'Статей нет',
        'issue_added': 'Выпуск добавлен',
        'issue_deleted': 'Выпуск удалён',
        'article_added': 'Статья добавлена',
        'article_deleted': 'Статья удалена',
        'wrong_login': 'Неверный логин или пароль',
        'login_title': 'Вход для администратора',
        'username': 'Логин',
        'password': 'Пароль',
        'login_btn': 'Войти',
        'footer': '© 2025 Yangi O\'zbekiston Ilmiy Jurnali',
        'archives_sidebar': 'Архив',
        'vol': 'Том',
        'no': '№',
    },
    'en': {
        'lang_name': 'English',
        'current': 'Current',
        'archives': 'Archives',
        'about': 'About',
        'login': 'Login',
        'logout': 'Logout',
        'admin': 'Admin',
        'articles': 'Articles',
        'published': 'Published',
        'for_readers': 'For Readers',
        'for_authors': 'For Authors',
        'for_librarians': 'For Librarians',
        'current_issue': 'Current Issue',
        'information': 'Information',
        'no_articles': 'No articles in this issue yet.',
        'no_issues': 'No issues yet.',
        'download_pdf': 'Download PDF',
        'no_pdf': 'PDF not uploaded',
        'back_to_issue': '← Back to issue',
        'abstract': 'Abstract',
        'no_abstract': 'No abstract provided.',
        'pages': 'pp.',
        'admin_panel': 'Admin Panel',
        'add_issue': 'Add New Issue',
        'add_article': 'Add Article',
        'issue_title': 'Issue Title',
        'volume': 'Volume',
        'number': 'Number',
        'year': 'Year',
        'pub_date': 'Publication Date',
        'create_issue': 'Create Issue',
        'select_issue': 'Issue',
        'article_title': 'Article Title',
        'authors': 'Author(s)',
        'annotation': 'Abstract',
        'pdf_file': 'PDF File',
        'cover_image': 'Cover Image (JPG/PNG)',
        'add_article_btn': 'Add Article',
        'issues_table': 'Issues',
        'articles_table': 'All Articles',
        'delete': 'Delete',
        'delete_issue_confirm': 'Delete issue and all its articles?',
        'delete_article_confirm': 'Delete article?',
        'id': 'ID',
        'actions': 'Actions',
        'no_issues_table': 'No issues',
        'no_articles_table': 'No articles',
        'issue_added': 'Issue added',
        'issue_deleted': 'Issue deleted',
        'article_added': 'Article added',
        'article_deleted': 'Article deleted',
        'wrong_login': 'Wrong username or password',
        'login_title': 'Admin Login',
        'username': 'Username',
        'password': 'Password',
        'login_btn': 'Login',
        'footer': '© 2025 Yangi O\'zbekiston Ilmiy Jurnali',
        'archives_sidebar': 'Archives',
        'vol': 'Vol.',
        'no': 'No.',
    },
}

def get_lang():
    return session.get('lang', 'uz')

def t(key):
    lang = get_lang()
    return TRANSLATIONS.get(lang, TRANSLATIONS['uz']).get(key, key)

app.jinja_env.globals['t'] = t
app.jinja_env.globals['get_lang'] = get_lang

# ── DB ────────────────────────────────────────────────────────────────────────
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
                cover      TEXT,
                created    TEXT DEFAULT (datetime('now'))
            );
        """)
        # add cover column if missing (migration)
        try:
            db.execute("ALTER TABLE articles ADD COLUMN cover TEXT")
            db.commit()
        except Exception:
            pass

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def allowed_img(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG

# ── AUTH ──────────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── LANGUAGE ──────────────────────────────────────────────────────────────────
@app.route('/lang/<lang>')
def set_lang(lang):
    if lang in ('uz', 'ru', 'en'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# ── PUBLIC ────────────────────────────────────────────────────────────────────
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

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_USER and
                request.form['password'] == ADMIN_PASSWORD):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash(t('wrong_login'), 'error')
    return render_template('login.html')

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── ADMIN ─────────────────────────────────────────────────────────────────────
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

@app.route('/admin/issue/add', methods=['POST'])
@login_required
def add_issue():
    db = get_db()
    db.execute("""
        INSERT INTO issues (title, volume, number, year, published)
        VALUES (?,?,?,?,?)
    """, (
        request.form['title'], request.form['volume'],
        request.form['number'], request.form['year'],
        request.form['published'],
    ))
    db.commit()
    flash(t('issue_added'), 'ok')
    return redirect(url_for('admin'))

@app.route('/admin/issue/delete/<int:issue_id>', methods=['POST'])
@login_required
def delete_issue(issue_id):
    db = get_db()
    rows = db.execute("SELECT filename, cover FROM articles WHERE issue_id=?", (issue_id,)).fetchall()
    for r in rows:
        for f in [r['filename'], r['cover']]:
            if f:
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, f))
                except FileNotFoundError:
                    pass
    db.execute("DELETE FROM issues WHERE id=?", (issue_id,))
    db.commit()
    flash(t('issue_deleted'), 'ok')
    return redirect(url_for('admin'))

@app.route('/admin/article/add', methods=['POST'])
@login_required
def add_article():
    db       = get_db()
    pdf_file = request.files.get('pdf_file')
    img_file = request.files.get('cover_image')
    filename = None
    cover    = None

    if pdf_file and pdf_file.filename and allowed_file(pdf_file.filename):
        safe   = secure_filename(pdf_file.filename)
        unique = f"{int(datetime.now().timestamp())}_{safe}"
        pdf_file.save(os.path.join(UPLOAD_FOLDER, unique))
        filename = unique

    if img_file and img_file.filename and allowed_img(img_file.filename):
        safe   = secure_filename(img_file.filename)
        unique = f"cover_{int(datetime.now().timestamp())}_{safe}"
        img_file.save(os.path.join(UPLOAD_FOLDER, unique))
        cover = unique

    db.execute("""
        INSERT INTO articles (issue_id, title, authors, abstract, pages, filename, cover)
        VALUES (?,?,?,?,?,?,?)
    """, (
        request.form['issue_id'], request.form['title'],
        request.form['authors'],  request.form.get('abstract', ''),
        request.form.get('pages', ''), filename, cover,
    ))
    db.commit()
    flash(t('article_added'), 'ok')
    return redirect(url_for('admin'))

@app.route('/admin/article/delete/<int:article_id>', methods=['POST'])
@login_required
def delete_article(article_id):
    db  = get_db()
    row = db.execute("SELECT filename, cover FROM articles WHERE id=?", (article_id,)).fetchone()
    if row:
        for f in [row['filename'], row['cover']]:
            if f:
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, f))
                except FileNotFoundError:
                    pass
    db.execute("DELETE FROM articles WHERE id=?", (article_id,))
    db.commit()
    flash(t('article_deleted'), 'ok')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
