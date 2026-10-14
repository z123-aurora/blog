# -*- coding: utf-8 -*-
"""个人技术博客 - Flask 主应用"""
import os
from functools import wraps

import markdown
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import init_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-in-production-9f2e1c"
app.config["ADMIN_USERNAME"] = "admin"
app.config["ADMIN_PASSWORD"] = "admin123"

POSTS_PER_PAGE = 5


# ---------- 数据库连接 ----------
def get_db():
    """获取当前请求绑定的数据库连接（Flask g 管理生命周期）。

    连接的实际创建统一委托给 init_db.create_connection，
    保证应用代码与初始化脚本使用完全一致的连接配置。
    """
    if "db" not in g:
        g.db = init_db.create_connection(DB_PATH)
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------- Markdown 渲染 ----------
@app.template_filter("markdown")
def render_markdown(text):
    return markdown.markdown(
        text or "",
        extensions=["fenced_code", "tables", "nl2br"],
    )


# ---------- 通用查询 ----------
def query_all(sql, query_params=()):
    return get_db().execute(sql, query_params).fetchall()


def query_one(sql, query_params=()):
    return get_db().execute(sql, query_params).fetchone()


def get_categories():
    return query_all(
        """SELECT c.*, COUNT(a.id) AS article_count
           FROM categories c
           LEFT JOIN articles a ON a.category_id = c.id
           GROUP BY c.id ORDER BY c.name"""
    )


def get_popular_tags():
    return query_all(
        """SELECT t.*, COUNT(at.article_id) AS article_count
           FROM tags t
           JOIN article_tags at ON at.tag_id = t.id
           GROUP BY t.id ORDER BY article_count DESC, t.name LIMIT 12"""
    )


def get_article_tags(article_id):
    return query_all(
        """SELECT t.* FROM tags t
           JOIN article_tags at ON at.tag_id = t.id
           WHERE at.article_id = ?""",
        (article_id,),
    )


def get_article_category(article_id):
    return query_one(
        """SELECT c.* FROM categories c
           JOIN articles a ON a.category_id = c.id
           WHERE a.id = ?""",
        (article_id,),
    )


@app.context_processor
def inject_sidebar_data():
    """向所有模板注入侧栏所需的分类与热门标签数据。"""
    return {"categories": get_categories(), "popular_tags": get_popular_tags()}


# ---------- 分页：计数与取数职责拆分 ----------
def get_total_count(count_sql, query_params=()):
    """执行 COUNT 查询，返回符合条件的记录总数。"""
    return query_one(count_sql, query_params)[0]


def fetch_paginated_rows(base_sql, query_params, page, total, per_page=POSTS_PER_PAGE):
    """按页码取一页数据，并把越界页码夹取到 [1, 总页数]。

    返回 (items, page, pages)：总数 total 由调用方通过
    get_total_count() 取得，计数 SQL 与取数 SQL 各自独立。
    """
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, page), pages)
    sql = base_sql + " LIMIT ? OFFSET ?"
    items = query_all(
        sql, tuple(query_params) + (per_page, (page - 1) * per_page)
    )
    return items, page, pages


# ---------- 登录保护 ----------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


# ================= 前台路由 =================
HOME_LIST_SQL = """SELECT a.*, c.name AS category_name FROM articles a
    LEFT JOIN categories c ON c.id = a.category_id
    ORDER BY a.created_at DESC, a.id DESC"""
HOME_COUNT_SQL = "SELECT COUNT(*) FROM articles"
LATEST_ARTICLES_SQL = (
    "SELECT id, title FROM articles ORDER BY created_at DESC, id DESC LIMIT 5"
)


def _render_home(template_name):
    """首页两个皮肤（版本一/版本二）共用的数据准备逻辑，仅模板不同。"""
    page = request.args.get("page", 1, type=int)
    total = get_total_count(HOME_COUNT_SQL)
    items, page, pages = fetch_paginated_rows(HOME_LIST_SQL, (), page, total)
    latest = query_all(LATEST_ARTICLES_SQL)
    return render_template(
        template_name, articles=items, page=page, pages=pages, total=total, latest=latest
    )


