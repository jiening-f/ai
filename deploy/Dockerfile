# ============================================
# Stage 1: Python 依赖
# ============================================
FROM python:3.11-slim AS python-deps

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: 前端构建
# ============================================
FROM node:20-alpine AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# ============================================
# Stage 3: 运行镜像
# ============================================
FROM python:3.11-slim

WORKDIR /app

# 安装运行时所需系统库（OpenCV、OCR 等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# 复制后端代码
COPY backend/ .

# 复制构建后的前端静态文件
COPY --from=frontend-build /app/dist /app/static

# 创建数据目录
RUN mkdir -p /app/data

EXPOSE 8765

CMD ["python", "server.py"]
