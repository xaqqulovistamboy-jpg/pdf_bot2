import os
import uuid
import re
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from database.db import Database
from states.states import PdfState
from keyboards.keyboards import get_main_keyboard, get_pdf_creation_keyboard
from services.queue_service import QueueManager, UserSession
from services.pdf_service import create_pdf_from_images_async, extract_zip_images_async

router = Router()

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Global queue manager instance
queue_manager = QueueManager(debounce_seconds=1.2)

async def on_images_batch_complete(session: UserSession, message: Message):
    """Callback fired when user has finished sending a batch of images"""
    total_images = len(session.images)
    text = (
        f"✅ {total_images} ta rasm qabul qilindi!\n\n"
        "Yana rasm yuborishingiz yoki pastdagi tugmani bosib PDF ni yaratishingiz mumkin. 📄"
    )
    
    # Send confirmation message or update the existing one to prevent spam
    try:
        if session.summary_message:
            await session.summary_message.edit_text(text, reply_markup=get_pdf_creation_keyboard())
        else:
            session.summary_message = await message.answer(text, reply_markup=get_pdf_creation_keyboard())
    except Exception:
        # Fallback to sending a new message if edit fails
        session.summary_message = await message.answer(text, reply_markup=get_pdf_creation_keyboard())

# --- IMAGE / DOCUMENT / ZIP HANDLER ---

