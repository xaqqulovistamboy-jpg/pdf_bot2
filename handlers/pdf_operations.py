import os
import uuid
import re
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.db import Database
from states.states import PdfState
from keyboards.keyboards import get_main_keyboard
from services.queue_service import QueueManager, UserSession
from services.pdf_service import merge_pdfs_async, split_pdf_async

router = Router()

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Using the same queue manager instance from images handler is not strictly required,
# but we need to reference the global queue_manager from handlers.images or import/create it.
# Let's import it from handlers.images to share the session state!
from handlers.images import queue_manager

def get_merge_keyboard() -> InlineKeyboardMarkup:
    """PDF Birlashtirish inline klaviatura"""
    keyboard = [
        [
            InlineKeyboardButton(text="📄 Birlashtirish", callback_data="do_merge"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_merge")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- MERGE COMMAND HANDLERS ---

@router.message(Command("merge"))
async def cmd_merge(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await queue_manager.clear_session(user_id)
    await state.set_state(PdfState.waiting_for_merge_pdfs)
    
    await message.answer(
        "📥 *PDF Birlashtirish (Merge) rejimi faollashdi.*\n\n"
        "Iltimos, birlashtirmoqchi bo'lgan PDF fayllaringizni birin-ketin yuboring.\n"
        "Hujjatlarni jo'natib bo'lgach, *📄 Birlashtirish* tugmasini bosing.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_merge")]]),
        parse_mode="Markdown"
    )

async def on_pdfs_batch_complete(session: UserSession, message: Message):
    total_pdfs = len(session.pdfs)
    text = (
        f"✅ {total_pdfs} ta PDF fayl qabul qilindi!\n\n"
        "Yana PDF yuborishingiz yoki pastdagi tugmani bosib ularni birlashtirishingiz mumkin."
    )
    try:
        if session.summary_message:
            await session.summary_message.edit_text(text, reply_markup=get_merge_keyboard())
        else:
            session.summary_message = await message.answer(text, reply_markup=get_merge_keyboard())
    except Exception:
        session.summary_message = await message.answer(text, reply_markup=get_merge_keyboard())

@router.message(PdfState.waiting_for_merge_pdfs, F.document)
async def handle_merge_document(message: Message, state: FSMContext):
    user_id = message.from_user.id
    doc = message.document
    
    if not doc.mime_type == "application/pdf" and not doc.file_name.lower().endswith(".pdf"):
        await message.answer("❌ Iltimos, faqat PDF formatidagi fayllarni yuboring.")
        return
        
    try:
        file = await message.bot.get_file(doc.file_id)
        unique_name = f"{uuid.uuid4().hex}.pdf"
        local_path = os.path.join(TEMP_DIR, unique_name)
        
        await message.bot.download_file(file.file_path, local_path)
        
        # Queue the PDF
        await queue_manager.add_pdf(
            user_id=user_id,
            file_path=local_path,
            message_id=message.message_id,
            trigger_message=message,
            callback=on_pdfs_batch_complete
        )
    except Exception as e:
        await message.answer(f"❌ PDF yuklashda xatolik: {e}")

@router.callback_query(F.data == "do_merge")
async def callback_do_merge(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    session = queue_manager.get_session(user_id)
    
    if len(session.pdfs) < 2:
        await callback.message.answer("❌ PDF birlashtirish uchun kamida 2 ta PDF fayl yuborishingiz kerak!")
        await callback.answer()
        return
        
    await state.set_state(PdfState.waiting_for_name)
    # Store that we are doing a merge operation
    await state.update_data(is_merge_op=True)
    
    await callback.message.answer("✏️ Birlashtiriladigan yangi PDF fayli uchun nom kiriting:")
    await callback.answer()

@router.callback_query(F.data == "cancel_merge")
async def callback_cancel_merge(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await queue_manager.clear_session(user_id)
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Birlashtirish amaliyoti bekor qilindi.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# --- SPLIT COMMAND HANDLERS ---

@router.message(Command("split"))
async def cmd_split(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(PdfState.waiting_for_split_pdf)
    
    await message.answer(
        "📤 *PDF Ajratish (Split) rejimi faollashdi.*\n\n"
        "Iltimos, sahifalarga ajratmoqchi bo'lgan PDF faylingizni yuboring.\n"
        "Chiqish uchun /cancel deb yozing.",
        parse_mode="Markdown"
    )

@router.message(PdfState.waiting_for_split_pdf, F.document)
async def handle_split_document(message: Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    doc = message.document
    
    if not doc.mime_type == "application/pdf" and not doc.file_name.lower().endswith(".pdf"):
        await message.answer("❌ Iltimos, faqat PDF formatidagi faylni yuboring.")
        return
        
    progress_msg = await message.answer("⏳ PDF yuklab olinmoqda va tahlil qilinmoqda...")
    
    try:
        file = await message.bot.get_file(doc.file_id)
        unique_name = f"{uuid.uuid4().hex}.pdf"
        local_path = os.path.join(TEMP_DIR, unique_name)
        
        await message.bot.download_file(file.file_path, local_path)
        
        await progress_msg.edit_text("⚙️ PDF sahifalarga ajratilib, arxivlanmoqda...")
        
        # Run async split
        zip_output_path = await split_pdf_async(local_path, TEMP_DIR)
        
        if zip_output_path and os.path.exists(zip_output_path):
            safe_name = doc.file_name.replace(".pdf", "_sahifalar.zip")
            zip_file = FSInputFile(zip_output_path, filename=safe_name)
            
            await message.answer_document(
                document=zip_file,
                caption="🎉 PDF faylingiz muvaffaqiyatli sahifalarga ajratildi!"
            )
            
            # Record stat in database
            file_size = os.path.getsize(zip_output_path)
            await db.add_conversion(
                user_id=user_id,
                file_type="split_pdf",
                files_count=1,
                file_size_bytes=file_size
            )
        else:
            await message.answer("❌ PDF ajratishda xatolik yuz berdi. PDF buzilmaganligiga ishonch hosil qiling.")
            
        # Clean up files
        if os.path.exists(local_path):
            os.remove(local_path)
        if zip_output_path and os.path.exists(zip_output_path):
            os.remove(zip_output_path)
            
    except Exception as e:
        await message.answer(f"❌ PDF ajratishda kutilmagan xatolik: {e}")
    finally:
        await progress_msg.delete()
        await state.clear()
