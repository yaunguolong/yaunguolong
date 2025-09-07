# 使用官方Python镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# 安装Poetry
RUN pip install poetry

# 复制项目文件
COPY pyproject.toml poetry.lock* ./

# 安装Python依赖
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# 复制应用代码
COPY . .

# 创建非root用户
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# 创建日志目录
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

# 暴露端口
EXPOSE 8000
EXPOSE 9090  # Prometheus监控端口

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动应用
CMD ["uvicorn", "api.mainV3:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]