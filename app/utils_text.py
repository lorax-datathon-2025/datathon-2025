import pymupdf as fitz  # PyMuPDF
import docx
from typing import Dict, List, Tuple
from PIL import Image
import io
import base64
import uuid, cv2, numpy as np
import os
import pytesseract

default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", default_path)

from pytesseract import Output


def extract_from_pdf(path: str) -> Tuple[Dict[int, str], int, float, List[Dict]]:
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


   legibility_score = analyze_pdf_legibility(path)
   legibility_report = (
   sum(s["combined_legibility"] for s in legibility_score) / len(legibility_score)
   if legibility_score else 0.0
   )
              
   return pages, image_count, legibility_report, images_data


def extract_from_docx(path: str) -> Tuple[Dict[int, str], int, float, List[Dict]]:
    """Extract text from DOCX (images not supported yet)."""
    document = docx.Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    # naive: whole doc as page 1
    legibility = 1.0 if text.strip() else 0.0
    return {1: text}, 0, legibility, []


def pdf_to_images(pdf_path: str, dpi: int = 150):
   """Convert all pages of a PDF into RGB images."""
   doc = fitz.open(pdf_path)
   images = []
   for page_num in range(len(doc)):
       page = doc.load_page(page_num)
       pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
       img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
       img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
       images.append(img_rgb)
   doc.close()
   return images




def sharpness_score(img_rgb: np.ndarray) -> float:
   """Compute image sharpness using variance of Laplacian."""
   gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
   return float(cv2.Laplacian(gray, cv2.CV_64F).var())




def ocr_confidence_score(img_rgb: np.ndarray) -> float:
   """Compute average OCR confidence as proxy for text legibility."""
   data = pytesseract.image_to_data(img_rgb, output_type=Output.DICT)
   confs = []
   for c in data['conf']:
       try:
           val = int(c)
           if val > 0:
               confs.append(val)
       except (ValueError, TypeError):
           continue
   if not confs:
       return 0.0
   return sum(confs) / len(confs)




def combined_legibility(img_rgb: np.ndarray) -> float:
   """Blend image sharpness and OCR confidence into a single legibility score (0–1)."""
   sharp = sharpness_score(img_rgb)
   ocr_conf = ocr_confidence_score(img_rgb)
   # Normalize and weight
   sharp_norm = min(sharp / 1000, 1.0)
   ocr_norm = ocr_conf / 100.0
   return round(0.5 * sharp_norm + 0.5 * ocr_norm, 3)




def analyze_pdf_legibility(pdf_path: str):
   """Compute per-page legibility for a PDF."""
   pages = pdf_to_images(pdf_path)
   results = []
   for i, img in enumerate(pages, 1):
       leg_score = combined_legibility(img)
       results.append({
           "page": i,
           "sharpness": sharpness_score(img),
           "ocr_confidence": ocr_confidence_score(img),
           "combined_legibility": leg_score
       })
   return results


def extract_generic(path: str) -> Tuple[Dict[int, str], int, float, List[Dict]]:
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
       return {1: f.read()}, 0, 0.0, []