@app.route("/")
def index():
    """版本一首页（浅色蓝紫风）。"""
    return _render_home("index.html")


@app.route("/v2")
def index_dark():
    """版本二首页（深色科技风）：数据与版本一完全一致，仅模板/样式不同。"""
    return _render_home("index_v2.html")


@app.route("/article/<int:article_id>")
def article_detail(article_id):
    art = query_one(
        """SELECT a.*, c.name AS category_name FROM articles a
           LEFT JOIN categories c ON c.id = a.category_id
           WHERE a.id = ?""",
        (article_id,),
    )
    if art is None:
        abort(404)
    get_db().execute("UPDATE articles SET views = views + 1 WHERE id = ?", (article_id,))
    get_db().commit()
    art = dict(art)
    art["views"] += 1
    prev_art = query_one(
        "SELECT id, title FROM articles WHERE id < ? ORDER BY id DESC LIMIT 1",
        (article_id,),
    )
    next_art = query_one(
        "SELECT id, title FROM articles WHERE id > ? ORDER BY id ASC LIMIT 1",
        (article_id,),
    )
    related = query_all(
        """SELECT DISTINCT a2.id, a2.title FROM articles a2
           JOIN article_tags at2 ON at2.article_id = a2.id
           WHERE at2.tag_id IN (SELECT tag_id FROM article_tags WHERE article_id = ?)
             AND a2.id != ?
           LIMIT 5""",
        (article_id, article_id),
    )
    return render_template(
        "article.html",
        article=art,
        tags=get_article_tags(article_id),
        prev_art=prev_art,
        next_art=next_art,
        related=related,
    )


@app.route("/category/<int:category_id>")
def category(category_id):
    cat = query_one("SELECT * FROM categories WHERE id = ?", (category_id,))
    if cat is None:
        abort(404)
    page = request.args.get("page", 1, type=int)
    count_sql = "SELECT COUNT(*) FROM articles WHERE category_id = ?"
    list_sql = """SELECT a.*, c.name AS category_name FROM articles a
        LEFT JOIN categories c ON c.id = a.category_id
        WHERE a.category_id = ?
        ORDER BY a.created_at DESC, a.id DESC"""
    total = get_total_count(count_sql, (category_id,))
    items, page, pages = fetch_paginated_rows(list_sql, (category_id,), page, total)
    return render_template(
        "category.html", category=cat, articles=items, page=page, pages=pages, total=total
    )


@app.route("/tag/<int:tag_id>")
def tag(tag_id):
    t = query_one("SELECT * FROM tags WHERE id = ?", (tag_id,))
    if t is None:
        abort(404)
    page = request.args.get("page", 1, type=int)
    list_sql = """SELECT DISTINCT a.*, c.name AS category_name FROM articles a
        JOIN article_tags at ON at.article_id = a.id
        LEFT JOIN categories c ON c.id = a.category_id
        WHERE at.tag_id = ?
        ORDER BY a.created_at DESC, a.id DESC"""
    count_sql = """SELECT COUNT(DISTINCT a.id) FROM articles a
        JOIN article_tags at ON at.article_id = a.id
        WHERE at.tag_id = ?"""
    total = get_total_count(count_sql, (tag_id,))
    items, page, pages = fetch_paginated_rows(list_sql, (tag_id,), page, total)
    return render_template(
        "tag.html", tag=t, articles=items, page=page, pages=pages, total=total
    )


@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    articles, page, pages, total = [], 1, 1, 0
    if keyword:
        like = f"%{keyword}%"
        query_params = (like, like, like)
        list_sql = """SELECT a.*, c.name AS category_name FROM articles a
            LEFT JOIN categories c ON c.id = a.category_id
            WHERE a.title LIKE ? OR a.summary LIKE ? OR a.content LIKE ?
            ORDER BY a.created_at DESC, a.id DESC"""
        count_sql = """SELECT COUNT(*) FROM articles
            WHERE title LIKE ? OR summary LIKE ? OR content LIKE ?"""
        total = get_total_count(count_sql, query_params)
        items, page, pages = fetch_paginated_rows(list_sql, query_params, page, total)
        articles = items
    return render_template(
        "search.html", keyword=keyword, articles=articles, page=page,
        pages=pages, total=total,
    )


