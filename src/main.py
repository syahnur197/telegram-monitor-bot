import logging

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder, CommandHandler

from src.config import Config
from src.models.database import init_db
from src.handlers.commands import (
    start,
    delete_service,
    list_services,
    get_add_conversation_handler,
)
from src.utils.monitor import poll_all_services

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await init_db()
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Show available commands"),
            BotCommand("add_service", "Add a new service to monitor"),
            BotCommand("delete_service", "Remove a monitored service"),
            BotCommand("list_services", "List all monitored services"),
        ]
    )
    logger.info("Database initialized and commands registered")


async def polling_job(context) -> None:
    await poll_all_services(context.bot)


def main() -> None:
    if not Config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set in .env")
    if not Config.ALLOWED_USER_IDS:
        raise ValueError("ALLOWED_USER_IDS not set in .env")

    app = ApplicationBuilder().token(Config.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("delete_service", delete_service))
    app.add_handler(CommandHandler("list_services", list_services))
    app.add_handler(get_add_conversation_handler())

    if app.job_queue is None:
        raise RuntimeError(
            "JobQueue is not available. Install python-telegram-bot with job-queue support."
        )

    app.job_queue.run_repeating(
        polling_job,
        interval=Config.POLL_INTERVAL_SECONDS,
        first=10,
    )

    logger.info("Bot started. Polling every %d seconds.", Config.POLL_INTERVAL_SECONDS)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()