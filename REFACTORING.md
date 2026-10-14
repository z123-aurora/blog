# 个人技术博客 —— 代码重构说明

> 重构日期：2026-09-27
> 重构范围：`app.py`、`init_db.py`、`templates/`、`tests/`、`pytest.ini`
> 重构原则：**不改功能、不改页面表现、不改对外路由 URL；只改内部结构、命名与测试组织方式。**
> 验证结论：重构后 **70 条测试全部通过**，前台两个版本与后台全部功能实测正常。

---

## 一、重构背景

本次重构依据一份代码审查清单（命名不规范 9 项、结构混乱 6 项、重复冗余 7 项，共 22 项）进行。
原代码功能完整、测试齐全，但在长期可维护性上存在三类典型问题：

1. **命名不规范**：常量缩写歧义、函数名与 Python 内置/模块归属混淆、参数名过于泛化；
2. **结构混乱**：单函数承担多项职责、两套连接管理并存、测试直接拼接 SQL、测试硬编码业务数据；
3. **重复冗余**：两个版本首页视图几乎完全重复、辅助函数在三个测试文件里各抄一遍、示例数据与建库逻辑耦合。

重构目标是让代码「见名知意、职责单一、数据与逻辑分离、测试稳健可复用」，同时**保证零功能回归**。

---

## 二、改了什么 / 为什么改 / 收益

### 1. 命名规范化（9 项）

| # | 原命名 | 新命名 | 位置 |
|---|---|---|---|
| 1 | `PER_PAGE` | `POSTS_PER_PAGE` | app.py:29 |
| 2 | `inject_globals()` | `inject_sidebar_data()` | app.py:106 |
| 3 | `args`（分页/查询参数） | `query_params` / `sql_params` | app.py 全局 |
| 4 | `index_v2()` | `index_dark()` | app.py:171 |
| 5 | `init_db.get_conn()`（与 `app.get_db()` 重叠） | 统一为 `init_db.create_connection()` | init_db.py:17 |
| 6 | `_count(where="", args=())` | `_count(where_clause="", params=())` + 表名白名单 | tests/test_admin.py |
| 7-9 | 三个测试文件各自定义 `_text(resp)` | 收敛为 conftest 共享函数 `response_text(resp)` | tests/ |

**为什么改：**
- `PER_PAGE` 含义过宽，改为 `POSTS_PER_PAGE` 能立刻看出是「文章列表每页条数」；
- `globals` 容易与 Python 内置概念混淆，且未描述注入内容，新名直接说明注入的是「侧栏数据」；
- `args` 在数据库语境里无法区分「SQL 参数」与普通参数，`query_params` 语义明确；
- 函数名带版本号 `v2` 属于暴露实现细节，按**界面风格**命名为 `index_dark` 更稳定（将来换 v3 也不必再改函数名）；
- `where` 是 SQL 关键字、`args` 易与 pytest fixture 概念冲突。

**收益：** 阅读代码时无需再猜「这个 args 是什么」「get_conn 和 get_db 有什么区别」；新人上手与全局搜索成本明显下降；后续改名不会牵动无关模块。

---

### 2. 结构优化（6 项）

#### 2.1 拆分「上帝分页函数」 `paginate()`

- **改了什么**：把一个同时做「计数 + 算总页数 + 夹页码 + 取数据」的函数，拆为两个单一职责函数：
  - `get_total_count(count_sql, query_params)` —— 只负责 COUNT 取总数（app.py:112）；
  - `fetch_paginated_rows(base_sql, query_params, page, total, per_page)` —— 只负责按页取行并夹取越界页码（app.py:117）。
  - 首页、分类、标签、搜索 4 处分页调用全部改用新 API。
- **为什么改**：原函数违反单一职责，数据访问（两条 SQL）与业务计算（页码夹取）耦合在一起，且调用方必须同时提供「列表 SQL + 计数 SQL」，复用粒度不合理。
- **收益**：计数与取数可独立测试、独立复用；函数签名各自只依赖自己需要的参数；分页测试也相应拆分为「总数/页数」与「每页行数/页码夹取」两类断言，意图更清晰。

#### 2.2 合并两个重复的首页视图

