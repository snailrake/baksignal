from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core.config import settings
from app.models.enums import Availability, FuelType, QueueLevel


def main_menu() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if settings.mini_app_url:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Открыть карту",
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ]
        )
    buttons.extend(
        [
            [InlineKeyboardButton(text="Сообщить статус", callback_data="report:start")],
            [InlineKeyboardButton(text="Подписаться на топливо", callback_data="sub:start")],
            [InlineKeyboardButton(text="Последние АЗС", callback_data="stations:list")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def fuel_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="АИ-92", callback_data=f"{prefix}:fuel:{FuelType.ai92.value}"),
                InlineKeyboardButton(text="АИ-95", callback_data=f"{prefix}:fuel:{FuelType.ai95.value}"),
                InlineKeyboardButton(text="ДТ", callback_data=f"{prefix}:fuel:{FuelType.diesel.value}"),
            ]
        ]
    )


def availability_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Есть", callback_data=f"report:availability:{Availability.yes.value}"),
                InlineKeyboardButton(text="Нет", callback_data=f"report:availability:{Availability.no.value}"),
                InlineKeyboardButton(
                    text="Не уверен", callback_data=f"report:availability:{Availability.unknown.value}"
                ),
            ]
        ]
    )


def queue_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Нет", callback_data=f"report:queue:{QueueLevel.none.value}"),
                InlineKeyboardButton(text="Малая", callback_data=f"report:queue:{QueueLevel.small.value}"),
            ],
            [
                InlineKeyboardButton(text="Средняя", callback_data=f"report:queue:{QueueLevel.medium.value}"),
                InlineKeyboardButton(text="Большая", callback_data=f"report:queue:{QueueLevel.large.value}"),
            ],
        ]
    )

