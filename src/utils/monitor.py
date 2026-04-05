import httpx
import logging
from datetime import datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.service import Service
from config import Config

logger = logging.getLogger(__name__)


async def check_service(session: AsyncSession, service: Service, bot) -> None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(service.url)
            is_now_up = response.status_code < 500
    except Exception:
        is_now_up = False

    now = datetime.utcnow()

    if service.is_up and not is_now_up:
        service.is_up = False
        service.first_down_at = now
        service.last_checked_at = now
        await session.commit()
        logger.info(f"Service '{service.name}' ({service.url}) is DOWN")

    elif not service.is_up and is_now_up:
        service.is_up = True
        service.first_down_at = None
        service.last_checked_at = now
        await session.commit()
        await _notify_all_users(
            bot,
            f"✅ *Service Restored*: {service.name}\n{service.url} is back up and running!",
        )
        logger.info(f"Service '{service.name}' is UP again")

    elif not service.is_up and not is_now_up:
        service.last_checked_at = now
        await session.commit()
        if service.first_down_at and (now - service.first_down_at) >= timedelta(
            seconds=Config.ALERT_AFTER_SECONDS
        ):
            await _notify_all_users(
                bot,
                f"🚨 *Service Down*: {service.name}\n{service.url} has been down for 10+ minutes!",
            )
            service.first_down_at = now
            await session.commit()
            logger.info(f"Alert sent for service '{service.name}'")

    else:
        service.last_checked_at = now
        await session.commit()


async def _notify_all_users(bot, message: str) -> None:
    from config import Config

    for user_id in Config.ALLOWED_USER_IDS:
        try:
            await bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")


async def poll_all_services(bot) -> None:
    from models.database import async_session

    async with async_session() as session:
        result = await session.exec(select(Service))
        services = result.all()

        for service in services:
            await check_service(session, service, bot)
