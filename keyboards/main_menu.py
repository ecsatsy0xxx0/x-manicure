# keyboards/main_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Записаться")],
        [KeyboardButton(text="Отменить запись")],
        [KeyboardButton(text="Прайсы")],
        [KeyboardButton(text="Портфолио")],
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="Админ-панель")])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )