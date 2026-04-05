import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from sqlmodel import select

from src.models.database import async_session
from src.models.service import Service
from src.config import Config

logger = logging.getLogger(__name__)

NAME, URL = range(2)


def is_allowed(user_id: int) -> bool:
    return user_id in Config.ALLOWED_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "Welcome to Service Monitor Bot!\n\n"
        "Commands:\n"
        "/add-service - Add a new service to monitor\n"
        "/delete-service - Remove a monitored service\n"
        "/list-services - List all monitored services"
    )


async def add_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END
    await update.message.reply_text(
        "What's the name of the service you want to monitor?"
    )
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["service_name"] = update.message.text
    await update.message.reply_text("What's the endpoint or URL I should poll?")
    return URL


async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = context.user_data["service_name"]
    url = update.message.text

    async with async_session() as session:
        service = Service(name=name, url=url)
        session.add(service)
        await session.commit()

    await update.message.reply_text(
        f"✅ Service '{name}' ({url}) has been added and is now being monitored!"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled adding service.")
    context.user_data.clear()
    return ConversationHandler.END


async def delete_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /delete-service <service_name>\n\n"
            "Use /list-services to see service names."
        )
        return

    service_name = " ".join(context.args)

    async with async_session() as session:
        result = await session.exec(select(Service).where(Service.name == service_name))
        service = result.first()

        if not service:
            await update.message.reply_text(f"Service '{service_name}' not found.")
            return

        await session.delete(service)
        await session.commit()

    await update.message.reply_text(f"🗑️ Service '{service_name}' has been removed.")


async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    async with async_session() as session:
        result = await session.exec(select(Service))
        services = result.all()

    if not services:
        await update.message.reply_text("No services are being monitored.")
        return

    msg = "*Monitored Services:*\n\n"
    for s in services:
        status = "🟢 UP" if s.is_up else "🔴 DOWN"
        msg += f"• *{s.name}*\n  {s.url}\n  Status: {status}\n\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


def get_add_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add_service", add_service_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )
