# handlers/common.py
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import settings
from keyboards.main_menu import main_menu_kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    is_admin = message.from_user.id == settings.ADMIN_ID
    text = (
        "<b>Добро пожаловать!</b>\n\n"
        "Это бот для записи к мастеру по маникюру.\n"
        "Используйте меню ниже, чтобы записаться, отменить запись, "
        "посмотреть прайсы или портфолио 💅"
    )
    await message.answer(text, reply_markup=main_menu_kb(is_admin=is_admin), parse_mode="HTML")