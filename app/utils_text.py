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
    """Extract text and images from DOCX.
    
    DOCX doesn't have explicit pages, so we split by page breaks or sections.
    If no page breaks found, we chunk by paragraph count.
    """
    document = docx.Document(path)
    
    # Try to split by page breaks and section breaks
    pages = {}
    current_page = 1
    current_text = []
    
    for para in document.paragraphs:
        para_text = para.text
        
        # Check for page break or section break
        has_page_break = para._element.xpath('.//w:br[@w:type="page"]')
        has_section_break = para._element.xpath('.//w:pPr/w:sectPr')
        
        if has_page_break or has_section_break:
            # Save current page before break
            if current_text or para_text:
                pages[current_page] = "\n".join(current_text + [para_text])
                current_page += 1
                current_text = []
        else:
            current_text.append(para_text)
    
    # Save last page
    if current_text:
        pages[current_page] = "\n".join(current_text)
    
    # If we still don't have enough pages, estimate by character count
    # Typical page ~3000 chars (500 words * 6 chars avg)
    if len(pages) < 2:
        all_text = "\n".join(p.text for p in document.paragraphs)
        chars_per_page = 3000
        
        if len(all_text) > chars_per_page:
            # Split by character count
            para_list = [p.text for p in document.paragraphs]
            pages = {}
            current_page = 1
            current_chars = 0
            current_text = []
            
            for para_text in para_list:
                current_text.append(para_text)
                current_chars += len(para_text)
                
                if current_chars >= chars_per_page:
                    pages[current_page] = "\n".join(current_text)
                    current_page += 1
                    current_text = []
                    current_chars = 0
            
            # Save last page
            if current_text:
                pages[current_page] = "\n".join(current_text)
    
    # Extract images from DOCX
    images_data = []
    image_count = 0
    
    try:
        from docx.oxml import parse_xml
        from docx.oxml.ns import qn
        
        # Get relationships to find images
        for rel in document.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    image_bytes = rel.target_part.blob
                    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Determine extension from content type
                    content_type = rel.target_part.content_type
                    ext = content_type.split('/')[-1] if '/' in content_type else 'png'
                    
                    images_data.append({
                        "page": 1,  # DOCX doesn't track which page images are on
                        "index": image_count,
                        "data": image_b64,
                        "ext": ext,
                        "size": len(image_bytes)
                    })
                    image_count += 1
                except Exception as e:
                    print(f"Failed to extract image: {e}")
                    continue
    except Exception as e:
        print(f"Image extraction from DOCX failed: {e}")
    
    return pages, image_count, images_data

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
