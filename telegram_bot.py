# telegram_bot.py
import os
import logging
import requests
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = os.getenv("ALLOWED_TELEGRAM_USER_ID", "")
HERMES_API_URL = os.getenv("HERMES_API_URL", "http://127.0.0.1:8000/chat")
CORE_MEMORY_URL = os.getenv("CORE_MEMORY_URL", "http://127.0.0.1:8000/memory/core")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def is_authorized(user_id: int) -> bool:
    if not ALLOWED_USER_ID:
        return True
    return str(user_id) == str(ALLOWED_USER_ID)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ 未授權的使用者。")
        return
    await update.message.reply_text("🤖 你好！我是 Hermes Agent。隨時發送訊息給我，我會自動為你記錄與回應！\n\n輸入 /memory 可以查看目前的 Core Memory。")

async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    try:
        res = requests.get(CORE_MEMORY_URL, timeout=10).json()
        core = res.get("core_memory", {})
        msg = f"🧠 *[Core Memory]*\n\n*Persona:*\n{core.get('persona', '無')}\n\n*Human:*\n{core.get('human', '無')}"
        await update.message.reply_markdown(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ 讀取記憶失敗: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("⛔ 未授權的使用者。")
        return

    user_text = update.message.text
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        response = requests.post(
            HERMES_API_URL,
            json={"prompt": user_text},
            timeout=60
        )
        if response.status_code == 200:
            reply_text = response.json().get("response", "（Hermes 沒有產生任何回覆）")
        else:
            reply_text = f"❌ Hermes 服務回應錯誤 (HTTP {response.status_code})"
    except Exception as e:
        reply_text = f"❌ 無法連線至 Hermes 服務: {e}"

    await update.message.reply_text(reply_text)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("memory", memory_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Hermes Telegram Bot 正式啟動...")
    app.run_polling()