# agent_loop.py
import os
import json
import sqlite3
from typing import List, Dict, Any
from openai import OpenAI
from memory_db import (
    DB_PATH,
    get_core_memory,
    update_core_memory,
    insert_archival_memory,
    search_archival_memory
)
from memgpt_tools import MEMGPT_TOOLS

# 初始化 OpenRouter 客戶端
client = OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY"),
    base_url=os.getenv("MINIMAX_BASE_URL", "https://openrouter.ai/api/v1")
)

def get_recent_recall_memory(limit: int = 10) -> List[Dict[str, str]]:
    """從 SQLite 讀取最新 10 條對話紀錄（保持時間順序）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM recall_memory ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    # 倒序排列還原為 Chronological 順序
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

def save_recall_memory(role: str, content: str):
    """將訊息寫入 SQLite 對話紀錄"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO recall_memory (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()
    conn.close()

def build_system_prompt() -> str:
    """根據當前 SQLite 中的 Core Memory 動態組裝 System Prompt"""
    core = get_core_memory()
    persona = core.get("persona", "我是 Hermes Agent。")
    human = core.get("human", "使用者資訊未知。")
    
    return f"""你是 Hermes Agent，運行在樹莓派 5 上的 AI 助理。

[CORE MEMORY - PERSONA]
{persona}

[CORE MEMORY - HUMAN (使用者資訊與習慣)]
{human}

【記憶修改指南】：
1. 若得知使用者的資訊變更（如名稱、偏好、硬體配置），你必須呼叫 `core_memory_replace` 或 `core_memory_append`。
2. 若有長篇技術細節或未來需備查的資訊，請呼叫 `archival_memory_insert` 並帶上合適的 topic 標籤。
3. 若需要回想或查詢過去的檔案，請呼叫 `archival_memory_search`。
"""

def run_agent_turn(user_input: str) -> str:
    """執行標準雙輪次 Agent 迴圈"""
    # 1. 讀取 Core Memory 並建立提示詞
    system_prompt = build_system_prompt()
    
    # 2. 讀取最新 10 條歷史紀錄 (LIMIT 10)
    history = get_recent_recall_memory(limit=10)
    
    # 3. 組合完整 Message List
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    
    # 先將使用者輸入寫入 Recall Memory
    save_recall_memory("user", user_input)
    
    # 第一輪 API 呼叫：讓模型決定回覆或調用工具
    response = client.chat.completions.create(
        model="minimax/minimax-m3:free",
        messages=messages,
        tools=MEMGPT_TOOLS,
        tool_choice="auto"
    )
    
    response_msg = response.choices[0].message
    
    # 判斷是否需要執行 Tool Call
    if response_msg.tool_calls:
        messages.append(response_msg)  # 帶入模型發起的 Tool Calls 紀錄
        
        for tool_call in response_msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            execution_result = ""
            
            # 執行本地資料庫變更
            if func_name == "core_memory_replace":
                section = args.get("section", "human")
                new_content = args.get("new_content", "")
                update_core_memory(section, new_content)
                execution_result = f"Core memory block '{section}' updated."
                
            elif func_name == "core_memory_append":
                section = args.get("section", "human")
                text = args.get("text_to_append", "")
                current_core = get_core_memory()
                old_text = current_core.get(section, "")
                update_core_memory(section, f"{old_text} {text}".strip())
                execution_result = f"Appended text to core memory block '{section}'."
                
            elif func_name == "archival_memory_insert":
                content = args.get("content", "")
                topic = args.get("topic", "general")
                insert_archival_memory(content=content, topic=topic)
                execution_result = f"Content archived under topic '{topic}'."
                
            elif func_name == "archival_memory_search":
                query = args.get("query", "")
                docs = search_archival_memory(query=query)
                execution_result = f"Archival search results: {json.dumps(docs, ensure_ascii=False)}"
            
            # 將工具執行結果作為 tool 角色加回對話隊列
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": execution_result
            })
        
        # 第二輪 API 呼叫：讓模型根據工具執行結果產生最終自然語言回覆
        second_response = client.chat.completions.create(
            model="minimax/minimax-m3:free",
            messages=messages
        )
        final_reply = second_response.choices[0].message.content or "已完成記憶更新。"
    else:
        final_reply = response_msg.content or ""

    # 將 Agent 最終回覆寫入 Recall Memory
    save_recall_memory("assistant", final_reply)
    return final_reply