from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.core.telegram import TelegramInitDataError, TelegramUser, validate_init_data


async def get_optional_telegram_user(
    telegram_init_data: Annotated[str | None, Header(alias="X-Telegram-Init-Data")] = None,
) -> TelegramUser | None:
    if not telegram_init_data:
        return None

    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TELEGRAM_BOT_TOKEN is required to validate initData",
        )

    try:
        return validate_init_data(telegram_init_data, settings.telegram_bot_token)
    except TelegramInitDataError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

