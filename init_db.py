# -*- coding: utf-8 -*-
"""初始化博客数据库：建表 + 写入示例数据

设计说明：
    - SCHEMA_SQL / SAMPLE_CATEGORIES / SAMPLE_ARTICLES 是纯数据，
      与建库流程分离，测试或脚本可直接 import 复用（避免硬编码漂移）。
    - create_connection() 是全站唯一的 sqlite 连接创建入口，
      app.py 的 get_db() 也复用它，保证连接配置一致。
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def create_connection(db_path=None):
    """创建一个配置好 Row 工厂与外键约束的 SQLite 连接。

    独立于 Flask 上下文：既可被 app.get_db() 调用，
    也可供命令行直接运行本模块时使用。

    注意：db_path 默认值在函数体内延迟读取模块全局 DB_PATH，
    而不是用 def create_connection(db_path=DB_PATH) 的定义期绑定，
    以便测试 monkeypatch DB_PATH 后能立即生效。
    """
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    content TEXT NOT NULL,
    category_id INTEGER,
    views INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS article_tags (
    article_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (article_id, tag_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
"""

SAMPLE_CATEGORIES = ["Python", "Web 开发", "数据库", "工具与效率"]

SAMPLE_ARTICLES = [
    {
        "title": "Flask 入门：从零搭建一个 Web 应用",
        "summary": "Flask 是一个轻量级 Python Web 框架，本文带你从零开始理解路由、模板与请求处理。",
        "category": "Python",
        "tags": ["Flask", "入门教程"],
        "content": """## 为什么选择 Flask

Flask 以「微框架」著称：核心简洁，扩展丰富。你可以在几分钟内跑起一个 Web 应用，又能按需引入数据库、认证等能力。

## 最小可用示例

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, Flask!"

if __name__ == "__main__":
    app.run(debug=True)
```

## 核心概念

1. **路由**：用 `@app.route` 把 URL 映射到视图函数
2. **模板**：使用 Jinja2 渲染 HTML，支持继承与宏
3. **请求对象**：`request` 封装了表单、参数、文件等输入

> 建议：项目变大后使用「应用工厂 + 蓝图」组织代码，结构会清晰很多。

## 下一步

- 接入 SQLite / SQLAlchemy 做数据持久化
- 使用蓝图拆分模块
- 部署到服务器（gunicorn + nginx）""",
    },
    {
        "title": "Markdown 写作指南：让技术文章更专业",
        "summary": "掌握标题、列表、代码块、表格等常用 Markdown 语法，提升技术写作效率。",
        "category": "工具与效率",
        "tags": ["Markdown", "写作"],
        "content": """## 常用语法速查

### 代码块

用三个反引号包裹，并标注语言以获得高亮：

```python
def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```

### 表格

| 语法 | 用途 |
| ---- | ---- |
| `#` | 标题 |
| `>` | 引用 |
| `-` | 列表 |

### 引用与强调

> 好的技术文章 = 清晰的结构 + 准确的示例 + 必要的配图。

使用 **加粗** 突出重点，使用 `行内代码` 标记命令与代码。

## 写作建议

- 先列提纲，再填内容
- 每个知识点配一个可运行的最小示例
- 定期回顾旧文章，保持内容不过时""",
    },
    {
        "title": "SQLite 数据库在小型项目中的最佳实践",
        "summary": "SQLite 零配置、单文件、性能足够，非常适合个人博客与中小型应用。本文总结常用实践。",
        "category": "数据库",
        "tags": ["SQLite", "最佳实践"],
        "content": """## 为什么用 SQLite

- **零配置**：无需安装数据库服务，一个文件就是全部
- **足够快**：读操作极其高效，单机写压力不大的场景完全够用
- **易备份**：复制文件即完成备份

## Python 中使用

```python
import sqlite3

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, title FROM articles ORDER BY id DESC")
rows = cur.fetchall()
```

## 实践要点

1. 开启外键约束：`PRAGMA foreign_keys = ON`
2. 使用参数化查询，防止 SQL 注入
3. 读写分离不适用于 SQLite，但可以用 WAL 模式提升并发：

```sql
PRAGMA journal_mode = WAL;
```

> 当并发写入成为瓶颈时，再考虑迁移到 PostgreSQL 也不迟。""",
    },
    {
        "title": "前端三件套复习：HTML 语义化与 CSS 布局",
        "summary": "回顾语义化标签、Flex 与 Grid 布局要点，写出结构清晰、易于维护的页面。",
        "category": "Web 开发",
        "tags": ["HTML", "CSS", "前端"],
        "content": """## 语义化标签

优先使用 `header`、`nav`、`main`、`article`、`footer` 等标签，而不是满屏的 `div`。好处：

- 对屏幕阅读器友好
- SEO 更好
- 代码可读性高

## Flex 布局

```css
.container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
```

## Grid 布局

```css
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
}
```

## 一点心得

布局选型：整体骨架用 Grid，局部对齐用 Flex，二者互补而非互斥。""",
    },
    {
        "title": "Python 装饰器详解：写出更优雅的代码",
        "summary": "装饰器是 Python 的进阶特性，本文通过日志、计时、缓存三个例子讲透它的原理与用法。",
        "category": "Python",
        "tags": ["Python", "进阶"],
        "content": """## 什么是装饰器

装饰器本质上是一个「接收函数并返回新函数」的高阶函数，用 `@` 语法糖应用。

## 三个实用例子

### 1. 计时器

```python
import time
from functools import wraps

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} 耗时 {time.perf_counter() - start:.3f}s")
        return result
    return wrapper
```

### 2. 简单缓存

```python
def cache(func):
    memo = {}
    @wraps(func)
    def wrapper(n):
        if n not in memo:
            memo[n] = func(n)
        return memo[n]
    return wrapper
```

### 3. 带参数的装饰器

再包一层即可接收参数：

```python
def repeat(times):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                func(*args, **kwargs)
        return wrapper
    return decorator
```

> 记得使用 `functools.wraps` 保留原函数的元信息。""",
    },
    {
        "title": "用 Docker 部署 Flask 应用的完整流程",
        "summary": "从编写 Dockerfile 到 docker-compose 编排，一步一步把 Flask 应用部署上线。",
        "category": "Web 开发",
        "tags": ["Docker", "部署", "Flask"],
        "content": """## Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

## docker-compose.yml

```yaml
services:
  web:
    build: .
    ports:
      - "8000:5000"
    restart: always
```

## 流程总结

1. `docker compose up -d --build` 构建并启动
2. `docker compose logs -f` 查看日志
3. 更新代码后重复第一步即可

> 生产环境记得关闭 debug 模式，并配置好环境变量。""",
    },
]


