import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="Hermes Agent on Pi 5")

# 讀取 MiniMax API 設定（由 GitHub Secrets 注入 Docker 環境變數）
def get_minimax_client():
    api_key = os.getenv("MINIMAX_API_KEY")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    if not api_key:
        raise ValueError("尚未設定 MINIMAX_API_KEY 環境變數")
    return OpenAI(api_key=api_key, base_url=base_url)

class ChatRequest(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    return {"status": "online", "agent": "Hermes-Pi5", "message": "Hermes Agent 服務運行中"}

@app.post("/chat")
def chat_with_agent(req: ChatRequest):
    try:
        client = get_minimax_client()
        response = client.chat.completions.create(# 關鍵修改：改用 OpenRouter 的 MiniMax 免費模型名稱
            model="minimax/minimax-m3:free",
            messages=[
                {"role": "system", "content": "你是運行在樹莓派 5 上的 Hermes Agent 助手。"},
                {"role": "user", "content": req.prompt}
            ]
        )
        reply = response.choices[0].message.content
        return {"prompt": req.prompt, "response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))