# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, date, time

from config import settings
from states.admin_states import AdminStates
from keyboards.admin import admin_menu_kb
from database import db
from aiogram.exceptions import TelegramBadRequest

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_ID

@router.message(F.text == "Админ-панель")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("<b>Админ-панель</b>", reply_markup=admin_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin:add_day")
async def admin_add_day(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.choosing_day_for_add)
    await callback.message.edit_text(
        "Введите дату рабочего дня в формате <b>ГГГГ-ММ-ДД</b> (например, 2026-03-20):",
        parse_mode="HTML"
    )

@router.message(AdminStates.choosing_day_for_add)
async def admin_enter_day_for_add(message: Message, state: FSMContext):
    try:
        d = date.fromisoformat(message.text.strip())
    except ValueError:
        await message.answer("Неверный формат даты. Пример: 2026-03-20", parse_mode="HTML")
        return

    await state.update_data(add_day=d.isoformat())
    await state.set_state(AdminStates.adding_time_to_day)
    await message.answer(
        "Введите список временных слотов через запятую в формате ЧЧ:ММ.\n"
        "Например: <code>10:00, 12:00, 15:30</code>",
        parse_mode="HTML"
    )

@router.message(AdminStates.adding_time_to_day)
async def admin_add_times(message: Message, state: FSMContext):
    data = await state.get_data()
    d = date.fromisoformat(data["add_day"])
    times_str = message.text.replace(" ", "")
    parts = [p for p in times_str.split(",") if p]
    created = 0
    for part in parts:
        try:
            t = datetime.strptime(part, "%H:%M").time()
        except ValueError:
            continue
        db.create_slot(d, t)
        created += 1

    await state.clear()
    await message.answer(
        f"Добавлено {created} слотов на дату <b>{d.isoformat()}</b>.",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin:close_day")
async def admin_close_day(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.choosing_day_for_close)
    await callback.message.edit_text(
        "Введите дату, которую нужно полностью закрыть, в формате <b>ГГГГ-ММ-ДД</b>:",
        parse_mode="HTML"
    )

@router.message(AdminStates.choosing_day_for_close)
async def admin_close_day_enter(message: Message, state: FSMContext):
    try:
        d = date.fromisoformat(message.text.strip())
    except ValueError:
        await message.answer("Неверный формат даты. Пример: 2026-03-20", parse_mode="HTML")
        return
    db.set_day_closed(d)
    await state.clear()
    await message.answer(f"День <b>{d.isoformat()}</b> закрыт для записи.", parse_mode="HTML")

@router.callback_query(F.data == "admin:view_schedule")
async def admin_view_schedule(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.choosing_day_for_view)
    await callback.message.edit_text(
        "Введите дату для просмотра расписания в формате <b>ГГГГ-ММ-ДД</b>:",
        parse_mode="HTML"
    )

@router.message(AdminStates.choosing_day_for_view)
async def admin_show_schedule(message: Message, state: FSMContext):
    try:
        d = date.fromisoformat(message.text.strip())
    except ValueError:
        await message.answer("Неверный формат даты. Пример: 2026-03-20", parse_mode="HTML")
        return

    rows = db.get_schedule_for_date(d.isoformat())
    if not rows:
        await message.answer("На эту дату слотов нет.", parse_mode="HTML")
        await state.clear()
        return

    lines = [f"<b>Расписание на {d.isoformat()}:</b>"]
    for r in rows:
        status = "Свободно" if r["is_available"] == 1 else "Занято"
        if r["booking_id"]:
            line = (
                f"{r['slot_time']} — <b>{status}</b> "
                f"(ID записи: <code>{r['booking_id']}</code>, "
                f"{r['client_name']}, {r['client_phone']})"
            )
        else:
            line = f"{r['slot_time']} — <b>{status}</b>"
        lines.append(line)

    await state.clear()
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.callback_query(F.data == "admin:cancel_booking")
async def admin_cancel_booking_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.cancelling_booking)
    await callback.message.edit_text(
        "Введите ID записи, которую нужно отменить:",
        parse_mode="HTML"
    )

@router.message(AdminStates.cancelling_booking)
async def admin_cancel_booking_finish(message: Message, state: FSMContext, bot):
    try:
        booking_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID должен быть числом.", parse_mode="HTML")
        return

    ok, schedule_msg_id = db.cancel_booking_by_id(booking_id)

    # Пытаемся удалить сообщение в канале расписания, если оно есть
    if ok and schedule_msg_id is not None:
        try:
            await bot.delete_message(
                chat_id=settings.SCHEDULE_CHANNEL_ID,
                message_id=schedule_msg_id,
            )
        except TelegramBadRequest:
            pass

    await state.clear()
    if ok:
        await message.answer(
            f"Запись с ID <code>{booking_id}</code> отменена, слот снова свободен.",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "Активная запись с таким ID не найдена.", parse_mode="HTML"
        )