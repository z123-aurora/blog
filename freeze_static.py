# -*- coding: utf-8 -*-
"""把 Flask 博客渲染为纯静态站点，用于部署到 CloudBase 静态网站托管。

用法:
    python freeze_static.py --out <输出目录> [--prefix /blog4]

产出:
    - 所有公开页面（首页/深色版/文章/分类/标签/归档）渲染为扁平 .html 文件
    - /static/** 原样复制
    - 搜索改为纯前端实现（search.html + search-index.json）
    - 站内链接统一重写为 <prefix>/xxx.html 形式
"""
import argparse
import json
import math
import os
import re
import shutil
import sqlite3
import sys
from urllib.parse import urlsplit, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import app, DB_PATH, POSTS_PER_PAGE  # noqa: E402

OUT_DIR = None
PREFIX = ""


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def enumerate_urls():
    """按数据库内容枚举所有需要渲染的 URL（含分页）。"""
    conn = db()
    urls = ["/"]
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    for p in range(2, math.ceil(total / POSTS_PER_PAGE) + 1):
        urls.append(f"/?page={p}")
    urls.append("/v2")
    for p in range(2, math.ceil(total / POSTS_PER_PAGE) + 1):
        urls.append(f"/v2?page={p}")

    for row in conn.execute("SELECT id FROM articles"):
        urls.append(f"/article/{row['id']}")

    for row in conn.execute(
        "SELECT id, COUNT(*) c FROM articles WHERE category_id IS NOT NULL "
        "GROUP BY category_id"
    ):
        urls.append(f"/category/{row['id']}")
        for p in range(2, math.ceil(row["c"] / POSTS_PER_PAGE) + 1):
            urls.append(f"/category/{row['id']}?page={p}")

    for row in conn.execute(
        "SELECT tag_id, COUNT(DISTINCT article_id) c FROM article_tags GROUP BY tag_id"
    ):
        urls.append(f"/tag/{row['tag_id']}")
        for p in range(2, math.ceil(row["c"] / POSTS_PER_PAGE) + 1):
            urls.append(f"/tag/{row['tag_id']}?page={p}")

    urls.append("/archives")
    urls.append("/search")
    conn.close()
    return urls


def url_to_file(url):
    """URL（含 ?page= 查询参数）→ 输出目录内的相对文件路径。"""
    parts = urlsplit(url)
    page = parse_qs(parts.query).get("page", [None])[0]
    path = parts.path

    if path in ("", "/"):
        return "index.html" if not page else f"page-{page}.html"
    if path == "/v2":
        return "v2.html" if not page else f"v2-page-{page}.html"

    m = re.fullmatch(r"/article/(\d+)", path)
    if m:
        return f"article-{m.group(1)}.html"
    m = re.fullmatch(r"/category/(\d+)", path)
    if m:
        return f"category-{m.group(1)}.html" if not page else \
            f"category-{m.group(1)}-page-{page}.html"
    m = re.fullmatch(r"/tag/(\d+)", path)
    if m:
        return f"tag-{m.group(1)}.html" if not page else \
            f"tag-{m.group(1)}-page-{page}.html"
    if path == "/archives":
        return "archives.html"
    if path == "/search":
        return "search.html"
    raise ValueError(f"未知的内部 URL: {url}")


def map_link(value):
    """把页面里的站内链接重写为静态文件地址（带部署前缀）。"""
    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or not parts.path.startswith("/"):
        return None  # 外链 / 锚点 / 相对路径，不动
    page = parse_qs(parts.query).get("page", [None])[0]
    path = parts.path.rstrip("/") or "/"

    if path == "/":
        return f"{PREFIX}/page-{page}.html" if page else f"{PREFIX}/"
    if path == "/v2":
        return f"{PREFIX}/v2-page-{page}.html" if page else f"{PREFIX}/v2.html"
    m = re.fullmatch(r"/article/(\d+)", path)
    if m:
        return f"{PREFIX}/article-{m.group(1)}.html"
    m = re.fullmatch(r"/category/(\d+)", path)
    if m:
        return (f"{PREFIX}/category-{m.group(1)}-page-{page}.html" if page
                else f"{PREFIX}/category-{m.group(1)}.html")
    m = re.fullmatch(r"/tag/(\d+)", path)
    if m:
        return (f"{PREFIX}/tag-{m.group(1)}-page-{page}.html" if page
                else f"{PREFIX}/tag-{m.group(1)}.html")
    if path == "/archives":
        return f"{PREFIX}/archives.html"
    if path == "/search":
        return f"{PREFIX}/search.html"
    if path in ("/login", "/logout") or path.startswith("/admin"):
        return "#"  # 静态站无后台，导航入口置空
    if path.startswith("/static/"):
        return f"{PREFIX}{path}"
    return None


