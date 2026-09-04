FROM python:3.11-slim

WORKDIR /app

# 1. 安裝系統基本工具（如 curl、git，以備 Agent 擴充技能時使用）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt-get/lists/*

# 2. 安裝 Python 依賴套件（包含 fastapi, uvicorn, openai 等）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 複製專案原始碼
COPY . .

# 4. 開放 API 埠號
EXPOSE 8000

# 5. 啟動 FastAPI / Uvicorn 服務
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]