# memgpt_tools.py
from typing import List, Dict, Any

MEMGPT_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "core_memory_replace",
            "description": "更新 Core Memory 中特定區塊的整體內容（用於修正或覆蓋已知的使用者個人資訊、習慣或偏好）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["human", "persona"],
                        "description": "要更新的核心記憶區塊：human (使用者資訊) 或 persona (Agent 設定)"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "替換後的新完整描述內文"
                    }
                },
                "required": ["section", "new_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "core_memory_append",
            "description": "在 Core Memory 指定區塊末尾追加新訊息，無須整體覆蓋舊內容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["human", "persona"],
                        "description": "要追加內容的目標區塊"
                    },
                    "text_to_append": {
                        "type": "string",
                        "description": "要額外補充寫入的事實或細節"
                    }
                },
                "required": ["section", "text_to_append"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "archival_memory_insert",
            "description": "將長篇技術細節、專案歷史或複雜知識寫入 ChromaDB 向量庫，並必須帶上主題標籤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "需要長期歸檔存查的詳細知識文字內容"
                    },
                    "topic": {
                        "type": "string",
                        "description": "該知識所屬的主題分類標籤（例如：python, docker, hardware, network, personal）"
                    }
                },
                "required": ["content", "topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "archival_memory_search",
            "description": "當無法回答或需要檢索過去的歷史紀錄、專案細節時，在 ChromaDB 進行語意向量搜尋。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋的關鍵字或語意描述問題"
                    },
                    "topic": {
                        "type": "string",
                        "description": "(可選) 指定主題標籤過濾，留空則搜尋全域向量庫"
                    }
                },
                "required": ["query"]
            }
        }
    }
]