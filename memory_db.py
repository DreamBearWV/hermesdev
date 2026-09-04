# memory_db.py
import sqlite3
from typing import Dict, List, Optional

DB_PATH = "hermes_memory.db"

def init_db():
    """初始化 SQLite 資料表，具備防中斷與主題隔離欄位"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Core Memory (固定寫入 System Prompt，Key-Value 結構)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS core_memory (
            section TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Recall Memory (短中層對話歷史，帶有 Session 隔離)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recall_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT DEFAULT 'default',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Archival Memory (長效海量記憶，帶有 Topic 標籤與全文檢索)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS archival_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT DEFAULT 'general',
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 寫入預設 Core Memory (若不存在)
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

if __name__ == "__main__":
    init_db()
    print("✅ 記憶資料庫初始化成功！")