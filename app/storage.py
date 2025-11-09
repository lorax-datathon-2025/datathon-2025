import os
import uuid
from typing import Dict, Any, List
from datetime import datetime

from . import db

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(BASE_DIR, exist_ok=True)

DOCS_META: Dict[str, Any] = {}
DOCS_TEXT: Dict[str, Any] = {}
DOCS_IMAGES: Dict[str, Any] = {}
DOCS_AUDIT: Dict[str, Any] = {}
JOBS: Dict[str, Any] = {}

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

    db.insert_doc_record(
        doc_id=doc_id,
        filename=filename,
        status="uploaded",
        page_count=0,
        image_count=0,
        legibility_score=None,
        source_path=path,
    )
    return doc_id

def save_extracted(doc_id: str, pages: Dict[int, str], images_count: int, images_data: list = None, legibility_result: float = 0.0):
    meta = DOCS_META[doc_id]
    meta.update({
        "page_count": len(pages),
        "image_count": images_count,
        "legibility_result": legibility_result,
        "status": "preprocessed"
    })
    DOCS_TEXT[doc_id] = pages
    if images_data:
        DOCS_IMAGES[doc_id] = images_data

    db.update_doc_record(
        doc_id=doc_id,
        status="preprocessed",
        page_count=len(pages),
        image_count=images_count,
        legibility_score=legibility_result,
    )

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

    db.update_doc_record(doc_id=doc_id, status="classified")
    db.insert_classification_record(doc_id, result)

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


# Job management functions
def create_job(doc_ids: List[str]) -> str:
    """Create a new batch processing job."""
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "total_files": len(doc_ids),
        "completed": 0,
        "failed": 0,
        "doc_ids": doc_ids,
        "documents": {doc_id: {"status": "pending", "progress": 0.0} for doc_id in doc_ids},
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "error": None
    }
    return job_id


def get_job(job_id: str) -> dict:
    """Get job status and details."""
    return JOBS.get(job_id, {})


def update_job_status(job_id: str, status: str):
    """Update overall job status."""
    if job_id in JOBS:
        JOBS[job_id]["status"] = status
        JOBS[job_id]["updated_at"] = datetime.now()


def update_document_in_job(job_id: str, doc_id: str, status: str, progress: float = 0.0, error: str = None):
    """Update individual document status within a job."""
    if job_id in JOBS and doc_id in JOBS[job_id]["documents"]:
        JOBS[job_id]["documents"][doc_id] = {
            "status": status,
            "progress": progress,
            "error": error
        }
        JOBS[job_id]["updated_at"] = datetime.now()
       
        # Update counters
        if status == "completed":
            JOBS[job_id]["completed"] = sum(
                1 for d in JOBS[job_id]["documents"].values() if d["status"] == "completed"
            )
        elif status == "failed":
            JOBS[job_id]["failed"] = sum(
                1 for d in JOBS[job_id]["documents"].values() if d["status"] == "failed"
            )


def get_all_jobs() -> List[dict]:
    """Get all jobs sorted by creation date."""
    return sorted(JOBS.values(), key=lambda x: x["created_at"], reverse=True)