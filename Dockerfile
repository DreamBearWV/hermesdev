FROM python:3.11-slim

WORKDIR /app

# 1. 安裝基本工具與 ChromaDB 所需的 C++ 編譯環境 (ARM64 支援)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 2. 安裝 Python 依賴套件（包含 fastapi, uvicorn, openai, chromadb, python-telegram-bot 等）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 複製專案原始碼
COPY . .

# 4. 給予啟動腳本執行權限
RUN chmod +x /app/start.sh

# 5. 開放 API 埠號
EXPOSE 8000

# 6. 改由 start.sh 同時啟動 FastAPI 與 Telegram Bot
CMD ["/app/start.sh"]