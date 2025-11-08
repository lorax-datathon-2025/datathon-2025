import fitz  # PyMuPDF
import docx
from typing import Dict
from PIL import Image
import io

def extract_from_pdf(path: str) -> (Dict[int, str], int):
    doc = fitz.open(path)
    pages = {}
    image_count = 0
    for i, page in enumerate(doc, start=1):
        pages[i] = page.get_text("text") or ""
        image_list = page.get_images(full=True)
        image_count += len(image_list)
    return pages, image_count

def extract_from_docx(path: str) -> (Dict[int, str], int):
    document = docx.Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    # naive: whole doc as page 1
    return {1: text}, 0

def extract_generic(path: str) -> (Dict[int, str], int):
    if path.lower().endswith(".pdf"):
        return extract_from_pdf(path)
    if path.lower().endswith(".docx"):
        return extract_from_docx(path)
    # fallback: treat as text
    with open(path, "r", errors="ignore") as f:
        return {1: f.read()}, 0
