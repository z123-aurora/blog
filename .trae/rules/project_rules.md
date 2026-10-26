---
description: 个人技术博客（Flask + SQLite + CloudBase）项目规则
alwaysApply: true
---

# 项目规则 · 个人技术博客

> 作用：每次会话自动注入上下文，避免重复交代。修改本文件即改变 AI 的默认行为。
> 位置：`<项目根>/.trae/rules/project_rules.md`（随仓库提交，团队共享）

## 1. 技术栈与边界

- 后端只有 Flask + 标准库 `sqlite3`，依赖清单锁定在 `requirements.txt`（flask、markdown）。
- **不得引入 ORM、前端框架、构建工具**（SQLAlchemy / Vue / npm / webpack 一律不加）。
- 模板用 Jinja2，样式为手写 CSS（`static/css/style.css`），不引 CDN 主题。
- 数据库文件 `database.db` 随仓库提供，**禁止删除或重建**（会丢现有文章数据）。

## 2. 目录职责

| 路径 | 职责 | 不允许做的事 |
|---|---|---|
| `app.py` | 路由、视图、模板过滤器、登录保护 | 写建表 SQL、写示例数据 |
| `init_db.py` | 建表 + 种子数据 + `create_connection` | 写业务路由 |
| `templates/` | 只做渲染 | 写业务计算逻辑 |
| `tests/` | 测试 | 触碰真实 `database.db` |
| `freeze_static.py` | 静态化导出 | 影响动态版行为 |

## 3. 测试硬约束（最高优先级）

- 所有测试必须用 `tmp_path` 临时库，通过 `monkeypatch` 分别 patch
  `app.DB_PATH` 与 `init_db.DB_PATH`（模块顶层各自持有一份，必须两处都 patch）。
- 共享夹具只写在 `tests/conftest.py`，禁止在多个测试文件里复制辅助函数。
- 测试断言不得依赖真实数据条数之外的硬编码 id/时间。
- 交付前 `pytest` 必须全绿（当前基线：70 passed），失败一律视为未完成。

## 4. 代码规范

- 命名：常量全大写且表意完整（`POSTS_PER_PAGE`，不用 `PER_PAGE`）；函数用动词开头。
- 一个函数一件事；超过 40 行先拆。
- 连接统一走 `init_db.create_connection(DB_PATH)`，禁止在视图里另起 `sqlite3.connect`。
- 中文注释写"为什么"，不写"是什么"。
- 对外路由 URL **不得变更**（已部署静态站与分享链接依赖）。

## 5. 交付与提交

- 每次改动后同步更新 `readme.txt` 的目录结构与变更说明。
- 重构类改动单独写 `REFACTORING.md`：改了什么 / 为什么改 / 收益 / 验证结果。
- 提交信息格式：`type: 摘要`（feat / fix / refactor / test / docs / chore）。
- 部署链路：`docker build` → CloudBase 云托管（端口 8080）；静态交付用 `freeze_static.py`。

## 6. 回复风格

- 先给结论，再给证据（文件路径 + 行号）。
- 涉及改动的方案，先列影响面（哪些文件、哪些路由、哪些测试），再动手。
- 不确定的外部事实先查证，不猜。
