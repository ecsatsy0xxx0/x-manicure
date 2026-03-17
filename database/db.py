# database/db.py
import sqlite3
from typing import List, Optional, Tuple
from datetime import datetime, date, time
from calendar import monthrange

from config import settings


def get_connection():
    # Увеличиваем таймаут, чтобы снизить вероятность ошибок "database is locked"
    conn = sqlite3.connect(settings.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Пользователи
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE NOT NULL,
        name TEXT,
        phone TEXT
    );
    """
    )

    # Временные слоты
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS slots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_date TEXT NOT NULL,     -- YYYY-MM-DD
        slot_time TEXT NOT NULL,     -- HH:MM
        is_available INTEGER NOT NULL DEFAULT 1,
        UNIQUE(slot_date, slot_time)
    );
    """
    )

    # Записи
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        slot_id INTEGER NOT NULL,
        client_name TEXT NOT NULL,
        client_phone TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',  -- active/cancelled
        created_at TEXT NOT NULL,
        reminder_at TEXT,                       -- ISO datetime для напоминания
        schedule_msg_id INTEGER,                -- сообщение в канале расписания
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(slot_id) REFERENCES slots(id)
    );
    """
    )

    # Таблица для восстановления напоминаний
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        remind_at TEXT NOT NULL,   -- ISO datetime
        FOREIGN KEY(booking_id) REFERENCES bookings(id)
    );
    """
    )

    conn.commit()
    conn.close()

    # На всякий случай пытаемся добавить столбец schedule_msg_id, если базы уже существует
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("ALTER TABLE bookings ADD COLUMN schedule_msg_id INTEGER")
        conn.commit()
    except Exception:
        # Столбец уже существует или другая не критичная ошибка схемы
        pass
    finally:
        conn.close()


def get_or_create_user(tg_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    if row:
        user_id = row["id"]
    else:
        cur.execute("INSERT INTO users (tg_id) VALUES (?)", (tg_id,))
        user_id = cur.lastrowid
        conn.commit()
    conn.close()
    return user_id


def user_has_active_booking(tg_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.id
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        WHERE u.tg_id = ? AND b.status = 'active'
    """,
        (tg_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def create_slot(slot_date: date, slot_time: time):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO slots (slot_date, slot_time, is_available)
        VALUES (?, ?, 1)
    """,
        (slot_date.isoformat(), slot_time.strftime("%H:%M")),
    )
    conn.commit()
    conn.close()


def set_day_closed(slot_date: date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE slots
        SET is_available = 0
        WHERE slot_date = ?
    """,
        (slot_date.isoformat(),),
    )
    conn.commit()
    conn.close()


def get_available_dates(limit_days: int = 30) -> List[str]:
    """
    Старый метод (с ограничением по дням), оставлен для совместимости.
    Сейчас для календаря по месяцам используется get_available_dates_for_month.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT slot_date
        FROM slots
        WHERE is_available = 1
        ORDER BY slot_date
        LIMIT ?
    """,
        (limit_days,),
    )
    rows = cur.fetchall()
    conn.close()
    return [r["slot_date"] for r in rows]


def get_available_dates_for_month(year: int, month: int) -> List[str]:
    """
    Возвращает даты (YYYY-MM-DD) выбранного месяца, в которых есть хотя бы один свободный слот.
    Используется для построения календаря.
    """
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT slot_date
        FROM slots
        WHERE is_available = 1
          AND slot_date BETWEEN ? AND ?
        ORDER BY slot_date
        """,
        (first_day.isoformat(), last_day.isoformat()),
    )
    rows = cur.fetchall()
    conn.close()
    return [r["slot_date"] for r in rows]


def get_available_times_for_date(slot_date: str) -> List[Tuple[int, str]]:
    """
    Старый метод, возвращающий только свободные слоты.
    Сейчас для календаря времени используется get_times_for_date_with_flags.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, slot_time
        FROM slots
        WHERE slot_date = ? AND is_available = 1
        ORDER BY slot_time
    """,
        (slot_date,),
    )
    rows = cur.fetchall()
    conn.close()
    return [(r["id"], r["slot_time"]) for r in rows]


def get_times_for_date_with_flags(
    slot_date: str,
) -> List[Tuple[Optional[int], str, bool]]:
    """
    Возвращает список временных слотов для даты:
    (slot_id или None, время 'HH:MM', is_available: bool).
    Если в базе нет ни одного слота на дату, возвращается пустой список.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, slot_time, is_available
        FROM slots
        WHERE slot_date = ?
        ORDER BY slot_time
        """,
        (slot_date,),
    )
    rows = cur.fetchall()
    conn.close()
    result: List[Tuple[Optional[int], str, bool]] = []
    for r in rows:
        result.append((r["id"], r["slot_time"], bool(r["is_available"])))
    return result