- **改了什么**：`index()` 与 `index_v2()` 的数据准备逻辑原本逐行重复（同样的列表 SQL、计数 SQL、最新文章 SQL、render 参数）。现抽出内部函数 `_render_home(template_name)`（app.py:153），两个路由只负责传不同的模板名；同时把三条 SQL 提升为模块常量 `HOME_LIST_SQL` / `HOME_COUNT_SQL` / `LATEST_ARTICLES_SQL`。
- **为什么改**：违反 DRY，同一段查询维护两份，改一处漏一处的风险很高。
- **收益**：首页查询逻辑只有「唯一事实来源」，以后调整排序或每页条数只需改一处；新增第三个皮肤只需一行路由。

#### 2.3 统一数据库连接管理

- **改了什么**：全站只保留一个连接工厂 `init_db.create_connection(db_path=None)`，`app.get_db()` 在 Flask `g` 中缓存并复用它；删除了 app.py 里重复的 `sqlite3.connect + row_factory + PRAGMA` 配置。
- **为什么改**：原先 app.py 与 init_db.py 各写一套连接配置，生命周期与参数容易随时间漂移。
- **收益**：Row 工厂、外键约束等配置在唯一入口维护；应用与脚本行为一致。
- **实现细节（踩坑记录）**：默认参数特意写成 `db_path=None` 后在函数体内读取全局 `DB_PATH`，而不是 `def create_connection(db_path=DB_PATH)`。因为默认值在模块导入时即绑定，会导致测试 monkeypatch `DB_PATH` 后仍连到真实库——重构首次跑测时因此出现大面积 `no such table`，改为延迟读取后修复。

#### 2.4 测试辅助函数 `_count` 安全加固

- **改了什么**：参数更名为 `where_clause` / `params`；新增**表名白名单**（仅允许 articles/categories/tags/article_tags）；强制条件值以 `?` 占位符传入并参数化；补充安全约定注释。
- **为什么改**：原实现用 f-string 直接拼接 WHERE 片段，虽然当前都是受控输入，但结构上留了 SQL 注入隐患。
- **收益**：即使将来误传外部输入也无法注入或跨表；测试辅助代码同样符合生产级安全规范。

#### 2.5 「发文成功」用例改为纯应用接口验证

- **改了什么**：`test_create_article_full` 原先 POST 后直接 `sqlite3.connect` 查库验证标签关联。现改为完整走 HTTP 接口链路：**POST 发布 → 后台统计 6 变 7 → 前台首页找到新文章链接 → 访问详情页确认标题与两个标签渲染**，全程不直连数据库。
- **为什么改**：单元/功能测试应通过应用对外接口验证结果，绕过数据访问层会让测试与底层表结构强耦合。
- **收益**：即使以后把裸 SQL 换成 ORM，这条用例也不用改；同时它顺带验证了「发布—列表—详情」整条真实链路。

#### 2.6 去除测试中的硬编码业务数据

- **改了什么**：`test_app.py` 中写死的标题 `"Docker 部署"` 改为从数据源动态获取：`from init_db import SAMPLE_ARTICLES`，用 `SAMPLE_ARTICLES[-1]["title"]` 表示「最新一篇」。
- **为什么改**：示例文章一旦调整标题或顺序，硬编码断言就会误失败，测试与生产数据耦合过紧。
- **收益**：示例内容迭代时测试自动适配，断言表达的是「最新文章应出现在首页」这一**行为**而非某个固定字符串。

---

### 3. 消除重复冗余（7 项）

| # | 冗余点 | 处理方式 |
|---|---|---|
| 1 | 两个首页视图函数体重复 | 抽 `_render_home(template_name)`（见 2.2） |
| 2 | 4 处分页重复「列表 SQL + 计数 SQL」模式 | 拆 `get_total_count` + `fetch_paginated_rows`，SQL 提常量（见 2.1） |
| 3 | `_count` 定义位置争议 | 核实仅 test_admin 使用，保留为该文件局部函数（正确归属，不强行上提） |
| 4-6 | `_text(resp)` 在三个测试文件中重复三遍 | 提取为 `conftest.response_text()`，各文件 import 共用 |
| 7 | 6 篇示例文章、4 个分类、建表语句内联在 `init_db()` 中 | 提取为模块级纯数据 `SCHEMA_SQL` / `SAMPLE_CATEGORIES` / `SAMPLE_ARTICLES`，`init_db()` 只保留流程 |

**为什么改（示例数据分离）**：原 `init_db()` 长达 300+ 行，数据和「建表—判空—写入」流程混在一起，既难读也无法被测试或其他脚本复用。
**收益**：数据是数据、流程是流程；测试可以直接 `import SAMPLE_ARTICLES` 驱动断言（2.6 的基础）；要增减示例文章只需改数据列表，不碰建库逻辑。

---

### 4. 配套：pytest 9 中文用例 id 转义问题（测试可观测性）

- **改了什么**：在 `pytest.ini` 增加 `disable_test_id_escaping_and_forfeit_all_rights_to_community_support = True`。
- **为什么改**：pytest 在管道/非 TTY 环境默认把非 ASCII 参数化 id 转义成 `\u547d\u4e2d...`，日志和截图里中文用例名不可读；且旧资料中的选项名 `..._media_support` 在 pytest 9 已移除（会报 Unknown config option），新名称为 `..._community_support`（已查本机 `_pytest/python.py` 源码确认）。
- **收益**：`[命中多篇]` 等中文用例 id 在终端、CI 日志、测试截图中直接可读，且消除配置告警。

---

## 三、没有改动的部分（明确边界）

为控制风险，以下内容**刻意保持不变**：

- **对外 URL 全部不变**：仍是 `/`、`/v2`、`/article/<id>`、`/admin` 等；函数改名只影响内部 endpoint 名，已同步更新所有模板引用。
- **页面表现不变**：版本一浅色风、版本二深色科技风、Logo/Banner、样式文件均未调整。
- **数据库结构与数据不变**：4 张表 schema、6 篇示例文章内容完全一致，真实 `database.db` 无需迁移。
- **未过度设计**：审查建议中的「封装 `PaginatedQuery` 类」暂不实施——当前仅 4 个调用点，两个函数已消除重复，引入类反而增加抽象成本；待分页场景明显增多后再升级。
- 测试仍为 **70 条**，未删减覆盖面；分页与连接相关用例只是跟随新 API 改名/改写断言。

---

## 四、涉及文件清单

| 文件 | 改动性质 |
|---|---|
| `app.py` | 常量/函数/参数重命名；拆分分页；合并首页视图；统一连接工厂；移除未用的 `import sqlite3` |
| `init_db.py` | `get_conn` → `create_connection`（延迟读 DB_PATH）；数据提取为 `SCHEMA_SQL`/`SAMPLE_CATEGORIES`/`SAMPLE_ARTICLES` |
| `templates/base_v2.html`、`templates/index_v2.html` | 仅同步 endpoint：`index_v2` → `index_dark`（模板文件名保留不变） |
| `tests/conftest.py` | 新增共享函数 `response_text` |
| `tests/test_core.py` | 分页用例改测两个新函数；连接用例改测 `create_connection` |
| `tests/test_app.py` | 共用 `response_text`；硬编码标题改为读 `SAMPLE_ARTICLES` |
| `tests/test_admin.py` | 共用 `response_text`；`_count` 加白名单与参数化；发文用例改纯接口验证 |
| `pytest.ini` | 新增 pytest 9 中文 id 不转义选项 |

---

## 五、验证结果

1. **自动化测试**：`python -m pytest -v` → **70 passed**（test_admin 25 + test_app 24 + test_core 21），无失败、无错误、无跳过。
2. **真实运行回归**（http://127.0.0.1:5000）：
   - 版本一 `/`、版本二 `/v2`（含分页 `/v2?page=2`）均 200，分页链接正确；
   - 文章详情、分类、标签、搜索（含中文关键词）、归档、登录、后台、404 全部正常；
   - 版本二页头/页脚 Logo2、Banner2 与切换入口正常；两版本静态资源互不串用。
3. **数据安全**：全程测试使用临时数据库，真实 `database.db` 未被改动；后台统计仍为 6 篇文章 / 4 个分类。
4. 运行结果截图与原始输出留存于 `reports/pytest_result.png`、`reports/pytest_output.txt`。

---

## 六、重构收益总结

- **可读性**：命名见名知意，函数职责单一，300 行的建库函数瘦身为「数据 + 简短流程」；
- **可维护性**：重复逻辑收敛为唯一实现，改一处即全站生效；新增页面皮肤成本从「复制整段查询」降为「一行路由」；
- **健壮性**：测试与底层实现解耦（接口验证、动态数据驱动），安全上消除了 SQL 拼接结构隐患；
- **可观测性**：中文用例名在日志与截图中可读；
- **零风险**：功能、URL、页面、数据、测试数量全部保持不变，70 条测试构成重构安全网。
