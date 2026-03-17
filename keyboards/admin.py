# keyboards/admin.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить рабочий день/слоты", callback_data="admin:add_day")],
        [InlineKeyboardButton(text="Закрыть день", callback_data="admin:close_day")],
        [InlineKeyboardButton(text="Посмотреть расписание", callback_data="admin:view_schedule")],
        [InlineKeyboardButton(text="Отменить запись по ID", callback_data="admin:cancel_booking")],
    ])