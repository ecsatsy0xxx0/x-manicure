# states/booking_states.py
from aiogram.fsm.state import StatesGroup, State

class BookingStates(StatesGroup):
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirm = State()