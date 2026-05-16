import os
import img2pdf
from PIL import Image

async def create_pdf_from_images(image_paths: list[str], output_filename: str) -> str:
    """
    Berilgan rasmlar ro'yxatini bitta PDF faylga birlashtiradi.
    """
    try:
        valid_images = []
        for img_path in image_paths:
            try:
                # Rasmni Pillow orqali ochib tekshiramiz
                with Image.open(img_path) as img:
                    # img2pdf asosan RGB formatni yaxshi qabul qiladi
                    # RGBA (shaffof fon) kabi formatlarni RGB ga o'tkazamiz
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                        temp_path = f"{img_path}_rgb.jpg"
                        img.save(temp_path, "JPEG")
                        valid_images.append(temp_path)
                    else:
                        valid_images.append(img_path)
            except Exception as e:
                print(f"Rasm bilan muammo yuzaga keldi: {img_path}, Xato: {e}")

        if not valid_images:
            raise ValueError("Yaroqli rasmlar topilmadi.")

        # img2pdf orqali rasmlarni PDF ga o'giramiz
        with open(output_filename, "wb") as f:
            pdf_bytes = img2pdf.convert(valid_images)
            f.write(pdf_bytes)
            
        # Agar RGB ga o'tkazish paytida vaqtinchalik fayllar yaratilgan bo'lsa, ularni o'chiramiz
        for img_path in valid_images:
            if img_path.endswith("_rgb.jpg"):
                try:
                    os.remove(img_path)
                except OSError:
                    pass

        return output_filename
    except Exception as e:
        print(f"PDF yaratishda xato yuzaga keldi: {e}")
        return None
