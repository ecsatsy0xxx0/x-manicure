# manage_slots.py
from datetime import datetime, date, time, timedelta

from database import db


def create_test_slots():
    """
    Создаём тестовые свободные слоты на сегодня и завтра,
    чтобы можно было сразу записаться и потестировать бота.
    """

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Времена приёма (можешь поменять под себя)
    times = [
        time(hour=10, minute=0),
        time(hour=12, minute=0),
        time(hour=14, minute=0),
        time(hour=16, minute=0),
        time(hour=18, minute=0),
    ]

    # Инициализируем базу (на случай, если ещё не создана)
    db.init_db()

    # Слоты на сегодня
    for t in times:
        # если время ещё не прошло – создаём слот
        dt = datetime.combine(today, t)
        if dt > datetime.now():
            db.create_slot(today, t)

    # Слоты на завтра (все считаем актуальными)
    for t in times:
        db.create_slot(tomorrow, t)

    print("Тестовые слоты созданы на даты:", today.isoformat(), "и", tomorrow.isoformat())


if __name__ == "__main__":
    create_test_slots()