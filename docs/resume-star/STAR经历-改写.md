# 博客项目 → STAR 简历经历改写

> 目标岗位 JD（校招 Python 后端开发，通用版）：熟悉 **Python/Flask** 至少一门 Web 框架；了解 **MySQL/SQLite** 数据库与 **SQL 优化**；熟悉 **Git** 团队协作；了解 **Docker/云部署**、**RESTful** 接口；有**单元测试**、**代码审查**习惯；了解 Web 安全（SQL 注入、XSS、开放重定向）；有**性能优化**经验者优先。
>
> ⚠️ 使用说明：如果你手上有具体岗位的 JD 原文，把关键词对照表第一列替换成 JD 原文关键词即可，改写稿中加粗词已覆盖绝大多数后端校招 JD 的公共关键词池。

---

## 改写前（学生简历常见写法）

> 用 Flask 做了一个个人博客，实现了文章、分类、标签功能，学习了数据库，部署到了云服务器。

问题：无情境、无任务、无动作细节、无量化结果；"学习了"暴露学生视角；一个数字都没有。

---

## 改写后（STAR 版，可直接粘贴进超级简历/Rezi）

**个人技术博客系统（Flask + SQLite + CloudBase）** · 独立开发 · 2026.10

- **【情境 S】** 为解决个人笔记发布与求职展示需求，从 0 到 1 设计并**独立开发**一套全栈博客系统，覆盖 Web 端、**微信小程序端**与**云函数**三种运行形态。
- **【任务 T】** 目标：功能完整可上线（文章/分类/标签/搜索/归档/后台管理）、**测试全绿**、通过 **HTTPS 上线检查**，并按团队 **Git Commit 规范**交付。
- **【行动 A】**
  - 基于 **Flask + Jinja2 + SQLite** 实现约 **1,500 行**后端代码（33 个路由/函数），设计文章、分类、标签、评论等数据模型与 **SQL** 查询，支持分页、模糊搜索与按字面量转义通配符；
  - 编写 **72 个 pytest 单元测试**（核心逻辑/管理后台/monkeypatch 隔离数据库），保持 **100% 通过**，并在导出、部署脚本中实践测试先行；
  - 开发 **2 个云函数**（addComment/listComments）经数据库网关读写评论，配套小程序端 `wx.cloud.callFunction` 接入；
  - 编写 **静态化导出脚本**，把动态站渲染为 29 页纯静态站点（全站 360KB），自动重写站内链接、注入 **og 标签**、生成 404 页与前端搜索索引；
  - 修复 **SQL 通配符注入隐患、登录开放重定向**等安全问题；通过**图片量化压缩**把首屏 Banner 从 **494KB 压至 25.6KB（-95%）**；
  - 全程 **Git 管理 19 次提交**，采用 feat/fix/docs/**chore 规范**（Conventional Commits），Gitee 与 GitHub **双远程同步**。
- **【结果 R】** 站点通过 **HTTPS 上线并逐项通过 8 项检查**（移动端自适应、404 页、首屏资源≤300KB、控制台零报错、29 页 37 条内链 0 失效、分享预览正常）；README 按 **六段式**交付并经第二模型**代码审查**交叉核对。

---

## JD 关键词对照表（关键词 → 真实证据）

| JD 关键词 | 简历落点 | 可验证证据（文件/行） |
| --- | --- | --- |
| Python / Flask | 技术栈主词 | `app.py`，Flask + Jinja2，33 个路由 |
| SQL / 数据库 | SQLite 数据模型与查询 | `init_db.py` 建表与示例数据；搜索通配符转义 fix（commit b2a0212） |
| 单元测试 | 72 个 pytest 全绿 | `pytest -q` → 72 passed in 3.57s |
| Git 规范 | 19 次 Conventional Commits | `git log`（feat/fix/docs/chore） |
| Docker / 云部署 | Dockerfile + CloudBase 云托管 | `Dockerfile`、`cloudbaserc.example.json` |
| RESTful / 云函数 | 2 个云函数读写评论 | `cloudfunctions/addComment`、`listComments` |
| Web 安全 | 修复 SQL 通配符注入、开放重定向 | commit b2a0212 / 2279d5e |
| 性能优化 | 首屏图 -95% | Banner 494KB→25.6KB（commit 5bcc957） |
| 小程序 | 微信小程序端接入 | `miniprogram/` |

## 量化数据出处清单（防面试追问）

| 数字 | 来源 |
| --- | --- |
| 72 个测试 | 2026-10-27 实测 `pytest -q` |
| 19 次提交 | `git log --oneline \| wc -l` |
| ~1,500 行 / 33 函数 | `wc -l` 与 `grep -c "def " app.py` |
| 29 页 / 37 内链 0 失效 | 静态导出后链接爬取脚本结果 |
| 494KB→25.6KB | `ls -la static/Banner.png` 压缩前后 |
| 8 项上线检查 | `docs/launch-check/上线检查清单-8项.png` |
