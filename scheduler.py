# scheduler.py
from datetime import datetime
from typing import Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from aiogram import Bot

from database import db

scheduler = AsyncIOScheduler()
_jobs_by_booking: Dict[int, str] = {}

async def reminder_job(booking_id: int, bot: Bot):
    info = db.get_booking_for_reminder(booking_id)
    if not info:
        return
    booking_id, tg_id, slot_date, slot_time, client_name = info
    text = (
        f"Напоминаем, что вы записаны на наращивание ресниц завтра в {slot_time}.\n"
        "Ждём вас ❤️"
    )
    await bot.send_message(tg_id, text)
    db.delete_reminder(booking_id)
    if booking_id in _jobs_by_booking:
        _jobs_by_booking.pop(booking_id, None)

async def schedule_reminder_for_booking(booking_id: int, remind_at: datetime, bot: Bot):
    if booking_id in _jobs_by_booking:
        job_id = _jobs_by_booking[booking_id]
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
    job = scheduler.add_job(
        reminder_job,
        trigger=DateTrigger(run_date=remind_at),
        args=[booking_id, bot],
        id=f"booking_{booking_id}",
        replace_existing=True
    )
    _jobs_by_booking[booking_id] = job.id

async def restore_jobs(bot: Bot):
    future = db.get_future_reminders()
    for booking_id, remind_at in future:
        if remind_at <= datetime.utcnow():
            continue
        await schedule_reminder_for_booking(booking_id, remind_at, bot)