@router.message(F.photo | F.document)
async def handle_uploads(message: Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    
    # If waiting for another input, ignore or reset FSM
    current_state = await state.get_state()
    if current_state in [PdfState.waiting_for_watermark, AdminState := None]:
        return

    # Check if document is a ZIP
    is_zip = False
    if message.document:
        doc = message.document
        mime = doc.mime_type or ""
        name = doc.file_name or ""
        if mime == "application/zip" or name.lower().endswith(".zip"):
            is_zip = True
        elif not mime.startswith("image/"):
            await message.answer("❌ Iltimos, faqat rasm formatidagi fayllarni yoki .zip arxivlarini yuboring.")
            return

    # If it is a ZIP, extract and process
    if is_zip:
        processing_msg = await message.answer("⏳ ZIP arxivi yuklab olinmoqda va ochilmoqda...")
        file_id = message.document.file_id
        
        try:
            file = await message.bot.get_file(file_id)
            zip_unique_name = f"{uuid.uuid4().hex}.zip"
            zip_local_path = os.path.join(TEMP_DIR, zip_unique_name)
            
            await message.bot.download_file(file.file_path, zip_local_path)
            
            # Extract images in the background
            extract_dir = os.path.join(TEMP_DIR, f"zip_{uuid.uuid4().hex}")
            os.makedirs(extract_dir, exist_ok=True)
            
            image_paths = await extract_zip_images_async(zip_local_path, extract_dir)
            
            # Clean up the zip file itself
            if os.path.exists(zip_local_path):
                os.remove(zip_local_path)
                
            if not image_paths:
                await processing_msg.edit_text("❌ ZIP fayl ichidan hech qanday yaroqli rasm topilmadi.")
                return
                
            # Store extracted paths in FSM context
            await state.update_data(zip_extracted_images=image_paths, zip_extract_dir=extract_dir)
            await state.set_state(PdfState.waiting_for_name)
            
            await processing_msg.edit_text(
                f"✅ ZIP ichidan {len(image_paths)} ta rasm ajratib olindi!\n"
                "✏️ Iltimos, tayyorlanadigan PDF fayl uchun nom kiriting:"
            )
        except Exception as e:
            await processing_msg.edit_text(f"❌ ZIP faylni qayta ishlashda xatolik: {e}")
        return

    # If it's a normal image (photo or file image)
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    file_ext = "jpg"
    if message.document:
        name = message.document.file_name or ""
        file_ext = name.split(".")[-1] if "." in name else "jpg"

    try:
        # Download image file
        file = await message.bot.get_file(file_id)
        unique_name = f"{uuid.uuid4().hex}.{file_ext}"
        local_path = os.path.join(TEMP_DIR, unique_name)
        
        await message.bot.download_file(file.file_path, local_path)
        
        # Add to session queue with debounce
        await queue_manager.add_image(
            user_id=user_id,
            file_path=local_path,
            message_id=message.message_id,
            trigger_message=message,
            callback=on_images_batch_complete
        )
    except Exception as e:
        await message.answer(f"❌ Rasmni yuklashda xatolik: {e}")

# --- CALLBACKS FOR ACTION ---

@router.callback_query(F.data == "create_pdf")
async def process_create_pdf(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    session = queue_manager.get_session(user_id)
    
    if not session.images:
        await callback.message.edit_text("❌ Hech qanday rasm topilmadi. Iltimos, avval rasm yuboring.")
        await callback.answer()
        return
        
    await state.set_state(PdfState.waiting_for_name)
    await callback.message.answer("✏️ Iltimos, tayyorlanadigan PDF fayl uchun nom kiriting (masalan: Mening_hujjatim):")
    await callback.answer()

@router.callback_query(F.data == "cancel_process")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await queue_manager.clear_session(user_id)
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Amaliyot bekor qilindi va barcha yuklangan rasmlar o'chirildi.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# --- FSM NAME COMPILATION HANDLER ---

@router.message(PdfState.waiting_for_name)
async def process_pdf_name(message: Message, state: FSMContext, db: Database, user_settings: dict):
    user_id = message.from_user.id
    pdf_name = message.text.strip()
    
    if pdf_name.lower() == "/cancel":
        await queue_manager.clear_session(user_id)
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_keyboard())
        return

    # Clean filename
    safe_name = re.sub(r'[\\/*?:"<>|]', "", pdf_name)
    if not safe_name:
        safe_name = "Hujjat"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
        
    state_data = await state.get_data()
    
    if state_data.get("is_merge_op"):
        session = queue_manager.get_session(user_id)
        pdfs = session.get_sorted_pdfs()
        if not pdfs:
            await message.answer("❌ Hech qanday PDF fayl topilmadi.", reply_markup=get_main_keyboard())
            await state.clear()
            return
            
        progress_msg = await message.answer("⏳ PDF fayllar birlashtirilmoqda, iltimos kuting...")
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        temp_pdf_filename = os.path.join(TEMP_DIR, f"merged_{date_str}_{user_id}.pdf")
        
        try:
            result_pdf = await merge_pdfs_async(pdfs, temp_pdf_filename)
            if result_pdf and os.path.exists(result_pdf):
                file_size = os.path.getsize(result_pdf)
                pdf_document = FSInputFile(result_pdf, filename=safe_name)
                
                await message.answer_document(
                    document=pdf_document,
                    caption=f"🎉 Birlashtirilgan PDF tayyor!\n📦 Hujjatlar soni: {len(pdfs)}"
                )
                
                await db.add_conversion(
                    user_id=user_id,
                    file_type="merge_pdf",
                    files_count=len(pdfs),
                    file_size_bytes=file_size
                )
            else:
                await message.answer("❌ PDF birlashtirishda xatolik yuz berdi.")
        except Exception as e:
            await message.answer(f"❌ PDF birlashtirishda kutilmagan xato: {e}")
        finally:
            await progress_msg.delete()
            await queue_manager.clear_session(user_id)
            if os.path.exists(temp_pdf_filename):
                try:
                    os.remove(temp_pdf_filename)
                except OSError:
                    pass
            await state.clear()
        return

    zip_images = state_data.get("zip_extracted_images")
    zip_dir = state_data.get("zip_extract_dir")
    
    # Retrieve images
    if zip_images:
        images = zip_images
    else:
        session = queue_manager.get_session(user_id)
        images = session.get_sorted_images()
        
    if not images:
        await message.answer("❌ Hech qanday rasm topilmadi. Iltimos, boshidan boshlang.", reply_markup=get_main_keyboard())
        await state.clear()
        return

    progress_msg = await message.answer("⏳ PDF fayl shakllantirilmoqda, iltimos kuting...")
    
    # Get user settings
    quality = user_settings.get("pdf_quality", "medium")
    watermark = user_settings.get("watermark_text")
    
    # Temp PDF file
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    temp_pdf_filename = os.path.join(TEMP_DIR, f"temp_{date_str}_{user_id}.pdf")
    
    try:
        # Create PDF asynchronously
        result_pdf = await create_pdf_from_images_async(images, temp_pdf_filename, quality, watermark)
        
        if result_pdf and os.path.exists(result_pdf):
            # Calculate file size
            file_size = os.path.getsize(result_pdf)
            pdf_document = FSInputFile(result_pdf, filename=safe_name)
            
            # Send file
            await message.answer_document(
                document=pdf_document,
                caption=f"🎉 PDF faylingiz tayyor!\n"
                        f"📊 Sifat: {quality.capitalize()}\n"
                        f"🖼 Sahifalar soni: {len(images)}"
            )
            
            # Record stat in database
            await db.add_conversion(
                user_id=user_id,
                file_type="zip_to_pdf" if zip_images else "images_to_pdf",
                files_count=len(images),
                file_size_bytes=file_size
            )
        else:
            await message.answer("❌ PDF yaratishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
    except Exception as e:
        await message.answer(f"❌ PDF yaratishda kutilmagan xato: {e}")
    finally:
        # Cleanup
        await progress_msg.delete()
        
        # Clean local files
        if zip_images:
            for img in zip_images:
                if os.path.exists(img):
                    try:
                        os.remove(img)
                    except OSError:
                        pass
            if zip_dir and os.path.exists(zip_dir):
                try:
                    os.rmdir(zip_dir)
                except OSError:
                    pass
        else:
            await queue_manager.clear_session(user_id)
            
        if os.path.exists(temp_pdf_filename):
            try:
                os.remove(temp_pdf_filename)
            except OSError:
                pass
                
        await state.clear()
