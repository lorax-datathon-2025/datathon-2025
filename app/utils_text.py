import pymupdf as fitz  # PyMuPDF
import docx
from typing import Dict, List, Tuple
from PIL import Image
import io
import base64

def extract_from_pdf(path: str) -> Tuple[Dict[int, str], int, List[Dict]]:
    """Extract text and images from PDF.
    
    Returns:
        Tuple of (pages_text, image_count, images_data)
        where images_data is a list of dicts with 'page', 'index', and 'data' (base64)
    """
    doc = fitz.open(path)
    pages = {}
    images_data = []
    image_count = 0
    
    for i, page in enumerate(doc, start=1):
        pages[i] = page.get_text("text") or ""
        image_list = page.get_images(full=True)
        
        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Convert to base64 for storage and API calls
                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                
                images_data.append({
                    "page": i,
                    "index": img_index,
                    "data": image_b64,
                    "ext": image_ext,
                    "size": len(image_bytes)
                })
                image_count += 1
            except Exception as e:
                # Skip images that can't be extracted
                print(f"Failed to extract image {img_index} from page {i}: {e}")
                continue
                
    return pages, image_count, images_data

def extract_from_docx(path: str) -> Tuple[Dict[int, str], int, List[Dict]]:
    """Extract text from DOCX (images not supported yet)."""
    document = docx.Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    # naive: whole doc as page 1
    return {1: text}, 0, []

def extract_generic(path: str) -> Tuple[Dict[int, str], int, List[Dict]]:
    """Extract text and images from document.
    
    Returns:
        Tuple of (pages_text, image_count, images_data)
    """
    if path.lower().endswith(".pdf"):
        return extract_from_pdf(path)
    if path.lower().endswith(".docx"):
        return extract_from_docx(path)
    # fallback: treat as text
    with open(path, "r", errors="ignore") as f:
        return {1: f.read()}, 0, []
