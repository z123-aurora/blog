# -*- coding: utf-8 -*-
"""pytest 共享夹具（fixture）

核心隔离策略（对应速查表第 ⑥、⑨ 节）：
    用 monkeypatch 把 app 模块和 init_db 模块各自的 DB_PATH 指向
    tmp_path 下的临时数据库，再调用 init_db.init_db() 建表+灌示例数据。
    真实的 database.db 全程不会被触碰，测试结束后 monkeypatch 自动还原。
"""
import pytest

import app as app_module
import init_db


def response_text(resp):
    """把响应体转成字符串（三个测试文件共用的辅助函数）。

    用法：from conftest import response_text
    """
    return resp.get_data(as_text=True)


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """准备一个带示例数据的临时数据库，返回其文件路径。

    app.py 和 init_db.py 在模块顶层各自计算了一份 DB_PATH，
    两处持有不同的字符串变量，因此必须分别 patch。
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))
    monkeypatch.setattr(init_db, "DB_PATH", str(db_path))
    # 在临时库中建表并写入 6 篇示例文章
    init_db.init_db()
    return str(db_path)


@pytest.fixture()
def client(test_db):
    """Flask 官方测试客户端：不启动真实服务器即可发请求。"""
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture()
def app_ctx(test_db):
    """推入 Flask 应用上下文，用于直接调用依赖 g/db 的纯逻辑函数。"""
    with app_module.app.app_context():
        yield


@pytest.fixture()
def logged_in_client(client):
    """在 client 基础上完成后台登录，后续请求自动携带会话 Cookie。"""
    resp = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 302  # 登录成功应跳转后台
    return client
