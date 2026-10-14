# -*- coding: utf-8 -*-
"""核心函数单元测试：Markdown 过滤器、分页、数据查询、数据库初始化

这些用例直接调用 app.py / init_db.py 中的纯逻辑函数，
运行快、失败定位准，对应速查表「优先测试纯逻辑」的建议。
"""
import sqlite3

import pytest

import app as app_module
import init_db


# ================= Markdown 过滤器 =================
class TestRenderMarkdown:
    """render_markdown：把 Markdown 文本转成 HTML（模板过滤器）。"""

    def test_none_input_returns_empty(self):
        """意图：正文为 None 时（text or '' 兜底）不应抛异常，返回空串。"""
        assert app_module.render_markdown(None) == ""

    def test_plain_text_wrapped_in_paragraph(self):
        """意图：普通文本应被 <p> 标签包裹，验证最基础的 Markdown 渲染。"""
        html = app_module.render_markdown("你好世界")
        assert "<p>" in html and "你好世界" in html

    def test_fenced_code_extension(self):
        """意图：围栏代码块（fenced_code 扩展）应渲染成 <pre><code>，
        并带上 language-python 语言标识类。"""
        text = "```python\nprint('hi')\n```"
        html = app_module.render_markdown(text)
        assert "<pre>" in html
        assert 'class="language-python"' in html
        assert "print(" in html

    def test_table_extension(self):
        """意图：tables 扩展应把管道表格渲染为 <table>，而不是原样文本。"""
        text = "| a | b |\n| - | - |\n| 1 | 2 |"
        html = app_module.render_markdown(text)
        assert "<table>" in html and "<th>a</th>" in html


# ================= 分页函数（get_total_count + fetch_paginated_rows） =================
class TestPaginate:
    """分页职责拆分为：先取总数，再按页取行并夹取越界页码。

    示例库共 6 篇文章、POSTS_PER_PAGE=5，因此总页数 pages=2：
    第 1 页 5 条，第 2 页 1 条。
    """

    BASE_SQL = "SELECT id, title FROM articles ORDER BY id DESC"
    COUNT_SQL = "SELECT COUNT(*) FROM articles"

    def test_total_and_pages(self, app_ctx):
        """意图：6 篇文章、每页 5 篇 → total=6、pages=2，验证总页数计算。"""
        total = app_module.get_total_count(self.COUNT_SQL)
        _, page, pages = app_module.fetch_paginated_rows(
            self.BASE_SQL, (), 1, total
        )
        assert total == 6
        assert pages == 2
        assert page == 1

    def test_first_page_size(self, app_ctx):
        """意图：第 1 页应返回满页的 5 条记录。"""
        total = app_module.get_total_count(self.COUNT_SQL)
        items, _, _ = app_module.fetch_paginated_rows(
            self.BASE_SQL, (), 1, total
        )
        assert len(items) == 5

    def test_last_page_size(self, app_ctx):
        """意图：最后一页只放剩余的 1 条记录（6 - 5 = 1）。"""
        total = app_module.get_total_count(self.COUNT_SQL)
        items, _, _ = app_module.fetch_paginated_rows(
            self.BASE_SQL, (), 2, total
        )
        assert len(items) == 1

    @pytest.mark.parametrize("bad_page", [0, -1, -99])
    def test_page_below_range_clamped_to_one(self, app_ctx, bad_page):
        """意图：页码 <= 0 时应被 max(1, page) 夹回第 1 页，而不是报错。"""
        total = app_module.get_total_count(self.COUNT_SQL)
        items, page, _ = app_module.fetch_paginated_rows(
            self.BASE_SQL, (), bad_page, total
        )
        assert page == 1
        assert len(items) == 5

    def test_page_above_range_clamped_to_last(self, app_ctx):
        """意图：页码远超总页数（如 999）时应夹到最后一页，返回最后 1 条。"""
        total = app_module.get_total_count(self.COUNT_SQL)
        items, page, pages = app_module.fetch_paginated_rows(
            self.BASE_SQL, (), 999, total
        )
        assert page == pages == 2
        assert len(items) == 1


# ================= 数据查询函数 =================
class TestQueryHelpers:
    """get_categories / get_popular_tags / get_article_tags 等。"""

    def test_get_categories_counts(self, app_ctx):
        """意图：应返回 4 个分类，且 Python 分类下挂 2 篇示例文章。"""
        cats = app_module.get_categories()
        assert len(cats) == 4
        python_cat = next(c for c in cats if c["name"] == "Python")
        assert python_cat["article_count"] == 2

    def test_get_popular_tags_order(self, app_ctx):
        """意图：Flask 标签关联了 2 篇文章（入门篇 + Docker 篇），
        按关联数降序应排在热门标签首位。"""
        tags = app_module.get_popular_tags()
        assert tags[0]["name"] == "Flask"
        assert tags[0]["article_count"] == 2

    def test_get_article_tags(self, app_ctx):
        """意图：文章 1 的标签是「Flask、入门教程」，应精确返回 2 个。"""
        tags = app_module.get_article_tags(1)
        names = {t["name"] for t in tags}
        assert names == {"Flask", "入门教程"}

    def test_get_article_tags_empty_for_unknown(self, app_ctx):
        """意图：不存在的文章没有标签，应返回空结果集而非报错。"""
        assert app_module.get_article_tags(99999) == []

    def test_get_article_category(self, app_ctx):
        """意图：文章 1 属于 Python 分类，验证 JOIN 查询正确。"""
        cat = app_module.get_article_category(1)
        assert cat["name"] == "Python"

    def test_query_one_returns_none_when_no_row(self, app_ctx):
        """意图：fetchone 查不到数据时返回 None，路由层靠它判断 404。"""
        row = app_module.query_one(
            "SELECT * FROM articles WHERE id = ?", (99999,)
        )
        assert row is None


# ================= init_db 数据库初始化 =================
class TestInitDb:
    """init_db：建表 + 首次灌入示例数据；create_connection：连接配置。"""

    def test_tables_and_sample_data_created(self, test_db):
        """意图：全新初始化后 4 张表齐全，且写入 6 篇文章、4 个分类。"""
        conn = sqlite3.connect(test_db)
        try:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert {
                "categories", "articles", "tags", "article_tags"
            }.issubset(tables)
            assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 6
            assert conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 4
        finally:
            conn.close()

    def test_init_is_idempotent(self, test_db, capsys):
        """意图：重复执行 init_db 不得重复灌数据（跳过分支），
        文章数仍为 6，并打印跳过提示。"""
        init_db.init_db()
        conn = sqlite3.connect(test_db)
        try:
            assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 6
        finally:
            conn.close()
        assert "跳过" in capsys.readouterr().out

    def test_create_connection_row_factory(self, test_db):
        """意图：create_connection 返回的连接必须配置 sqlite3.Row，
        应用代码才能用 row['列名'] 方式取值。"""
        conn = init_db.create_connection()
        try:
            assert conn.row_factory is sqlite3.Row
        finally:
            conn.close()

    def test_tag_links_created(self, test_db):
        """意图：示例数据的文章-标签关联表应有记录，
        验证初始化时多对多关联写入成功。"""
        conn = sqlite3.connect(test_db)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM article_tags"
            ).fetchone()[0]
            assert count > 0
        finally:
            conn.close()
