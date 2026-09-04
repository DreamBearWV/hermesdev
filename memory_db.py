# memory_db.py
import sqlite3
import uuid
import chromadb
from typing import Dict, List, Optional

DB_PATH = "hermes_memory.db"
CHROMA_PATH = "./chroma_db"

# 初始化 ChromaDB 向量資料庫（本地持久化儲存）
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
archival_collection = chroma_client.get_or_create_collection(name="archival_memory")


def init_db():
    """初始化 SQLite 與 ChromaDB 記憶結構"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Core Memory (固定寫入 System Prompt，Key-Value 結構)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS core_memory (
            section TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Recall Memory (短中層對話歷史)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recall_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT DEFAULT 'default',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 寫入預設 Core Memory
    cursor.execute("""
        INSERT OR IGNORE INTO core_memory (section, content) 
        VALUES ('persona', '我是 Hermes Agent，運行在 Raspberry Pi 5 上的 AI 助理。')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO core_memory (section, content) 
        VALUES ('human', '使用者名稱未知，技術偏好：使用 Python、Docker 與樹莓派 5。')
    """)

    conn.commit()
    conn.close()


# --- Core Memory 操作介面 ---
def get_core_memory() -> Dict[str, str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT section, content FROM core_memory")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def update_core_memory(section: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO core_memory (section, content) VALUES (?, ?) 
        ON CONFLICT(section) DO UPDATE SET content=excluded.content, updated_at=CURRENT_TIMESTAMP
    """,
        (section, content),
    )
    conn.commit()
    conn.close()


# --- Recall Memory 操作介面 (支援 LIMIT 10) ---
def get_recent_recall_memory(limit: int = 10) -> List[Dict[str, str]]:
    """從 SQLite 僅讀取最新 N 條對話歷史 (預設 10 條，按時間順序排列)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM recall_memory ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    # 反轉以保持時間序列 (Chronological Order)
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]


def save_recall_memory(role: str, content: str):
    """將對話紀錄寫入 SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO recall_memory (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()
    conn.close()


# --- Archival Memory (ChromaDB 向量) 操作介面 ---
def insert_archival_memory(content: str, topic: str = "general"):
    """將長效記憶轉換為向量文字塊並存入 ChromaDB"""
    doc_id = str(uuid.uuid4())
    archival_collection.add(
        documents=[content], metadatas=[{"topic": topic}], ids=[doc_id]
    )


def search_archival_memory(query: str, topic: Optional[str] = None, n_results: int = 3) -> List[str]:
    """使用語意相似度檢索 Archival Memory (支援 Topic 標籤過濾)"""
    where_filter = {"topic": topic} if topic else None
    results = archival_collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter
    )
    if results and results.get("documents") and results["documents"]:
        return results["documents"][0]
    return []


if __name__ == "__main__":
    init_db()
    print("✅ SQLite 與 ChromaDB 記憶引擎初始化完畢！")