# config.py
from dataclasses import dataclass
import os

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8744698973:AAGzEgabHLfRNs0UB3nw58HhseVgixZdono")
    
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "8696584352"))

    # Канал с новостями/основной
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "@x_manicure")
    CHANNEL_LINK: str = os.getenv("CHANNEL_LINK", "https://t.me/x_manicure")

    # Канал с расписанием
    SCHEDULE_CHANNEL_ID: str = os.getenv("SCHEDULE_CHANNEL_ID", "@x_manicure_schedule_1")

    # Путь к базе данных
    DB_PATH: str = os.getenv("DB_PATH", "database/bot.db")

settings = Settings()