import os
import uuid
from typing import Dict, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(BASE_DIR, exist_ok=True)

DOCS_META: Dict[str, Any] = {}
DOCS_TEXT: Dict[str, Any] = {}
DOCS_IMAGES: Dict[str, Any] = {}
DOCS_AUDIT: Dict[str, Any] = {}

def save_document(file_bytes: bytes, filename: str) -> str:
    doc_id = str(uuid.uuid4())
    path = os.path.join(BASE_DIR, f"{doc_id}_{filename}")
    with open(path, "wb") as f:
        f.write(file_bytes)

    DOCS_META[doc_id] = {
        "filename": filename,
        "path": path,
        "status": "uploaded",
    }
    return doc_id

def save_extracted(doc_id: str, pages: Dict[int, str], images_count: int, images_data: list = None):
    meta = DOCS_META[doc_id]
    meta.update({
        "page_count": len(pages),
        "image_count": images_count,
        "status": "preprocessed"
    })
    DOCS_TEXT[doc_id] = pages
    if images_data:
        DOCS_IMAGES[doc_id] = images_data

def get_document_pages(doc_id: str) -> Dict[int, str]:
    return DOCS_TEXT.get(doc_id, {})

def get_document_images(doc_id: str) -> list:
    return DOCS_IMAGES.get(doc_id, [])

def get_meta(doc_id: str) -> dict:
    return DOCS_META.get(doc_id, {})

def save_classification(doc_id: str, result: Any):
    DOCS_META[doc_id]["status"] = "classified"
    DOCS_META[doc_id]["classification"] = result
    DOCS_AUDIT.setdefault(doc_id, []).append({
        "event": "auto_classification",
        "data": result
    })

def save_hitl_update(doc_id: str, update: dict):
    DOCS_META[doc_id]["status"] = "reviewed"
    DOCS_META[doc_id]["classification"]["final_category"] = update["new_label"]
    DOCS_META[doc_id]["classification"]["explanation"] += (
        f"\n[HITL Override by {update['reviewer']}]: {update.get('comment','')}"
    )
    DOCS_AUDIT.setdefault(doc_id, []).append({
        "event": "hitl_override",
        "data": update
    })
