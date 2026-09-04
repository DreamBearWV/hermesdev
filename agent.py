import os
from openai import OpenAI

# 從環境變數讀取 MiniMax 設定
api_key = os.getenv("MINIMAX_API_KEY")
base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

def run_agent(prompt: str):
    print(f"🤖 [Hermes Agent] 收到任務: {prompt}")
    response = client.chat.completions.create(
        model="abab6.5s-chat", # MiniMax 模型名稱
        messages=[
            {"role": "system", "content": "你是運行在樹莓派 5 上的 Hermes Agent 助手。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    result = run_agent("請確認樹莓派 Hermes Agent 系統是否正常運行？")
    print(f"💬 [MiniMax 回應]:\n{result}")