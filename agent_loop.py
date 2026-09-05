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
from system_tools import get_system_status_data

# 初始化 OpenRouter / MiniMax 客戶端
client = OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY"),
    base_url=os.getenv("MINIMAX_BASE_URL", "https://openrouter.ai/api/v1")
)

# --- 擴充 Tool 宣告清單（包含 MemGPT 工具與系統診斷工具）---

SYSTEM_STATUS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_system_status",
        "description": "讀取樹莓派當前的背景程式進程 (ps aux top RAM/CPU)、Docker 容器現況與硬體資源 (RAM/Disk) 使用率。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

# 組合 MemGPT 記憶工具與系統診斷工具
ALL_TOOLS = MEMGPT_TOOLS + [SYSTEM_STATUS_TOOL]


def get_recent_recall_memory(limit: int = 10) -> List[Dict[str, str]]:
    """從 SQLite 讀取最新 N 條對話紀錄（保持時間順序）"""
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
    """根據當前 SQLite 中的 Core Memory 動態組裝 System Prompt，並加入強效行為護欄與系統診斷能力"""
    core = get_core_memory()
    persona = core.get("persona", "我是 Hermes Agent，運行在樹莓派 5 上的 AI 助理。")
    human = core.get("human", "使用者資訊未知。")
    
    return f"""你是 Hermes Agent，運行在樹莓派 5 (ARM64) Docker 容器內的自主 AI 助理。

[CORE MEMORY - PERSONA]
{persona}

[CORE MEMORY - HUMAN (使用者資訊與習慣)]
{human}

【嚴格記憶與系統工具呼叫規則】：
1. 當使用者提及任何個人資訊、習慣、偏好、生日、姓名或要求你「記住/更新/修改」記憶時，你【必須】發起 `core_memory_append` 或 `core_memory_replace` 工具呼叫。
2. 絕對禁止在沒有產生 Tool Call 的情況下口頭宣稱「已記錄」、「好的我記住了」。沒有觸發工具就等於沒有寫入資料庫！
3. 若有長篇技術細節或未來需備查的資訊，請呼叫 `archival_memory_insert` 並帶上合適的 topic 標籤。
4. 若需要回想或查詢過去的檔案或備註，請呼叫 `archival_memory_search`。
5. 【系統診斷】當使用者詢問樹莓派系統狀態、記憶體/CPU 佔用、背景程式進程、有沒有沒用到的程式、或是 Docker 容器現況時，你【必須】呼叫 `get_system_status` 工具讀取系統資料，並針對取得的進程進行專業分析，區分必要服務與可刪除的廢稿進程。
"""


def run_agent_turn(user_input: str) -> str:
    """執行標準雙輪次 Agent 迴圈 (經 OpenRouter 呼叫 MiniMax 3)"""
    # 1. 讀取最新 Core Memory 並建立動態 Prompt
    system_prompt = build_system_prompt()
    
    # 2. 讀取最新 10 條歷史紀錄 (LIMIT 10)
    history = get_recent_recall_memory(limit=10)
    
    # 3. 組合 Message List
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    
    # 寫入使用者輸入至 Recall Memory
    save_recall_memory("user", user_input)
    
    # 4. 第一輪 API 呼叫：讓模型決定回覆或調用工具
    response = client.chat.completions.create(
        model="minimax/minimax-m3:free",
        messages=messages,
        tools=ALL_TOOLS,
        tool_choice="auto"
    )
    
    response_msg = response.choices[0].message
    
    # 5. 判斷是否觸發 Tool Call
    if response_msg.tool_calls:
        # 將模型的 Tool Call 請求訊息加回歷史隊列（OpenAI 標準格式）
        messages.append(response_msg)
        
        for tool_call in response_msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            execution_result = ""
            
            # --- 記憶庫操作工具 ---
            if func_name == "core_memory_replace":
                section = args.get("section", "human")
                new_content = args.get("new_content", "")
                update_core_memory(section, new_content)
                execution_result = f"Successfully replaced core memory section '{section}'."
                
            elif func_name == "core_memory_append":
                section = args.get("section", "human")
                text = args.get("text_to_append", "")
                current_core = get_core_memory()
                old_text = current_core.get(section, "")
                
                # 自動避免重複追加相同字串
                if text in old_text:
                    updated_text = old_text
                else:
                    updated_text = f"{old_text} {text}".strip()
                    
                update_core_memory(section, updated_text)
                execution_result = f"Successfully appended text to core memory section '{section}'."
                
            elif func_name == "archival_memory_insert":
                content = args.get("content", "")
                topic = args.get("topic", "general")
                insert_archival_memory(content=content, topic=topic)
                execution_result = f"Content successfully archived under topic '{topic}'."
                
            elif func_name == "archival_memory_search":
                query = args.get("query", "")
                docs = search_archival_memory(query=query)
                execution_result = f"Archival search results: {json.dumps(docs, ensure_ascii=False)}"
            
            # --- 樹莓派系統診斷工具 ---
            elif func_name == "get_system_status":
                sys_data = get_system_status_data()
                execution_result = f"System status report: {json.dumps(sys_data, ensure_ascii=False)}"
            
            # 將工具執行結果作為 tool 角色回應模型
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": execution_result
            })
        
        # 6. 第二輪 API 呼叫：讓 MiniMax 根據工具執行結果產生最終分析與建議
        second_response = client.chat.completions.create(
            model="minimax/minimax-m3:free",
            messages=messages
        )
        final_reply = second_response.choices[0].message.content or "已完成系統查詢與分析。"
    else:
        final_reply = response_msg.content or ""

    # 7. 將 Agent 的最終回覆寫入 Recall Memory
    save_recall_memory("assistant", final_reply)
    return final_reply