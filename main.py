# main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from memory_db import (
    init_db, 
    get_core_memory, 
    archival_collection,
    get_recent_recall_memory
)
from agent_loop import run_agent_turn
from system_tools import get_system_status_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 容器啟動時自動初始化 SQLite 與 ChromaDB 表格
    init_db()
    print("🚀 Hermes Agent MemGPT 記憶系統與系統診斷模組初始化完畢！")
    yield

app = FastAPI(
    title="Hermes Agent on Pi 5",
    description="具備 MemGPT 分層記憶、系統進程診斷與動態 Tool Call 機制的 AI Agent",
    lifespan=lifespan
)

class ChatRequest(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    """保留原版根目錄狀態回應"""
    return {"status": "online", "agent": "Hermes-Pi5", "message": "Hermes Agent 服務運行中"}

@app.post("/chat")
def chat_with_agent(req: ChatRequest):
    """主對話介面：觸發 MemGPT 雙輪次控制迴圈 (包含記憶自動更新)"""
    try:
        reply = run_agent_turn(req.prompt)
        return {"prompt": req.prompt, "response": reply}
    except Exception as e:
        print(f"❌ Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 系統診斷 Endpoints ---

@app.get("/system/status")
def inspect_system_status():
    """即時檢視樹莓派系統資源與 Docker 容器現況"""
    return {
        "status": "success",
        "system_data": get_system_status_data()
    }

# --- 記憶體檢視與除錯 Endpoints ---

@app.get("/memory/core")
def inspect_core_memory():
    """即時檢視 SQLite Core Memory (Persona & Human)"""
    return {
        "status": "success",
        "core_memory": get_core_memory()
    }

@app.get("/memory/recall")
def inspect_recall_memory(limit: int = 10):
    """即時檢視 SQLite 對話歷史 (預設最新 10 條)"""
    return {
        "status": "success",
        "recall_memory": get_recent_recall_memory(limit=limit)
    }

@app.get("/memory/archival")
def inspect_archival_memory():
    """即時檢視 ChromaDB 向量庫中的長效知識與 Topic"""
    try:
        data = archival_collection.get()
        return {
            "status": "success",
            "total_items": len(data.get("ids", [])),
            "documents": data.get("documents", []),
            "metadatas": data.get("metadatas", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))