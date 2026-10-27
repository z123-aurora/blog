# -*- coding: utf-8 -*-
"""前台路由测试：首页、文章详情、分类、标签、搜索、归档、404

所有请求都通过 Flask test_client 打到「临时数据库」上，
真实 database.db 不参与，可任意顺序、任意次数运行。
"""
import sqlite3

import pytest

from conftest import response_text
from init_db import SAMPLE_ARTICLES

# 示例文章按 SAMPLE_ARTICLES 顺序插入，最后一篇即首页最新文章。
# 标题从数据源动态获取，示例数据调整时测试无需改断言。
LATEST_ARTICLE_TITLE = SAMPLE_ARTICLES[-1]["title"]


class TestIndex:
    """/ 首页：文章列表 + 分页 + 侧栏。"""

    @pytest.mark.smoke
    def test_index_ok_and_shows_article(self, client):
        """意图：首页正常返回 200，文章列表渲染出 5 张卡片（满页），
        且最新的 id=6 文章标题在列表中。"""
        resp = client.get("/")
        assert resp.status_code == 200
        body = response_text(resp)
        assert body.count('class="article-card"') == 5
        assert LATEST_ARTICLE_TITLE in body

    def test_sidebar_injects_categories(self, client):
        """意图：context_processor 注入的分类侧栏应渲染在首页。"""
        resp = client.get("/")
        assert "工具与效率" in response_text(resp)

    @pytest.mark.parametrize("page", [1, 2, 999])
    def test_pagination_pages_all_ok(self, client, page):
        """意图：第 1 页、第 2 页、越界页码（夹回末页）都应返回 200。"""
        resp = client.get("/", query_string={"page": page})
        assert resp.status_code == 200

    def test_first_page_contains_latest_article(self, client):
        """意图：按 id 倒序时第 1 页应展示数据中最新插入的那篇文章。"""
        resp = client.get("/")
        assert LATEST_ARTICLE_TITLE in response_text(resp)

    def test_second_page_contains_oldest_article(self, client):
        """意图：第 2 页应只放最旧的 id=1 文章（1 张卡片）。
        用卡片计数而非全文匹配，避免被侧栏「最新文章」链接干扰。"""
        resp = client.get("/", query_string={"page": 2})
        body = response_text(resp)
        assert body.count('class="article-card"') == 1
        assert 'href="/article/1"' in body


class TestArticleDetail:
    """/article/<id> 文章详情：Markdown 渲染、阅读计数、上下篇。"""

    @pytest.mark.smoke
    def test_detail_ok(self, client):
        """意图：存在的文章返回 200，标题与 Markdown 渲染后的正文都在页面上。"""
        resp = client.get("/article/1")
        assert resp.status_code == 200
        body = response_text(resp)
        assert "Flask 入门" in body
        assert "为什么选择 Flask" in body  # 正文里的 ## 标题已渲染为 HTML

    def test_detail_404_for_missing(self, client):
        """意图：访问不存在的文章 id 必须触发 abort(404)。"""
        resp = client.get("/article/99999")
        assert resp.status_code == 404

    def test_views_increment_on_visit(self, client, test_db):
        """意图：每访问一次详情页阅读数 +1；访问两次后库里应为 2。"""
        client.get("/article/1")
        client.get("/article/1")
        conn = sqlite3.connect(test_db)
        try:
            views = conn.execute(
                "SELECT views FROM articles WHERE id = 1"
            ).fetchone()[0]
        finally:
            conn.close()
        assert views == 2

    def test_prev_next_navigation(self, client):
        """意图：id=1 是最旧文章（无上篇），页面应出现指向 id=2 的「下一篇」。"""
        resp = client.get("/article/1")
        assert "Markdown 写作指南" in response_text(resp)

    def test_related_articles_by_shared_tag(self, client):
        """意图：文章 1 与最新一篇共享 Flask 标签，相关文章区应推荐它。"""
        resp = client.get("/article/1")
        assert LATEST_ARTICLE_TITLE in response_text(resp)


class TestCategory:
    """/category/<id> 分类页。"""

    def test_category_page_ok(self, client):
        """意图：Python 分类（id=1）下有 2 篇文章，页面标题与计数正确。"""
        resp = client.get("/category/1")
        assert resp.status_code == 200
        assert "Python" in response_text(resp)
        assert "共 2 篇" in response_text(resp)

    def test_category_only_shows_its_articles(self, client):
        """意图：分类页只能出现该分类的文章，不能混入其他分类的标题。"""
        resp = client.get("/category/3")  # 数据库分类，仅 1 篇
        body = response_text(resp)
        assert "SQLite 数据库" in body
        assert "Docker 部署" not in body

    def test_category_404(self, client):
        """意图：不存在的分类 id 应返回 404。"""
        assert client.get("/category/99999").status_code == 404


class TestTag:
    """/tag/<id> 标签页。"""

    def test_tag_page_ok(self, client):
        """意图：id=1 的 Flask 标签关联 2 篇文章，页面正常返回。"""
        resp = client.get("/tag/1")
        assert resp.status_code == 200
        body = response_text(resp)
        assert "Flask" in body
        assert "共 2 篇" in body

    def test_tag_404(self, client):
        """意图：不存在的标签 id 应返回 404。"""
        assert client.get("/tag/99999").status_code == 404


class TestSearch:
    """/search 关键词搜索：标题/摘要/正文 LIKE 匹配。"""

    @pytest.mark.parametrize(
        "keyword, expect_min, expect_text",
        [
            pytest.param("Flask", 2, "Flask 入门", id="命中多篇"),
            pytest.param("装饰器", 1, "装饰器详解", id="命中单篇"),
            pytest.param("不存在的词xyz", 0, "没有找到", id="无结果"),
        ],
    )
    def test_search_results(self, client, keyword, expect_min, expect_text):
        """意图：参数化覆盖「多命中/单命中/零命中」三种搜索结果形态。"""
        resp = client.get("/search", query_string={"q": keyword})
        assert resp.status_code == 200
        assert expect_text in response_text(resp)
        assert f"找到" in response_text(resp)  # 结果计数文案始终渲染

    def test_search_empty_keyword(self, client):
        """意图：关键词为空时不执行查询，页面提示输入关键词。"""
        resp = client.get("/search", query_string={"q": ""})
        assert resp.status_code == 200
        assert "请输入关键词" in response_text(resp)

    def test_search_keyword_is_stripped(self, client):
        """意图：关键词两侧空格应被 strip，仍能正确命中。"""
        resp = client.get("/search", query_string={"q": "  Flask  "})
        assert resp.status_code == 200
        assert "Flask 入门" in response_text(resp)

    def test_search_percent_is_literal(self, client):
        """意图：% 按字面匹配，不应被当成通配符返回全部文章。"""
        resp = client.get("/search", query_string={"q": "%"})
        assert resp.status_code == 200
        assert "没有找到" in response_text(resp)


class TestArchivesAndErrors:
    """归档页与全局 404。"""

    def test_archives_ok(self, client):
        """意图：归档页 200，按年份分组，示例文章的年份（2026）出现。"""
        resp = client.get("/archives")
        assert resp.status_code == 200
        assert "2026" in response_text(resp)
        assert "Flask 入门" in response_text(resp)

    def test_unknown_route_404(self, client):
        """意图：未注册的路径应走自定义 404 页面，状态码为 404。"""
        resp = client.get("/this/does/not/exist")
        assert resp.status_code == 404
        assert "404" in response_text(resp)
