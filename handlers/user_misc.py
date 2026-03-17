# handlers/user_misc.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards.subscription import portfolio_kb
from keyboards.booking import cancel_bookings_kb
from config import settings

router = Router()


@router.message(F.text == "Отменить запись")
async def cancel_my_booking(message: Message):
    bookings = db.get_user_active_bookings(message.from_user.id)
    if not bookings:
        await message.answer("У вас нет активных записей.", parse_mode="HTML")
        return

    text_lines = ["<b>Выберите запись для отмены:</b>"]
    for booking_id, slot_date, slot_time in bookings:
        text_lines.append(
            f"ID <code>{booking_id}</code> — {slot_date} {slot_time}"
        )

    await message.answer(
        "\n".join(text_lines),
        reply_markup=cancel_bookings_kb(bookings),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cancel_my:"))
async def cancel_my_booking_choice(callback: CallbackQuery, bot):
    booking_id = int(callback.data.split(":", 1)[1])
    ok, schedule_msg_id = db.cancel_booking_by_id(booking_id)
    if not ok:
        await callback.answer(
            "Эта запись уже была отменена или не найдена.", show_alert=True
        )
        return

    await callback.answer()

    # Пытаемся удалить сообщение в канале расписания, если оно было
    if schedule_msg_id is not None:
        from aiogram.exceptions import TelegramBadRequest
        try:
            await bot.delete_message(
                chat_id=settings.SCHEDULE_CHANNEL_ID,
                message_id=schedule_msg_id,
            )
        except TelegramBadRequest:
            pass
    await callback.message.edit_text(
        f"❌ Запись с ID <code>{booking_id}</code> отменена, слот снова доступен.",
        parse_mode="HTML",
    )

@router.message(F.text == "Прайсы")
async def show_prices(message: Message):
    text = (
        "<b>Прайс-лист:</b>\n\n"
        "Френч — <b>1000₽</b>\n"
        "Квадрат — <b>500₽</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "Портфолио")
async def show_portfolio(message: Message):
    await message.answer(
        "<b>Портфолио работ:</b>",
        reply_markup=portfolio_kb(),
        parse_mode="HTML"
    )