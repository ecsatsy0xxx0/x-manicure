# handlers/user_booking.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta, date

from states.booking_states import BookingStates
from database import db
from keyboards.booking import calendar_inline_kb, times_inline_kb, confirm_booking_kb
from keyboards.main_menu import main_menu_kb
from config import settings
from aiogram.exceptions import TelegramBadRequest

router = Router()

# Диапазон календаря: с января текущего года по январь следующего года
CURRENT_YEAR = date.today().year
MIN_YEAR = CURRENT_YEAR
MIN_MONTH = 1
MAX_YEAR = CURRENT_YEAR + 1
MAX_MONTH = 1


async def _send_month_calendar(message_or_callback, year: int, month: int):
    """
    Рендер одного месяца календаря:
    - Дни с доступными слотами — цифрой.
    - Остальные дни — точкой "·".
    """
    available_dates = set(db.get_available_dates_for_month(year, month))
    kb = calendar_inline_kb(
        year=year,
        month=month,
        available_dates=available_dates,
        min_year=MIN_YEAR,
        min_month=MIN_MONTH,
        max_year=MAX_YEAR,
        max_month=MAX_MONTH,
    )
    text = "<b>Выберите дату для записи:</b>"

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_callback.message.edit_text(
            text, reply_markup=kb, parse_mode="HTML"
        )


async def start_booking_flow(message: Message):
    # Стартуем с текущего месяца, но навигация разрешена с января текущего года
    today = date.today()
    await _send_month_calendar(message, today.year, today.month)


@router.callback_query(F.data.startswith("cal:"))
async def switch_calendar_month(callback: CallbackQuery):
    """
    Обработчик навигации по месяцам календаря.
    callback.data: "cal:YYYY-MM:prev" или "cal:YYYY-MM:next"
    """
    _, ym, direction = callback.data.split(":")
    year, month = map(int, ym.split("-"))

    if direction == "prev":
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    elif direction == "next":
        month += 1
        if month == 13:
            month = 1
            year += 1

    # Ограничиваем диапазоном
    if (year < MIN_YEAR) or (year == MIN_YEAR and month < MIN_MONTH):
        await callback.answer()
        return
    if (year > MAX_YEAR) or (year == MAX_YEAR and month > MAX_MONTH):
        await callback.answer()
        return

    await _send_month_calendar(callback, year, month)
    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """
    Пустой обработчик для "служебных" кнопок календаря/точек.
    """
    await callback.answer()


