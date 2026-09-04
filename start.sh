#!/bin/sh
# 在背景啟動 Telegram Bot
python3 telegram_bot.py &

# 在前台啟動 FastAPI 主服務
exec uvicorn main:app --host 0.0.0.0 --port 8000