# keyboards/booking.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Tuple, Set
from calendar import monthrange
from datetime import date


def calendar_inline_kb(
    year: int,
    month: int,
    available_dates: Set[str],
    min_year: int,
    min_month: int,
    max_year: int,
    max_month: int,
) -> InlineKeyboardMarkup:
    """
    Календарь на один месяц.
    - Дни с доступными слотами показываются цифрой (1–31) и доступны для нажатия.
    - Все остальные дни показываются точкой "·" и недоступны (callback_data = "ignore").
    - Навигация по месяцам — кнопки ◀ и ▶.
    """
    kb: List[List[InlineKeyboardButton]] = []

    # Шапка с названием месяца и годом
    month_name = date(year, month, 1).strftime("%B %Y")
    kb.append(
        [
            InlineKeyboardButton(text=month_name, callback_data="ignore"),
        ]
    )

    # Дни недели
    kb.append(
        [
            InlineKeyboardButton(text="Пн", callback_data="ignore"),
            InlineKeyboardButton(text="Вт", callback_data="ignore"),
            InlineKeyboardButton(text="Ср", callback_data="ignore"),
            InlineKeyboardButton(text="Чт", callback_data="ignore"),
            InlineKeyboardButton(text="Пт", callback_data="ignore"),
            InlineKeyboardButton(text="Сб", callback_data="ignore"),
            InlineKeyboardButton(text="Вс", callback_data="ignore"),
        ]
    )

    first_weekday, days_in_month = monthrange(year, month)  # first_weekday: 0=Пн
    # Сдвиг: сколько пустых ячеек до первого числа
    shift = first_weekday

    row: List[InlineKeyboardButton] = []
    # Пустые клетки до первого числа
    for _ in range(shift):
        row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    # Сами дни
    for day in range(1, days_in_month + 1):
        iso_date = f"{year:04d}-{month:02d}-{day:02d}"
        if iso_date in available_dates:
            text = str(day)
            cb = f"date:{iso_date}"
        else:
            text = "·"
            cb = "ignore"

        row.append(InlineKeyboardButton(text=text, callback_data=cb))
        if len(row) == 7:
            kb.append(row)
            row = []

    # Хвост строки, если остались элементы
    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
        kb.append(row)

    # Навигация по месяцам
    nav_row: List[InlineKeyboardButton] = []

    # prev
    prev_year, prev_month = year, month - 1
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    if (prev_year > min_year) or (prev_year == min_year and prev_month >= min_month):
        nav_row.append(
            InlineKeyboardButton(
                text="◀",
                callback_data=f"cal:{year:04d}-{month:02d}:prev",
            )
        )
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    # next
    next_year, next_month = year, month + 1
    if next_month == 12 + 1:
        next_month = 1
        next_year += 1
    if (next_year < max_year) or (next_year == max_year and next_month <= max_month):
        nav_row.append(
            InlineKeyboardButton(
                text="▶",
                callback_data=f"cal:{year:04d}-{month:02d}:next",
            )
        )
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    kb.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=kb)


def times_inline_kb(times: List[Tuple[int, str, bool]]) -> InlineKeyboardMarkup:
    """
    times: список (slot_id, "HH:MM", is_available).
    - Свободные слоты показываются временем и доступны.
    - Занятые показываются точкой "·" и недоступны (callback_data = "ignore").
    """
    kb: List[List[InlineKeyboardButton]] = []
    for slot_id, t, is_available in times:
        if is_available:
            text = t
            cb = f"time:{slot_id}"
        else:
            text = "·"
            cb = "ignore"
        kb.append([InlineKeyboardButton(text=text, callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def confirm_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="confirm:no"),
            ]
        ]
    )


def cancel_bookings_kb(bookings: List[Tuple[int, str, str]]) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора, какую запись отменить.
    bookings: список (booking_id, slot_date, slot_time)
    """
    kb: List[List[InlineKeyboardButton]] = []
    for booking_id, slot_date, slot_time in bookings:
        text = f"{slot_date} {slot_time} (ID {booking_id})"
        cb = f"cancel_my:{booking_id}"
        kb.append([InlineKeyboardButton(text=text, callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=kb)