# StudyBot 后端 Docker 镜像
# 开发环境：代码通过 docker-compose volumes 挂入，pip 包在镜像构建时安装
# 生产环境：可将 COPY . /app 加入以打包代码

FROM python:3.11-slim

# 防止 Python 生成 .pyc 文件、缓冲输出（Docker 里不需要）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 安装系统依赖（psycopg2-binary 需要 libpq）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# 先只复制依赖文件，利用 Docker 层缓存（代码改了不用重新 pip install）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 FastAPI 端口
EXPOSE 8000

# 启动命令（--reload 在开发时热重载，生产环境去掉）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
