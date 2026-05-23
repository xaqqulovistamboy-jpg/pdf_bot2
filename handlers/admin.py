import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import Database
from config import ADMIN_IDS
from states.states import AdminState
from keyboards.keyboards import get_admin_keyboard

router = Router()

def is_user_admin(user_id: int, user_settings: dict) -> bool:
    """Helper to check if user is an admin via environment variable or database"""
    return user_id in ADMIN_IDS or user_settings.get("is_admin", False)

@router.message(Command("admin"))
async def cmd_admin(message: Message, user_settings: dict):
    user_id = message.from_user.id
    if not is_user_admin(user_id, user_settings):
        await message.answer("❌ Kechirasiz, bu buyruq faqat bot adminlari uchun.")
        return

    await message.answer(
        "💼 *Admin Panelga xush kelibsiz!*\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery, db: Database, user_settings: dict):
    user_id = callback.from_user.id
    if not is_user_admin(user_id, user_settings):
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    stats = await db.get_stats()
    
    stats_text = (
        "📊 *Bot statistikasi:*\n\n"
        f"👤 *Jami foydalanuvchilar:* {stats['total_users']} ta\n"
        f"📅 *Oylik faol foydalanuvchilar (MAU):* {stats['monthly_active_users']} ta\n"
        f"📄 *PDF yaratishlar (Conversions):* {stats['total_conversions']} marta\n"
        f"🖼 *Qayta ishlangan jami fayllar:* {stats['total_files_processed']} ta\n"
    )
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, state: FSMContext, user_settings: dict):
    user_id = callback.from_user.id
    if not is_user_admin(user_id, user_settings):
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.answer(
        "📣 *Reklama Tarqatish:*\n\n"
        "Iltimos, barcha foydalanuvchilarga tarqatmoqchi bo'lgan xabaringizni yuboring.\n"
        "Bu matn, rasm, video, klaviatura yoki har qanday formatda bo'lishi mumkin.\n\n"
        "Amaliyotni bekor qilish uchun /cancel deb yozing.",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def callback_admin_close(callback: CallbackQuery, user_settings: dict):
    user_id = callback.from_user.id
    if not is_user_admin(user_id, user_settings):
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return
        
    await callback.message.delete()
    await callback.answer()

@router.message(AdminState.waiting_for_broadcast)
async def process_admin_broadcast(message: Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    
    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Reklama tarqatish bekor qilindi.")
        return

    progress_msg = await message.answer("⏳ Reklama tarqatilmoqda, iltimos kuting...")
    
    all_users = await db.get_all_users()
    
    success = 0
    fail = 0
    
    for uid in all_users:
        # Don't send to admin themselves (or we can if we want to test)
        try:
            # We copy the exact message sent by admin (keeps text, image, format, custom keyboards, etc.)
            await message.copy_to(chat_id=uid)
            success += 1
            # Rate limiting to prevent Telegram API spam limits
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1

    await progress_msg.edit_text(
        "📢 *Reklama tarqatish yakunlandi:*\n\n"
        f"✅ Muvaffaqiyatli yuborildi: {success} ta foydalanuvchi\n"
        f"❌ Yuborilmadi (bloklangan): {fail} ta foydalanuvchi",
        parse_mode="Markdown"
    )
    await state.clear()
