FROM python:3.11-slim

WORKDIR /app

# 1. 安裝基本工具與 ChromaDB 所需的 C++ 編譯環境 (ARM64 支援)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 2. 安裝 Python 依賴套件（包含 fastapi, uvicorn, openai, chromadb 等）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 複製專案原始碼
COPY . .

# 4. 開放 API 埠號
EXPOSE 8000

# 5. 啟動 FastAPI / Uvicorn 服務
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]