# handlers/subscription.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

from config import settings
from keyboards.subscription import subscription_kb

router = Router()


async def check_subscription(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(settings.CHANNEL_ID, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,  # раньше было OWNER
        )
    except TelegramBadRequest:
        return False


@router.message(F.text == "Записаться")
async def start_booking_with_sub_check(message: Message, bot):
    if not await check_subscription(message.from_user.id, bot):
        text = (
            "Для записи необходимо подписаться на канал.\n\n"
            "После подписки нажмите кнопку <b>Проверить подписку</b>."
        )
        await message.answer(text, reply_markup=subscription_kb(), parse_mode="HTML")
        return

    from .user_booking import start_booking_flow
    await start_booking_flow(message)


@router.callback_query(F.data == "sub:check")
async def callback_check_subscription(callback: CallbackQuery, bot):
    if await check_subscription(callback.from_user.id, bot):
        await callback.message.edit_text(
            "Подписка подтверждена! Теперь вы можете записаться через кнопку <b>Записаться</b>.",
            parse_mode="HTML",
        )
    else:
        await callback.answer(
            "Подписка не найдена. Подпишитесь и попробуйте снова.",
            show_alert=True,
        )