@router.callback_query(F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    chosen_date = callback.data.split(":", 1)[1]
    times_raw = db.get_times_for_date_with_flags(chosen_date)

    if not times_raw:
        await callback.message.edit_text(
            f"На дату <b>{chosen_date}</b> нет доступных слотов.\nВыберите другую дату.",
            parse_mode="HTML",
        )
        await callback.answer()
        return

    # Преобразуем к формату (slot_id, "HH:MM", is_available)
    times = [(slot_id, t, is_available) for slot_id, t, is_available in times_raw]

    await state.update_data(chosen_date=chosen_date)
    await state.set_state(BookingStates.choosing_time)
    await callback.message.edit_text(
        f"<b>Дата:</b> {chosen_date}\n\nВыберите время:",
        reply_markup=times_inline_kb(times),
        parse_mode="HTML",
    )
    await callback.answer()

@router.callback_query(BookingStates.choosing_time, F.data.startswith("time:"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split(":", 1)[1])
    await state.update_data(slot_id=slot_id)
    await state.set_state(BookingStates.entering_name)
    await callback.message.edit_text(
        "Введите, пожалуйста, ваше <b>имя</b>:",
        parse_mode="HTML"
    )

@router.message(BookingStates.entering_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text.strip())
    await state.set_state(BookingStates.entering_phone)
    await message.answer("Теперь введите ваш <b>номер телефона</b>:", parse_mode="HTML")

@router.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    await state.update_data(client_phone=message.text.strip())
    data = await state.get_data()

    slot_info = get_slot_info(data["slot_id"])
    if not slot_info:
        await message.answer("К сожалению, выбранный слот больше недоступен. Попробуйте ещё раз.")
        await state.clear()
        return

    chosen_date, chosen_time = slot_info
    text = (
        "<b>Проверьте данные записи:</b>\n\n"
        f"Дата: <b>{chosen_date}</b>\n"
        f"Время: <b>{chosen_time}</b>\n"
        f"Имя: <b>{data['client_name']}</b>\n"
        f"Телефон: <b>{data['client_phone']}</b>\n\n"
        "Подтвердить запись?"
    )
    await state.set_state(BookingStates.confirm)
    await message.answer(text, reply_markup=confirm_booking_kb(), parse_mode="HTML")

def get_slot_info(slot_id: int):
    from database.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT slot_date, slot_time FROM slots WHERE id = ?", (slot_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return row["slot_date"], row["slot_time"]

def calc_reminder_datetime(slot_date: str, slot_time: str):
    visit_dt = datetime.fromisoformat(f"{slot_date}T{slot_time}:00")
    reminder_dt = visit_dt - timedelta(hours=24)
    if reminder_dt <= datetime.utcnow():
        return None
    return reminder_dt

@router.callback_query(BookingStates.confirm, F.data.startswith("confirm:"))
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot):
    decision = callback.data.split(":", 1)[1]
    if decision == "no":
        await callback.message.edit_text("Запись отменена.", parse_mode="HTML")
        # Показываем главное меню после отмены, чтобы продолжить работу с ботом
        is_admin = callback.from_user.id == settings.ADMIN_ID
        await callback.message.answer(
            "Вы можете выбрать дальнейшее действие через меню ниже.",
            reply_markup=main_menu_kb(is_admin=is_admin),
            parse_mode="HTML",
        )
        await state.clear()
        return

    data = await state.get_data()
    slot_info = get_slot_info(data["slot_id"])
    if not slot_info:
        await callback.message.edit_text("Слот больше недоступен. Попробуйте записаться снова.", parse_mode="HTML")
        await state.clear()
        return

    chosen_date, chosen_time = slot_info
    reminder_dt = calc_reminder_datetime(chosen_date, chosen_time)

    booking_id = db.book_slot(
        tg_id=callback.from_user.id,
        slot_id=data["slot_id"],
        client_name=data["client_name"],
        client_phone=data["client_phone"],
        reminder_at=reminder_dt
    )

    if not booking_id:
        await callback.message.edit_text("Не удалось забронировать слот (он уже занят). Попробуйте снова.", parse_mode="HTML")
        await state.clear()
        return

    from scheduler import schedule_reminder_for_booking
    if reminder_dt:
        await schedule_reminder_for_booking(booking_id, reminder_dt, bot)

    await state.clear()

    user_text = (
        "✅ <b>Запись подтверждена!</b>\n\n"
        f"Дата: <b>{chosen_date}</b>\n"
        f"Время: <b>{chosen_time}</b>\n"
        f"Имя: <b>{data['client_name']}</b>\n"
        f"Телефон: <b>{data['client_phone']}</b>\n\n"
        "Ждём вас 💅\n\n"
        "Можете продолжить пользоваться ботом через меню ниже."
    )
    await callback.message.edit_text(user_text, parse_mode="HTML")

    # Отдельным сообщением отправляем главное меню (ReplyKeyboardMarkup нельзя использовать в edit_message_text)
    is_admin = callback.from_user.id == settings.ADMIN_ID
    await callback.message.answer(
        "Вы можете выбрать дальнейшее действие через меню ниже.",
        reply_markup=main_menu_kb(is_admin=is_admin),
        parse_mode="HTML",
    )

    admin_text = (
        "<b>Новая запись:</b>\n\n"
        f"ID записи: <code>{booking_id}</code>\n"
        f"Дата: <b>{chosen_date}</b>\n"
        f"Время: <b>{chosen_time}</b>\n"
        f"Имя: <b>{data['client_name']}</b>\n"
        f"Телефон: <b>{data['client_phone']}</b>\n"
        f"TG ID: <code>{callback.from_user.id}</code>"
    )
    await bot.send_message(settings.ADMIN_ID, admin_text, parse_mode="HTML")

    channel_text = (
        "<b>Новая запись в расписании:</b>\n\n"
        f"Дата: <b>{chosen_date}</b>\n"
        f"Время: <b>{chosen_time}</b>\n"
        f"Клиент: <b>{data['client_name']}</b>"
    )
    schedule_msg_id = None
    try:
        msg = await bot.send_message(
            settings.SCHEDULE_CHANNEL_ID, channel_text, parse_mode="HTML"
        )
        schedule_msg_id = msg.message_id
    except TelegramBadRequest:
        # Если канал расписания не настроен или недоступен, не падаем
        schedule_msg_id = None

    if schedule_msg_id is not None:
        # Сохраняем ID сообщения канала в бронирование
        from database.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE bookings SET schedule_msg_id = ? WHERE id = ?",
                (schedule_msg_id, booking_id),
            )
            conn.commit()
        finally:
            conn.close()