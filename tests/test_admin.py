# -*- coding: utf-8 -*-
"""后台测试：登录保护、文章增删改、分类管理

注意（以 app.py 真实行为为准）：
    _save_article() 校验失败时只 flash + return，路由随后仍会
    redirect 到 /admin。因此「缺标题」类用例的状态码是 302，
    需要 follow_redirects=True 才能看到错误提示。
"""
import re
import sqlite3

import pytest

from conftest import response_text


# 仅允许测试辅助函数统计以下白名单表，杜绝任意表名拼接
_COUNT_TABLE_WHITELIST = {"articles", "categories", "tags", "article_tags"}


def _count(db_path, table, where_clause="", params=()):
    """直连临时库做行数统计的局部辅助（仅本文件使用）。

    安全约定：
        - table 必须在 _COUNT_TABLE_WHITELIST 白名单内；
        - where_clause 只能由测试代码硬编码提供，且条件值必须以 ?
          占位符书写、实参通过 params 传入（参数化），绝不拼接外部输入。
    """
    if table not in _COUNT_TABLE_WHITELIST:
        raise ValueError(f"拒绝统计白名单之外的表: {table}")
    sql = f"SELECT COUNT(*) FROM {table}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


# ================= 登录与访问控制 =================
class TestAuth:
    """登录、退出与 login_required 装饰器。"""

    @pytest.mark.smoke
    def test_admin_requires_login(self, client):
        """意图：未登录访问后台必须被重定向到登录页，并带上 next 回跳地址。"""
        resp = client.get("/admin")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
        assert "next=/admin" in resp.headers["Location"]

    def test_login_page_ok(self, client):
        """意图：GET 登录页正常渲染表单。"""
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "后台登录" in response_text(resp)

    def test_login_wrong_password(self, client):
        """意图：密码错误时不建立会话，留在登录页并显示错误提示。"""
        resp = client.post(
            "/login", data={"username": "admin", "password": "wrong"}
        )
        assert resp.status_code == 200
        assert "用户名或密码错误" in response_text(resp)

    def test_login_wrong_username(self, client):
        """意图：用户名错误同样被拒，防止只校验密码的逻辑漏洞。"""
        resp = client.post(
            "/login", data={"username": "root", "password": "admin123"}
        )
        assert resp.status_code == 200
        assert "用户名或密码错误" in response_text(resp)

    def test_login_success_redirects_admin(self, client):
        """意图：凭证正确时 302 跳转后台，并写入登录会话。"""
        resp = client.post(
            "/login", data={"username": "admin", "password": "admin123"}
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/admin")

    def test_login_respects_next_param(self, client):
        """意图：带 next 参数登录成功后应回跳到原目标页，而非固定后台。"""
        resp = client.post(
            "/login?next=/archives",
            data={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/archives")

    def test_logout_clears_session(self, logged_in_client):
        """意图：退出后会话清空，再访问后台应重新被要求登录。"""
        resp = logged_in_client.get("/logout")
        assert resp.status_code == 302
        again = logged_in_client.get("/admin")
        assert again.status_code == 302
        assert "/login" in again.headers["Location"]


# ================= 后台仪表盘 =================
class TestDashboard:
    """登录后的后台首页与统计数据。"""

    def test_dashboard_ok(self, logged_in_client):
        """意图：登录后可看仪表盘，页面含管理区与示例文章标题。"""
        resp = logged_in_client.get("/admin")
        assert resp.status_code == 200
        body = response_text(resp)
        assert "后台管理" in body
        assert "Flask 入门" in body

    def test_dashboard_stats(self, logged_in_client):
        """意图：统计卡片应正确显示 6 篇文章、4 个分类。"""
        body = response_text(logged_in_client.get("/admin"))
        # 示例库固定 6 篇 / 4 分类，数字直接渲染在统计卡片中
        assert ">6<" in body
        assert ">4<" in body


# ================= 文章新增 =================
class TestCreateArticle:
    """POST /admin/article/new。"""

    @pytest.mark.smoke
    def test_create_article_full(self, logged_in_client):
        """意图：标题/摘要/正文/分类/标签齐全时创建成功。

        全程通过应用接口验证（绕过数据访问层直连）：
        1) POST 发布后 302 跳后台；
        2) 后台仪表盘统计从 6 变为 7；
        3) 前台首页能找到新文章，点进详情页后两个标签均渲染出来。
        """
        resp = logged_in_client.post(
            "/admin/article/new",
            data={
                "title": "pytest 造的测试文章",
                "summary": "测试摘要",
                "content": "# 正文内容",
                "category_id": "1",
                "tags": "pytest, 测试",
            },
        )
        assert resp.status_code == 302

        # 仪表盘统计：文章总数 6 → 7
        dashboard = response_text(logged_in_client.get("/admin"))
        assert ">7<" in dashboard

        # 首页（按 id 倒序）第一张卡片即新文章，取其详情链接
        home = response_text(logged_in_client.get("/"))
        assert "pytest 造的测试文章" in home
        new_id = re.search(r'href="/article/(\d+)"', home).group(1)

        # 详情页验证标题与两个标签关联均已落库并渲染
        detail = response_text(logged_in_client.get(f"/article/{new_id}"))
        assert "pytest 造的测试文章" in detail
        assert "# pytest" in detail
        assert "# 测试" in detail

    def test_created_article_visible_on_site(self, logged_in_client):
        """意图：新建文章应立即出现在前台首页（端到端验证写入链路）。"""
        logged_in_client.post(
            "/admin/article/new",
            data={
                "title": "端到端可见性文章",
                "summary": "",
                "content": "正文",
                "category_id": "1",
                "tags": "",
            },
        )
        resp = logged_in_client.get("/")
        assert "端到端可见性文章" in response_text(resp)

    def test_create_article_empty_title_rejected(
        self, logged_in_client, test_db
    ):
        """意图：标题为空时 flash 校验错误且不入库（文章数保持 6）。"""
        resp = logged_in_client.post(
            "/admin/article/new",
            data={
                "title": "   ",  # 纯空白经 strip 后为空
                "summary": "",
                "content": "有正文",
                "category_id": "1",
                "tags": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "标题、内容和分类不能为空" in response_text(resp)
        assert _count(test_db, "articles") == 6

    def test_create_article_missing_category_rejected(
        self, logged_in_client, test_db
    ):
        """意图：不选分类（category_id 缺省为 None）时同样拒绝写入。"""
        resp = logged_in_client.post(
            "/admin/article/new",
            data={"title": "无分类文章", "content": "正文", "tags": ""},
            follow_redirects=True,
        )
        assert "标题、内容和分类不能为空" in response_text(resp)
        assert _count(test_db, "articles") == 6

    def test_create_article_without_tags(self, logged_in_client, test_db):
        """意图：标签留空不应阻断发布，新文章的标签关联数为 0。"""
        logged_in_client.post(
            "/admin/article/new",
            data={
                "title": "无标签文章",
                "summary": "",
                "content": "正文",
                "category_id": "1",
                "tags": "",
            },
        )
        conn = sqlite3.connect(test_db)
        try:
            new_id = conn.execute(
                "SELECT id FROM articles WHERE title = ?", ("无标签文章",)
            ).fetchone()[0]
            link_count = conn.execute(
                "SELECT COUNT(*) FROM article_tags WHERE article_id = ?",
                (new_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        assert link_count == 0

    def test_create_requires_login(self, client, test_db):
        """意图：未登录直接 POST 发布文章应被拦截，数据库不新增任何文章。"""
        resp = client.post(
            "/admin/article/new",
            data={"title": "越权文章", "content": "x", "category_id": "1"},
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
        assert _count(test_db, "articles") == 6


# ================= 文章编辑 =================
class TestEditArticle:
    """GET/POST /admin/article/edit/<id>。"""

    def test_edit_form_prefills(self, logged_in_client):
        """意图：编辑页应预填文章 1 的原标题与标签。"""
        resp = logged_in_client.get("/admin/article/edit/1")
        assert resp.status_code == 200
        body = response_text(resp)
        assert "Flask 入门" in body
        assert "入门教程" in body  # 原标签应回填到输入框

    def test_edit_submit_updates_content(self, logged_in_client, test_db):
        """意图：提交修改后标题更新，且标签关联被整体替换
        （旧标签「入门教程」解绑，新标签「新标签」绑定，Flask 保留）。"""
        resp = logged_in_client.post(
            "/admin/article/edit/1",
            data={
                "title": "Flask 入门（修订版）",
                "summary": "新摘要",
                "content": "修订后的正文",
                "category_id": "1",
                "tags": "Flask, 新标签",
            },
        )
        assert resp.status_code == 302
        assert _count(test_db, "articles") == 6  # 是更新不是新增

        conn = sqlite3.connect(test_db)
        try:
            title = conn.execute(
                "SELECT title FROM articles WHERE id = 1"
            ).fetchone()[0]
            tag_names = {
                r[0]
                for r in conn.execute(
                    """SELECT t.name FROM tags t
                       JOIN article_tags at ON at.tag_id = t.id
                       WHERE at.article_id = 1"""
                )
            }
        finally:
            conn.close()
        assert title == "Flask 入门（修订版）"
        assert tag_names == {"Flask", "新标签"}

    def test_edit_missing_article_404(self, logged_in_client):
        """意图：编辑不存在的文章应返回 404，而不是渲染空表单。"""
        resp = logged_in_client.get("/admin/article/edit/99999")
        assert resp.status_code == 404


# ================= 文章删除 =================
class TestDeleteArticle:
    """POST /admin/article/delete/<id>。"""

    def test_delete_article(self, logged_in_client, test_db):
        """意图：删除后文章与其标签关联一并消失，前台访问变为 404。"""
        resp = logged_in_client.post("/admin/article/delete/1")
        assert resp.status_code == 302
        assert _count(test_db, "articles") == 5
        assert _count(
            test_db, "article_tags", "article_id = ?", (1,)
        ) == 0
        assert logged_in_client.get("/article/1").status_code == 404

    def test_delete_requires_login(self, client, test_db):
        """意图：未登录的删除请求必须被拦截，文章 1 仍然存在。"""
        resp = client.post("/admin/article/delete/1")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
        assert _count(test_db, "articles", "id = ?", (1,)) == 1

    def test_delete_nonexistent_is_noop(self, logged_in_client, test_db):
        """意图：删除不存在的 id 不应报错，原有文章数量保持不变。"""
        resp = logged_in_client.post("/admin/article/delete/99999")
        assert resp.status_code == 302
        assert _count(test_db, "articles") == 6


# ================= 分类管理 =================
class TestCategoryManage:
    """POST /admin/category/new。"""

    def test_create_category(self, logged_in_client, test_db):
        """意图：新分类创建成功，分类数 4→5。"""
        resp = logged_in_client.post(
            "/admin/category/new", data={"name": "人工智能"}
        )
        assert resp.status_code == 302
        assert _count(test_db, "categories") == 5
        assert _count(
            test_db, "categories", "name = ?", ("人工智能",)
        ) == 1

    def test_duplicate_category_ignored(self, logged_in_client, test_db):
        """意图：同名分类重复提交靠 UNIQUE + INSERT OR IGNORE 容错，
        不报错也不产生重复行。"""
        logged_in_client.post(
            "/admin/category/new", data={"name": "重复分类"}
        )
        resp = logged_in_client.post(
            "/admin/category/new", data={"name": "重复分类"}
        )
        assert resp.status_code == 302
        assert _count(
            test_db, "categories", "name = ?", ("重复分类",)
        ) == 1

    def test_empty_category_not_created(self, logged_in_client, test_db):
        """意图：名称为空时静默跳过，分类数保持 4。"""
        resp = logged_in_client.post(
            "/admin/category/new", data={"name": "  "}
        )
        assert resp.status_code == 302
        assert _count(test_db, "categories") == 4

    def test_category_requires_login(self, client, test_db):
        """意图：未登录不能创建分类。"""
        resp = client.post(
            "/admin/category/new", data={"name": "越权分类"}
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
        assert _count(test_db, "categories") == 4
