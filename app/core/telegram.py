import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramUser:
    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> TelegramUser:
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("Telegram initData hash is missing")

    auth_date_raw = parsed.get("auth_date")
    if not auth_date_raw:
        raise TelegramInitDataError("Telegram initData auth_date is missing")

    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise TelegramInitDataError("Telegram initData auth_date is invalid") from exc

    if time.time() - auth_date > max_age_seconds:
        raise TelegramInitDataError("Telegram initData is expired")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramInitDataError("Telegram initData hash is invalid")

    user_raw = parsed.get("user")
    if not user_raw:
        raise TelegramInitDataError("Telegram initData user is missing")

    try:
        user_data = json.loads(user_raw)
        user_id = int(user_data["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TelegramInitDataError("Telegram initData user payload is invalid") from exc

    return TelegramUser(
        id=user_id,
        username=user_data.get("username"),
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
    )

