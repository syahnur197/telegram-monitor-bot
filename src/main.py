import logging
import asyncio

from telegram.ext import ApplicationBuilder, CommandHandler

from config import Config
from models.database import init_db
from handlers.commands import (
    start,
    delete_service,
    list_services,
    get_add_conversation_handler,
)
from utils.monitor import poll_all_services

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application):
    await init_db()
    logger.info("Database initialized")


async def polling_job(context):
    await poll_all_services(context.bot)


def main():
    if not Config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set in .env")
    if not Config.ALLOWED_USER_IDS:
        raise ValueError("ALLOWED_USER_IDS not set in .env")

    app = ApplicationBuilder().token(Config.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("delete_service", delete_service))
    app.add_handler(CommandHandler("list_services", list_services))
    app.add_handler(get_add_conversation_handler())

    job_queue = app.job_queue
    job_queue.run_repeating(
        polling_job, interval=Config.POLL_INTERVAL_SECONDS, first=10
    )

    logger.info("Bot started. Polling every %d seconds.", Config.POLL_INTERVAL_SECONDS)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
