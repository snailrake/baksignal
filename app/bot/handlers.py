from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.keyboards import availability_keyboard, fuel_keyboard, main_menu, queue_keyboard
from app.models.enums import Availability, FuelType, QueueLevel, SourceType
from app.models.station import Station
from app.models.subscription import Subscription
from app.services.observation_service import create_observation_with_status

router = Router()


class ReportState(StatesGroup):
    station_id = State()
    fuel_type = State()
    availability = State()
    queue_level = State()
    limit_liters = State()


class SubscriptionState(StatesGroup):
    fuel_type = State()
    district = State()


@router.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "БакСигнал: отметки по наличию топлива на АЗС Саратова и Энгельса.",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "stations:list")
async def list_stations(callback: CallbackQuery, session: AsyncSession) -> None:
    result = await session.scalars(
        select(Station).options(selectinload(Station.statuses)).order_by(Station.id).limit(20)
    )
    stations = list(result)
    if not stations:
        await callback.message.answer("База АЗС пока пустая. Следующий шаг - импортировать АЗС.")
        await callback.answer()
        return

    lines = ["Первые АЗС в базе:"]
    for station in stations:
        lines.append(f"{station.id}. {station.name}, {station.address}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "report:start")
async def report_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReportState.station_id)
    await callback.message.answer(
        "Введите ID АЗС. Сейчас ID можно посмотреть через /docs или кнопку 'Последние АЗС'."
    )
    await callback.answer()


@router.message(ReportState.station_id)
async def report_station_id(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        station_id = int(message.text or "")
    except ValueError:
        await message.answer("Нужен числовой ID АЗС.")
        return

    station = await session.get(Station, station_id)
    if station is None:
        await message.answer("АЗС с таким ID не найдена.")
        return

    await state.update_data(station_id=station_id)
    await state.set_state(ReportState.fuel_type)
    await message.answer(f"АЗС: {station.name}, {station.address}\nВыберите топливо.", reply_markup=fuel_keyboard("report"))


@router.callback_query(ReportState.fuel_type, F.data.startswith("report:fuel:"))
async def report_fuel(callback: CallbackQuery, state: FSMContext) -> None:
    fuel_type = callback.data.rsplit(":", 1)[-1]
    await state.update_data(fuel_type=fuel_type)
    await state.set_state(ReportState.availability)
    await callback.message.answer("Есть это топливо?", reply_markup=availability_keyboard())
    await callback.answer()


@router.callback_query(ReportState.availability, F.data.startswith("report:availability:"))
async def report_availability(callback: CallbackQuery, state: FSMContext) -> None:
    availability = callback.data.rsplit(":", 1)[-1]
    await state.update_data(availability=availability)
    await state.set_state(ReportState.queue_level)
    await callback.message.answer("Какая очередь?", reply_markup=queue_keyboard())
    await callback.answer()


@router.callback_query(ReportState.queue_level, F.data.startswith("report:queue:"))
async def report_queue(callback: CallbackQuery, state: FSMContext) -> None:
    queue_level = callback.data.rsplit(":", 1)[-1]
    await state.update_data(queue_level=queue_level)
    await state.set_state(ReportState.limit_liters)
    await callback.message.answer("Лимит в литрах? Напишите число или 0, если лимита нет/не знаете.")
    await callback.answer()


@router.message(ReportState.limit_liters)
async def report_limit(message: Message, state: FSMContext, session: AsyncSession) -> None:
    try:
        raw_limit = int(message.text or "0")
    except ValueError:
        await message.answer("Напишите число. Если лимит неизвестен - 0.")
        return

    report_data = await state.get_data()
    station = await session.get(Station, report_data["station_id"])
    if station is None:
        await state.clear()
        await message.answer("АЗС не найдена. Начните заново.", reply_markup=main_menu())
        return

    await create_observation_with_status(
        session,
        station=station,
        data={
            "station_id": report_data["station_id"],
            "fuel_type": FuelType(report_data["fuel_type"]),
            "availability": Availability(report_data["availability"]),
            "queue_level": QueueLevel(report_data["queue_level"]),
            "limit_liters": raw_limit if raw_limit > 0 else None,
            "source_type": SourceType.user,
            "telegram_user_id": message.from_user.id if message.from_user else None,
        },
        bot=message.bot,
    )
    await state.clear()

    await message.answer("Статус сохранен. Спасибо.", reply_markup=main_menu())


@router.callback_query(F.data == "sub:start")
async def subscription_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SubscriptionState.fuel_type)
    await callback.message.answer("На какое топливо подписаться?", reply_markup=fuel_keyboard("sub"))
    await callback.answer()


@router.callback_query(SubscriptionState.fuel_type, F.data.startswith("sub:fuel:"))
async def subscription_fuel(callback: CallbackQuery, state: FSMContext) -> None:
    fuel_type = callback.data.rsplit(":", 1)[-1]
    await state.update_data(fuel_type=fuel_type)
    await state.set_state(SubscriptionState.district)
    await callback.message.answer("Напишите район, например: Ленинский, Заводской, Энгельс.")
    await callback.answer()


@router.message(SubscriptionState.district)
async def subscription_district(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить Telegram пользователя.")
        return

    district = (message.text or "").strip()
    if not district:
        await message.answer("Напишите район текстом.")
        return

    data = await state.get_data()
    existing = await session.scalar(
        select(Subscription).where(
            Subscription.telegram_user_id == message.from_user.id,
            Subscription.fuel_type == FuelType(data["fuel_type"]),
            Subscription.district == district,
        )
    )
    if existing is not None:
        existing.active = True
    else:
        subscription = Subscription(
            telegram_user_id=message.from_user.id,
            fuel_type=FuelType(data["fuel_type"]),
            district=district,
        )
        session.add(subscription)
    await session.commit()
    await state.clear()

    await message.answer(f"Подписка сохранена: {data['fuel_type']} / {district}.", reply_markup=main_menu())
