from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "👋 Salom! Men rasmlarni PDF faylga aylantirib beruvchi botman.\n\n"
        "Menga bitta yoki bir nechta rasm yuboring, men ularni bitta PDF hujjatga aylantirib beraman. 📄\n"
        "Sifatni yo'qotmaslik uchun rasmlarni 'Fayl' sifatida ham yuborishingiz mumkin."
    )
    await message.answer(text)
