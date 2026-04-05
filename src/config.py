import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ALLOWED_USER_IDS = [
        int(uid.strip())
        for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
        if uid.strip()
    ]
    DATABASE_URL = "sqlite+aiosqlite:///./monitor.db"
    POLL_INTERVAL_SECONDS = 300  # 5 minutes
    ALERT_AFTER_SECONDS = 600  # 10 minutes