ATTR_RE = re.compile(r'((?:href|src|action)=")([^"]*)(")')


def rewrite_links(html):
    def repl(m):
        mapped = map_link(m.group(2))
        return m.group(1) + (mapped if mapped is not None else m.group(2)) + m.group(3)
    return ATTR_RE.sub(repl, html)


SEARCH_JS = """
<script>
(function () {
  var BASE = "__PREFIX__";
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  var form = document.querySelector("form.search-form");
  if (!form) return;
  var cache = null;
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = form.querySelector("input[name=q]").value.trim().toLowerCase();
    var main = document.querySelector("main.main-content");
    var render = function (data) {
      var hits = !q ? [] : data.filter(function (a) {
        return (a.title + " " + (a.summary || "") + " " + (a.text || ""))
          .toLowerCase().indexOf(q) !== -1;
      });
      var html = "<h1 class=\\"page-title\\">🔍 搜索：" + esc(q) +
        " <small>找到 " + hits.length + " 篇</small></h1>";
      if (q && !hits.length) {
        html += "<div class=\\"empty-state\\">没有找到与「" + esc(q) + "」相关的文章。</div>";
      }
      hits.forEach(function (a) {
        html += "<article class=\\"article-card\\"><h2 class=\\"card-title\\"><a href=\\"" +
          a.url + "\\">" + esc(a.title) + "</a></h2><div class=\\"card-meta\\"><span>" +
          a.date + "</span></div><p class=\\"card-summary\\">" + esc(a.summary || "") +
          "</p><a class=\\"read-more\\" href=\\"" + a.url + "\\">阅读全文 →</a></article>";
      });
      if (!q) html += "<div class=\\"empty-state\\">请输入关键词进行搜索。</div>";
      main.innerHTML = html;
    };
    if (cache) { render(cache); return; }
    fetch(BASE + "/search-index.json")
      .then(function (r) { return r.json(); })
      .then(function (d) { cache = d; render(d); });
  });
})();
</script>
"""


def build_search_index():
    conn = db()
    items = []
    for row in conn.execute(
        "SELECT id, title, summary, content, created_at FROM articles "
        "ORDER BY created_at DESC, id DESC"
    ):
        items.append({
            "id": row["id"],
            "title": row["title"],
            "summary": row["summary"],
            "date": (row["created_at"] or "")[:10],
            "url": f"{PREFIX}/article-{row['id']}.html",
            "text": row["content"],
        })
    conn.close()
    return items


def main():
    global OUT_DIR, PREFIX
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="静态站点输出目录")
    parser.add_argument("--prefix", default="/blog4",
                        help="部署子路径前缀（站点将被上传到该目录下）")
    args = parser.parse_args()
    PREFIX = args.prefix.rstrip("/")
    OUT_DIR = os.path.abspath(args.out)
    os.makedirs(OUT_DIR, exist_ok=True)

    client = app.test_client()
    urls = enumerate_urls()
    print(f"共 {len(urls)} 个页面待渲染，输出目录: {OUT_DIR}，链接前缀: {PREFIX}")

    for url in urls:
        resp = client.get(url)
        if resp.status_code != 200:
            print(f"  [跳过] {url} -> HTTP {resp.status_code}")
            continue
        html = rewrite_links(resp.get_data(as_text=True))
        rel = url_to_file(url)
        dest = os.path.join(OUT_DIR, rel)
        os.makedirs(os.path.dirname(dest) or OUT_DIR, exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        print(f"  [OK] {url} -> {rel}")

    # 搜索页注入前端检索脚本 + 生成索引
    search_path = os.path.join(OUT_DIR, "search.html")
    if os.path.exists(search_path):
        with open(search_path, "r", encoding="utf-8") as f:
            html = f.read()
        html = html.replace("</body>", SEARCH_JS.replace("__PREFIX__", PREFIX) + "</body>")
        with open(search_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        print("  [OK] search.html 已注入前端搜索脚本")
    with open(os.path.join(OUT_DIR, "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(build_search_index(), f, ensure_ascii=False)
    print("  [OK] search-index.json 已生成")

    # 复制静态资源
    static_src = os.path.join(BASE_DIR, "static")
    static_dst = os.path.join(OUT_DIR, "static")
    if os.path.isdir(static_dst):
        shutil.rmtree(static_dst)
    shutil.copytree(static_src, static_dst)
    print("  [OK] static/ 静态资源已复制")

    print("全部完成。")


if __name__ == "__main__":
    main()