@app.route("/archives")
def archives():
    rows = query_all(
        """SELECT id, title, created_at FROM articles
           ORDER BY created_at DESC, id DESC"""
    )
    by_year = {}
    for row in rows:
        year = row["created_at"][:4]
        by_year.setdefault(year, []).append(row)
    return render_template("archives.html", archives=sorted(by_year.items(), reverse=True))


# ================= 后台路由 =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if (
            username == app.config["ADMIN_USERNAME"]
            and password == app.config["ADMIN_PASSWORD"]
        ):
            session["logged_in"] = True
            flash("登录成功", "success")
            return redirect(request.args.get("next") or url_for("admin"))
        flash("用户名或密码错误", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出登录", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin():
    stats = {
        "articles": query_one("SELECT COUNT(*) c FROM articles")[0],
        "categories": query_one("SELECT COUNT(*) c FROM categories")[0],
        "tags": query_one("SELECT COUNT(*) c FROM tags")[0],
        "views": query_one("SELECT COALESCE(SUM(views), 0) c FROM articles")[0],
    }
    articles = query_all(
        """SELECT a.*, c.name AS category_name FROM articles a
           LEFT JOIN categories c ON c.id = a.category_id
           ORDER BY a.created_at DESC, a.id DESC"""
    )
    return render_template("admin/dashboard.html", stats=stats, articles=articles)


@app.route("/admin/article/new", methods=["GET", "POST"])
@login_required
def admin_article_new():
    if request.method == "POST":
        _save_article(None)
        flash("文章发布成功", "success")
        return redirect(url_for("admin"))
    return render_template("admin/article_form.html", article=None, tags="")


@app.route("/admin/article/edit/<int:article_id>", methods=["GET", "POST"])
@login_required
def admin_article_edit(article_id):
    art = query_one("SELECT * FROM articles WHERE id = ?", (article_id,))
    if art is None:
        abort(404)
    if request.method == "POST":
        _save_article(article_id)
        flash("文章更新成功", "success")
        return redirect(url_for("admin"))
    tags = ", ".join(t["name"] for t in get_article_tags(article_id))
    return render_template("admin/article_form.html", article=art, tags=tags)


def _save_article(article_id):
    title = request.form.get("title", "").strip()
    summary = request.form.get("summary", "").strip()
    content = request.form.get("content", "").strip()
    category_id = request.form.get("category_id", type=int)
    tag_names = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    if not title or not content or not category_id:
        flash("标题、内容和分类不能为空", "error")
        return
    db = get_db()
    if article_id is None:
        cur = db.execute(
            "INSERT INTO articles (title, summary, content, category_id) VALUES (?, ?, ?, ?)",
            (title, summary, content, category_id),
        )
        article_id = cur.lastrowid
    else:
        db.execute(
            """UPDATE articles SET title = ?, summary = ?, content = ?,
               category_id = ?, updated_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (title, summary, content, category_id, article_id),
        )
        db.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
    for name in tag_names:
        db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = db.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()["id"]
        db.execute(
            "INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)",
            (article_id, tag_id),
        )
    db.commit()


@app.route("/admin/article/delete/<int:article_id>", methods=["POST"])
@login_required
def admin_article_delete(article_id):
    db = get_db()
    db.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
    db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    db.commit()
    flash("文章已删除", "success")
    return redirect(url_for("admin"))


@app.route("/admin/category/new", methods=["POST"])
@login_required
def admin_category_new():
    name = request.form.get("name", "").strip()
    if name:
        db = get_db()
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
        db.commit()
        flash("分类已创建", "success")
    return redirect(url_for("admin"))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db.init_db()  # 首次运行自动建库
    app.run(debug=True, host="127.0.0.1", port=5000)
