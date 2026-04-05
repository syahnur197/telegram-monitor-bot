import logging
from urllib.parse import urlparse

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown
from sqlmodel import select

from src.models.database import async_session
from src.models.service import Service
from src.config import Config

logger = logging.getLogger(__name__)

NAME, URL = range(2)


def is_allowed(user_id: int) -> bool:
    return user_id in Config.ALLOWED_USER_IDS


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    if not parsed.netloc:
        return False

    if not parsed.hostname:
        return False

    return True


def _service_status_text(service: Service) -> str:
    if service.last_checked_at is None:
        return "⚪ UNKNOWN"
    return "🟢 UP" if service.is_up else "🔴 DOWN"


async def _reply_unauthorized(update: Update) -> None:
    message = update.effective_message
    if message:
        await message.reply_text("You are not authorized to use this bot.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not is_allowed(update.effective_user.id):
        await _reply_unauthorized(update)
        return

    message = update.effective_message
    if not message:
        return

    await message.reply_text(
        "Welcome to Service Monitor Bot!\n\n"
        "Commands:\n"
        "/add_service - Add a new service to monitor\n"
        "/delete_service <service_name> - Remove a monitored service\n"
        "/list_services - List all monitored services\n"
        "/cancel - Cancel the current add flow"
    )


async def add_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_user or not is_allowed(update.effective_user.id):
        await _reply_unauthorized(update)
        return ConversationHandler.END

    message = update.effective_message
    if not message:
        return ConversationHandler.END

    context.user_data.clear()
    await message.reply_text("What's the name of the service you want to monitor?")
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_user or not is_allowed(update.effective_user.id):
        await _reply_unauthorized(update)
        context.user_data.clear()
        return ConversationHandler.END

    message = update.effective_message
    if not message or not message.text:
        context.user_data.clear()
        return ConversationHandler.END

    name = message.text.strip()
    if not name:
        await message.reply_text("Service name cannot be empty. Please enter a valid name.")
        return NAME

    context.user_data["service_name"] = name
    await message.reply_text("What's the endpoint or URL I should poll?")
    return URL


async def receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_user or not is_allowed(update.effective_user.id):
        await _reply_unauthorized(update)
        context.user_data.clear()
        return ConversationHandler.END

    message = update.effective_message
    if not message or not message.text:
        context.user_data.clear()
        return ConversationHandler.END

    name = context.user_data.get("service_name")
    if not name:
        await message.reply_text("Session expired. Please run /add_service again.")
        context.user_data.clear()
        return ConversationHandler.END

    url = message.text.strip()

    if not _is_valid_url(url):
        await message.reply_text("Please provide a valid http:// or https:// URL.")
        return URL

    try:
        async with async_session() as session:
            existing_by_name = await session.exec(
                select(Service).where(Service.name == name)
            )
            if existing_by_name.first():
                await message.reply_text(
                    f"Service '{name}' already exists. Use a different name."
                )
                context.user_data.clear()
                return ConversationHandler.END

            existing_by_url = await session.exec(
                select(Service).where(Service.url == url)
            )
            if existing_by_url.first():
                await message.reply_text(
                    f"The URL '{url}' is already being monitored."
                )
                context.user_data.clear()
                return ConversationHandler.END

            service = Service(name=name, url=url)
            session.add(service)
            await session.commit()

    except Exception:
        logger.exception("Failed to add service '%s' with URL '%s'", name, url)
        await message.reply_text("Failed to add service due to a database error.")
        context.user_data.clear()
        return ConversationHandler.END

    await message.reply_text(
        f"✅ Service '{name}' ({url}) has been added and is now being monitored!"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_user or not is_allowed(update.effective_user.id):
        await _reply_unauthorized(update)
        context.user_data.clear()
        return ConversationHandler.END

    message = update.effective_message
    if message:
        await message.reply_text("Cancelled adding service.")

    context.user_data.clear()
    return ConversationHandler.END


async def delete_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not is_allowed(update.effective_user.id):
        await _reply_unauthorized(update)
        return

    message = update.effective_message
    if not message:
        return

    if not context.args:
        await message.reply_text(
            "Usage: /delete_service <service_name>\n\n"
            "Use /list_services to see service names."
        )
        return

    service_name = " ".join(context.args).strip()
    if not service_name:
        await message.reply_text("Please provide a valid service name.")
        return

    try:
        async with async_session() as session:
            result = await session.exec(
                select(Service).where(Service.name == service_name)
            )
            service = result.first()

            if not service:
                await message.reply_text(f"Service '{service_name}' not found.")
                return

            await session.delete(service)
            await session.commit()

    except Exception:
        logger.exception("Failed to delete service '%s'", service_name)
        await message.reply_text("Failed to delete service due to a database error.")
        return

    await message.reply_text(f"🗑️ Service '{service_name}' has been removed.")


async def list_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not is_allowed(update.effective_user.id):
        await _reply_unauthorized(update)
        return

    message = update.effective_message
    if not message:
        return

    try:
        async with async_session() as session:
            result = await session.exec(select(Service))
            services = result.all()
    except Exception:
        logger.exception("Failed to list services")
        await message.reply_text("Failed to load services due to a database error.")
        return

    if not services:
        await message.reply_text("No services are being monitored.")
        return

    lines = ["*Monitored Services:*", ""]

    for service in services:
        safe_name = escape_markdown(service.name, version=2)
        safe_url = escape_markdown(service.url, version=2)
        safe_status = escape_markdown(_service_status_text(service), version=2)

        lines.append(f"• *{safe_name}*")
        lines.append(f"  {safe_url}")
        lines.append(f"  Status: {safe_status}")
        lines.append("")

    msg = "\n".join(lines)

    await message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


def get_add_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add_service", add_service_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
        allow_reentry=True,
    )