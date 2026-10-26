网址与环境ID
静态版（作业交付地址）：https://blog-d3gd2wmcb82969ac9-1511513920.tcloudbaseapp.com/blog4/
CloudBase 环境ID：100053993154
完整动态版（含后台）：https://personal-tech-blog-10060.app.workbuddy.host/?sharecode=ZFCMKOTS27
后台入口：/login    账号：admin    密码：admin123

一、项目简介
个人技术博客，Flask + SQLite 实现：首页（含分页、深浅两套皮肤）、文章详情、
分类、标签、搜索、归档，以及文章增删改的后台管理。

二、目录结构
app.py                        Flask 主应用（路由、分页、Markdown 渲染、登录保护）
init_db.py                    建库与初始化种子数据
database.db                   SQLite 数据库（本地文件，不入 git 仓库；克隆后运行 app.py 自动重建）
templates/                    Jinja2 模板（base.html 浅色版 / base_v2.html 深色版）
static/                       样式表与图片资源
cloudfunctions/addComment/    云函数：写入留言到 comments 集合
freeze_static.py              静态化导出脚本（生成静态托管用的纯 HTML 站点）
Dockerfile                    云托管容器镜像定义
readme.txt                    本说明

三、怎么装依赖
已安装 Python 3.11+ 时执行：
    pip install -r requirements.txt
依赖仅两个：flask>=3.0、markdown>=3.5

四、怎么启动
1) 本地运行：
    python app.py
    浏览器打开 http://127.0.0.1:5000（首次运行自动建库；仓库不含 database.db，
    从 git 克隆后也可手动执行 python init_db.py 重建）

2) 云托管（容器）运行：
    docker build -t blog .
    docker run -p 8080:8080 blog
    浏览器打开 http://127.0.0.1:8080
    或在 CloudBase 控制台选「本地代码部署 → 上传文件夹」，端口填 8080

3) 静态站导出（可选，用于静态托管交付）：
    python freeze_static.py --out ../blog_static/blog4 --prefix /blog4
    将生成结果上传到静态托管的 blog4/ 目录

五、注意事项
1. 容器内 SQLite 数据在每次重新部署时会被清空，真实数据需迁移到云数据库；
2. 启动必须绑定 0.0.0.0，写 127.0.0.1 会导致容器外无法访问；
3. 静态托管只分发文件、不执行 Python，直接把 Flask 源码上传只会显示未渲染的模板；
4. 打包时已排除 node_modules、虚拟环境、__pycache__、.git 与含密钥的 .env。
