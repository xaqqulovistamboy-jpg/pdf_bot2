import os
import zipfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
import img2pdf
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pypdf import PdfReader, PdfWriter

# Running blocking image/file operations in a thread pool to avoid blocking the main async loop
executor = ThreadPoolExecutor(max_workers=4)

def _process_single_image(img_path: str, quality_mode: str, watermark_text: str = None) -> str:
    """
    Resizes, applies watermark, and saves the image with proper quality compression.
    Runs inside a thread pool.
    """
    try:
        with Image.open(img_path) as img:
            # 1. Convert to RGB mode (needed for PDF conversion)
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # 2. Quality-based resizing
            max_size = 1920
            jpeg_quality = 90
            
            if quality_mode == "low":
                max_size = 1000
                jpeg_quality = 55
            elif quality_mode == "medium":
                max_size = 1600
                jpeg_quality = 75
            elif quality_mode == "high":
                max_size = 2500
                jpeg_quality = 95

            width, height = img.size
            if max(width, height) > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 3. Watermarking
            if watermark_text:
                # Create semi-transparent overlay
                txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(txt_layer)
                
                # Try to load a standard font, fallback to default if not available
                font = None
                font_sizes = [int(img.size[0] * 0.04), 30, 20, 12]
                
                for f_size in font_sizes:
                    try:
                        # Try commonly available fonts on systems (Windows / Linux)
                        font = ImageFont.truetype("arial.ttf", f_size)
                        break
                    except IOError:
                        try:
                            font = ImageFont.truetype("DejaVuSans.ttf", f_size)
                            break
                        except IOError:
                            continue
                
                if font is None:
                    font = ImageFont.load_default()
                
                # Calculate size and position (bottom right corner with padding)
                # In Pillow 10+, textbbox is the standard way to get text size
                try:
                    bbox = draw.textbbox((0, 0), watermark_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                except AttributeError:
                    # Fallback for older Pillow versions
                    text_width, text_height = draw.textsize(watermark_text, font=font)
                
                margin_x = int(img.size[0] * 0.05)
                margin_y = int(img.size[1] * 0.05)
                x = img.size[0] - text_width - margin_x
                y = img.size[1] - text_height - margin_y
                
                # Draw text with 40% opacity (100 out of 255)
                # Outer stroke/shadow for readability
                draw.text((x + 1, y + 1), watermark_text, font=font, fill=(0, 0, 0, 80))
                draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 120))
                
                # Composite images
                img = Image.alpha_composite(img.convert("RGBA"), txt_layer).convert("RGB")
            
            # Save processed image to a temp location
            temp_mod_path = f"{img_path}_mod.jpg"
            img.save(temp_mod_path, "JPEG", quality=jpeg_quality)
            return temp_mod_path
    except Exception as e:
        print(f"Error processing image {img_path}: {e}")
        return None

def _merge_pdfs_sync(pdf_paths: list[str], output_filename: str) -> str:
    """Sync PDF merge using pypdf"""
    merger = PdfWriter()
    try:
        for path in pdf_paths:
            merger.append(path)
        merger.write(output_filename)
        return output_filename
    finally:
        merger.close()

def _split_pdf_sync(pdf_path: str, output_dir: str) -> str:
    """Sync PDF split. Splits pages and writes them to a ZIP archive."""
    reader = PdfReader(pdf_path)
    base_name = os.path.basename(pdf_path).replace(".pdf", "")
    zip_path = os.path.join(output_dir, f"{base_name}_split.zip")
    
    temp_files = []
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for page_idx in range(len(reader.pages)):
                writer = PdfWriter()
                writer.append(pdf_path, pages=(page_idx, page_idx + 1))
                
                page_pdf_name = f"{base_name}_page_{page_idx + 1}.pdf"
                page_pdf_path = os.path.join(output_dir, page_pdf_name)
                
                writer.write(page_pdf_path)
                writer.close()
                
                zip_file.write(page_pdf_path, arcname=page_pdf_name)
                temp_files.append(page_pdf_path)
        
        return zip_path
    finally:
        # Clean up temp page PDFs
        for tf in temp_files:
            try:
                if os.path.exists(tf):
                    os.remove(tf)
            except OSError:
                pass

def _extract_zip_sync(zip_path: str, extract_dir: str) -> list[str]:
    """Sync zip extraction and filtering images"""
    image_paths = []
    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Extract files
        zip_ref.extractall(extract_dir)
        
        # Collect extracted file paths
        for filename in zip_ref.namelist():
            # Skip hidden files or OS directories
            if filename.startswith('__MACOSX/') or filename.endswith('.DS_Store'):
                continue
            
            ext = os.path.splitext(filename.lower())[1]
            if ext in valid_extensions:
                full_path = os.path.join(extract_dir, filename)
                # Ensure the path exists and is a file
                if os.path.isfile(full_path):
                    image_paths.append(full_path)
                    
    # Sort files naturally by filename
    image_paths.sort()
    return image_paths


# --- ASYNC API WRAPPERS ---

async def create_pdf_from_images_async(
    image_paths: list[str], 
    output_filename: str, 
    quality_mode: str, 
    watermark_text: str = None
) -> str:
    """Combines a list of images into a single PDF asynchronously"""
    loop = asyncio.get_running_loop()
    
    # 1. Process all images concurrently in the thread pool
    tasks = [
        loop.run_in_executor(executor, _process_single_image, img, quality_mode, watermark_text)
        for img in image_paths
    ]
    processed_paths = await asyncio.gather(*tasks)
    
    # Filter out failed image conversions
    valid_processed = [p for p in processed_paths if p is not None]
    
    if not valid_processed:
        return None
        
    try:
        # 2. Run img2pdf on processed images (run in executor since it writes to disk)
        def _convert():
            with open(output_filename, "wb") as f:
                pdf_bytes = img2pdf.convert(valid_processed)
                f.write(pdf_bytes)
            return output_filename
            
        await loop.run_in_executor(executor, _convert)
        return output_filename
    except Exception as e:
        print(f"Error generating PDF bytes: {e}")
        return None
    finally:
        # 3. Clean up the temporary modified files
        for p in valid_processed:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

async def merge_pdfs_async(pdf_paths: list[str], output_filename: str) -> str:
    """Merge multiple PDF files asynchronously"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _merge_pdfs_sync, pdf_paths, output_filename)

async def split_pdf_async(pdf_path: str, output_dir: str) -> str:
    """Split pages of a PDF into individual files packed into a ZIP asynchronously"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _split_pdf_sync, pdf_path, output_dir)

async def extract_zip_images_async(zip_path: str, extract_dir: str) -> list[str]:
    """Extract and retrieve image paths from a zip file asynchronously"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _extract_zip_sync, zip_path, extract_dir)
