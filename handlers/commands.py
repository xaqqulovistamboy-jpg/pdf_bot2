from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import Database
from keyboards.keyboards import get_main_keyboard, get_settings_keyboard
from states.states import PdfState

router = Router()

START_TEXT = (
    "Assalomu alaykum 👋\n"
    "Menga rasmlar yuboring, men ularni PDF faylga aylantiraman 📄"
)

HELP_TEXT = (
    "📖 *Botdan foydalanish bo'yicha yordam*\n\n"
    "1️⃣ *PDF yaratish*:\n"
    "• Botga bir nechta rasm yuboring (alohida yoki media guruh sifatida).\n"
    "• Yuborib bo'lgach, *📄 PDF ni yaratish* tugmasini bosing.\n"
    "• PDF uchun nom kiriting va tayyor faylni yuklab oling.\n\n"
    "2️⃣ *ZIP fayldan PDF yaratish*:\n"
    "• Ichida rasmlar bo'lgan `.zip` arxivini yuboring.\n"
    "• Bot rasmlarni avtomatik ajratib olib, PDF yaratadi.\n\n"
    "3️⃣ *PDF-larni birlashtirish (Merge)*:\n"
    "• /merge buyrug'ini yuboring va botga PDF fayllarni birin-ketin jo'nating.\n"
    "• Tayyor bo'lgach *📄 Birlashtirish* tugmasini bosing.\n\n"
    "4️⃣ *PDF-ni ajratish (Split)*:\n"
    "• /split buyrug'ini yuboring va PDF fayl yuboring.\n"
    "• Bot uni sahifalarga ajratib, ZIP arxivda yuboradi.\n\n"
    "⚙️ Sozlamalar menyusi orqali PDF sifati va watermark matnini sozlashingiz mumkin."
)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(START_TEXT, reply_markup=get_main_keyboard())

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="Markdown")

@router.message(Command("settings"))
async def cmd_settings(message: Message, db: Database, user_settings: dict):
    quality = user_settings.get("pdf_quality", "medium")
    watermark = user_settings.get("watermark_text")
    await message.answer(
        "⚙️ *Bot sozlamalari:*\n\n"
        "Bu yerda PDF sifati va sahifalarga qo'yiladigan watermark matnini sozlashingiz mumkin.",
        reply_markup=get_settings_keyboard(quality, watermark),
        parse_mode="Markdown"
    )

# --- CALLBACK HANDLERS ---

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(START_TEXT, reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "how_to_send")
async def callback_how_to_send(callback: CallbackQuery):
    await callback.message.answer(
        "📥 *Qanday qilib rasm yuboriladi?*\n\n"
        "• Shunchaki chatga bir yoki bir nechta rasmlarni oddiy rasm yoki sifatini yo'qotmaslik uchun *Hujjat (File)* ko'rinishida yuboring.\n"
        "• Rasmlar yuborilgandan so'ng, sizga tasdiqlash xabari va PDF yaratish tugmasi ko'rsatiladi.",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "help_info")
async def callback_help_info(callback: CallbackQuery):
    await callback.message.edit_text(HELP_TEXT, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "settings_menu")
async def callback_settings_menu(callback: CallbackQuery, user_settings: dict):
    quality = user_settings.get("pdf_quality", "medium")
    watermark = user_settings.get("watermark_text")
    
    await callback.message.edit_text(
        "⚙️ *Bot sozlamalari:*\n\n"
        "Bu yerda PDF sifati va sahifalarga qo'yiladigan watermark matnini sozlashingiz mumkin.",
        reply_markup=get_settings_keyboard(quality, watermark),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- QUALITY SETTING CALLBACKS ---

@router.callback_query(F.data.startswith("set_quality_"))
async def callback_set_quality(callback: CallbackQuery, db: Database, user_settings: dict):
    new_quality = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    
    await db.update_user_settings(user_id, pdf_quality=new_quality)
    user_settings["pdf_quality"] = new_quality
    
    # Reload settings keyboard
    quality = new_quality
    watermark = user_settings.get("watermark_text")
    
    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(quality, watermark)
    )
    await callback.answer(f"Sifat '{new_quality}' qilib belgilandi! ✅")

# --- WATERMARK TOGGLE / SET CALLBACKS ---

@router.callback_query(F.data == "toggle_watermark")
async def callback_toggle_watermark(callback: CallbackQuery, state: FSMContext, db: Database, user_settings: dict):
    user_id = callback.from_user.id
    watermark = user_settings.get("watermark_text")
    
    if watermark:
        # If already exists, toggle off
        await db.update_user_settings(user_id, watermark_text="")
        user_settings["watermark_text"] = None
        quality = user_settings.get("pdf_quality", "medium")
        
        await callback.message.edit_reply_markup(
            reply_markup=get_settings_keyboard(quality, None)
        )
        await callback.answer("Watermark o'chirildi! ❌")
    else:
        # Toggle on -> Ask for text
        await state.set_state(PdfState.waiting_for_watermark)
        await callback.message.answer(
            "✏️ Iltimos, watermark matnini yozib yuboring (masalan: @mening_kanalim):\n"
            "Chiqish uchun /cancel deb yozing."
        )
        await callback.answer()

@router.message(PdfState.waiting_for_watermark)
async def process_set_watermark(message: Message, state: FSMContext, db: Database):
    watermark_text = message.text.strip()
    
    if watermark_text.lower() == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi.")
        return
        
    user_id = message.from_user.id
    await db.update_user_settings(user_id, watermark_text=watermark_text)
    
    # Fetch updated settings
    settings = await db.get_user_settings(user_id)
    quality = settings.get("pdf_quality", "medium")
    
    await message.answer(
        f"✅ Watermark matni muvaffaqiyatli saqlandi: '{watermark_text}'",
        reply_markup=get_settings_keyboard(quality, watermark_text)
    )
    await state.clear()
