from aiogram.fsm.state import State, StatesGroup

class PdfState(StatesGroup):
    waiting_for_images = State()
    waiting_for_name = State()
    waiting_for_watermark = State()
    waiting_for_split_pdf = State()
    waiting_for_merge_pdfs = State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()
