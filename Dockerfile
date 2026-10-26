# Flask 博客云托管镜像
# 说明：静态托管只能分发文件，Flask 每个请求都要服务端实时计算，必须容器化运行
FROM python:3.11-slim

WORKDIR /app

# 先拷贝依赖清单，便于利用 Docker 层缓存
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝项目源码
COPY . /app

# 容器内监听端口；云托管也会通过 PORT 环境变量注入实际端口
ENV PORT=8080
EXPOSE 8080

# CMD 只能写一行，多个 CMD 仅最后一行生效
CMD ["python3", "app.py"]
