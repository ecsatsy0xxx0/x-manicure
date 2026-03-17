from aiogram.fsm.state import StatesGroup, State

class AdminStates(StatesGroup):
    choosing_day_for_add = State()
    adding_time_to_day = State()
    choosing_day_for_close = State()
    choosing_day_for_view = State()
    cancelling_booking = State()