def init_db():
    """建表（幂等）并在空库时写入示例分类与文章。"""
    conn = create_connection()
    c = conn.cursor()

    c.executescript(SCHEMA_SQL)

    # 已有数据则不重复写入示例
    if c.execute("SELECT COUNT(*) FROM articles").fetchone()[0] > 0:
        print("数据库已存在数据，跳过示例数据写入。")
        conn.close()
        return

    for name in SAMPLE_CATEGORIES:
        c.execute("INSERT INTO categories (name) VALUES (?)", (name,))

    for art in SAMPLE_ARTICLES:
        c.execute(
            "SELECT id FROM categories WHERE name = ?", (art["category"],)
        )
        cat_id = c.fetchone()["id"]
        c.execute(
            "INSERT INTO articles (title, summary, content, category_id) VALUES (?, ?, ?, ?)",
            (art["title"], art["summary"], art["content"], cat_id),
        )
        article_id = c.lastrowid
        for tag in art["tags"]:
            c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            tag_id = c.execute(
                "SELECT id FROM tags WHERE name = ?", (tag,)
            ).fetchone()["id"]
            c.execute(
                "INSERT OR IGNORE INTO article_tags (article_id, tag_id) VALUES (?, ?)",
                (article_id, tag_id),
            )

    conn.commit()
    conn.close()
    print(f"数据库初始化完成：{DB_PATH}")


if __name__ == "__main__":
    init_db()