def book_slot(
    tg_id: int,
    slot_id: int,
    client_name: str,
    client_phone: str,
    reminder_at: Optional[datetime],
) -> Optional[int]:
    """
    Бронируем слот в одной транзакции, используя одно соединение.
    Это уменьшает вероятность "database is locked".
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        # Проверяем слот
        cur.execute(
            "SELECT id, is_available, slot_date, slot_time FROM slots WHERE id = ?",
            (slot_id,),
        )
        slot_row = cur.fetchone()
        if not slot_row or slot_row["is_available"] == 0:
            conn.rollback()
            return None

        # Получаем или создаём пользователя в рамках той же транзакции
        cur.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = cur.fetchone()
        if row:
            user_id = row["id"]
        else:
            cur.execute("INSERT INTO users (tg_id) VALUES (?)", (tg_id,))
            user_id = cur.lastrowid

        # Создаём бронирование
        cur.execute(
            """
            INSERT INTO bookings (user_id, slot_id, client_name, client_phone, status, created_at, reminder_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                user_id,
                slot_id,
                client_name,
                client_phone,
                datetime.utcnow().isoformat(),
                reminder_at.isoformat() if reminder_at else None,
            ),
        )
        booking_id = cur.lastrowid

        # Помечаем слот как занятый
        cur.execute("UPDATE slots SET is_available = 0 WHERE id = ?", (slot_id,))

        # Напоминание, если нужно
        if reminder_at:
            cur.execute(
                """
                INSERT INTO reminders (booking_id, remind_at)
                VALUES (?, ?)
                """,
                (booking_id, reminder_at.isoformat()),
            )

        conn.commit()
        return booking_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancel_booking_by_user(tg_id: int) -> Optional[Tuple[int, str, str]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.id AS booking_id, s.id AS slot_id, s.slot_date, s.slot_time
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        JOIN slots s ON s.id = b.slot_id
        WHERE u.tg_id = ? AND b.status = 'active'
        ORDER BY b.created_at DESC
        LIMIT 1
    """,
        (tg_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    try:
        cur.execute("BEGIN")
        cur.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?",
            (row["booking_id"],),
        )
        cur.execute(
            "UPDATE slots SET is_available = 1 WHERE id = ?", (row["slot_id"],)
        )
        cur.execute(
            "DELETE FROM reminders WHERE booking_id = ?", (row["booking_id"],)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return row["booking_id"], row["slot_date"], row["slot_time"]


def get_user_active_bookings(tg_id: int) -> List[Tuple[int, str, str]]:
    """
    Возвращает список активных записей пользователя:
    (booking_id, slot_date, slot_time), отсортированных по дате/времени.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.id AS booking_id, s.slot_date, s.slot_time
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        JOIN slots s ON s.id = b.slot_id
        WHERE u.tg_id = ? AND b.status = 'active'
        ORDER BY s.slot_date, s.slot_time
        """,
        (tg_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [(r["booking_id"], r["slot_date"], r["slot_time"]) for r in rows]


def cancel_booking_by_id(booking_id: int) -> Tuple[bool, Optional[int]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.id AS booking_id, s.id AS slot_id, b.schedule_msg_id
        FROM bookings b
        JOIN slots s ON s.id = b.slot_id
        WHERE b.id = ? AND b.status = 'active'
    """,
        (booking_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, None
    try:
        cur.execute("BEGIN")
        cur.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )
        cur.execute(
            "UPDATE slots SET is_available = 1 WHERE id = ?", (row["slot_id"],)
        )
        cur.execute(
            "DELETE FROM reminders WHERE booking_id = ?", (booking_id,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return True, row["schedule_msg_id"]


def get_schedule_for_date(slot_date: str) -> List[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.slot_time, s.is_available,
               b.id AS booking_id, b.client_name, b.client_phone, b.status
        FROM slots s
        LEFT JOIN bookings b ON b.slot_id = s.id AND b.status = 'active'
        WHERE s.slot_date = ?
        ORDER BY s.slot_time
    """,
        (slot_date,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_future_reminders() -> List[Tuple[int, datetime]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT booking_id, remind_at
        FROM reminders
    """
    )
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append((r["booking_id"], datetime.fromisoformat(r["remind_at"])))
    return result


def get_booking_for_reminder(
    booking_id: int,
) -> Optional[Tuple[int, int, str, str, str]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.id AS booking_id, u.tg_id, s.slot_date, s.slot_time, b.client_name
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        JOIN slots s ON s.id = b.slot_id
        WHERE b.id = ? AND b.status = 'active'
    """,
        (booking_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return (
        row["booking_id"],
        row["tg_id"],
        row["slot_date"],
        row["slot_time"],
        row["client_name"],
    )


def delete_reminder(booking_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM reminders WHERE booking_id = ?", (booking_id,))
    conn.commit()
    conn.close()