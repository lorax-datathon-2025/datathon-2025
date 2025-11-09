from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os

from .models import (
    UploadResponse, ClassificationResult, HITLUpdate, 
    BatchUploadResponse, JobStatusResponse, DocumentStatus, JobStatus
)
from .storage import (
    save_document, save_extracted, get_document_pages, get_document_images, 
    get_meta, save_classification, create_job, get_job, get_all_jobs
)
from .utils_text import extract_generic
from .detectors import run_detectors
from .orchestrator import classify_document
from .hitl import apply_hitl_update
from .job_processor import process_batch_job

app = FastAPI(title="RegDoc Guardrail API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    doc_id = save_document(content, file.filename)
    meta = get_meta(doc_id)

    pages, image_count, images_data = extract_generic(meta["path"])
    if not pages:
        raise HTTPException(status_code=400, detail="Unable to extract content.")
    save_extracted(doc_id, pages, image_count, images_data)

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        page_count=len(pages),
        image_count=image_count,
        status="preprocessed",
    )

@app.post("/classify/{doc_id}")
async def classify(doc_id: str):
    pages = get_document_pages(doc_id)
    if not pages:
        raise HTTPException(status_code=404, detail="Document not found or not processed.")
    
    meta = get_meta(doc_id)
    image_count = meta.get("image_count", 0)
    images_data = get_document_images(doc_id)

    signals = run_detectors(pages)
    result = classify_document(doc_id, pages, signals, image_count, images_data)
    save_classification(doc_id, result)
    return result

@app.get("/documents/{doc_id}")
async def get_document_status(doc_id: str):
    meta = get_meta(doc_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Not found.")
    return meta

@app.post("/hitl", response_model=dict)
async def hitl_override(update: HITLUpdate):
    meta = get_meta(update.doc_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Document not found.")

    apply_hitl_update(update)
    return {"status": "ok"}

@app.post("/batch/upload", response_model=BatchUploadResponse)
async def batch_upload(files: List[UploadFile], background_tasks: BackgroundTasks):
    """
    Upload multiple documents and process them in batch.
    Returns a job_id for tracking progress.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    doc_ids = []
    failed_uploads = []
    
    # Upload and preprocess all documents
    for file in files:
        try:
            content = await file.read()
            doc_id = save_document(content, file.filename)
            meta = get_meta(doc_id)
            
            pages, image_count, images_data = extract_generic(meta["path"])
            if not pages:
                failed_uploads.append(file.filename)
                continue
            
            save_extracted(doc_id, pages, image_count, images_data)
            doc_ids.append(doc_id)
        except Exception as e:
            print(f"Failed to upload {file.filename}: {e}")
            failed_uploads.append(file.filename)
    
    if not doc_ids:
        raise HTTPException(
            status_code=400, 
            detail=f"All uploads failed. Files: {', '.join(failed_uploads)}"
        )
    
    # Create job and start background processing
    job_id = create_job(doc_ids)
    background_tasks.add_task(process_batch_job, job_id)
    
    message = f"Batch upload initiated. Successfully queued {len(doc_ids)} documents."
    if failed_uploads:
        message += f" Failed: {', '.join(failed_uploads)}"
    
    return BatchUploadResponse(
        job_id=job_id,
        total_files=len(doc_ids),
        status=JobStatus.PENDING,
        message=message
    )

@app.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a batch processing job with detailed progress.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build document status list
    documents = []
    for doc_id in job["doc_ids"]:
        meta = get_meta(doc_id)
        doc_status_data = job["documents"].get(doc_id, {})
        documents.append(DocumentStatus(
            doc_id=doc_id,
            filename=meta.get("filename", "unknown"),
            status=doc_status_data.get("status", "pending"),
            progress=doc_status_data.get("progress", 0.0),
            error=doc_status_data.get("error")
        ))
    
    # Calculate overall progress
    total_progress = sum(d.progress for d in documents)
    overall_progress = total_progress / len(documents) if documents else 0.0
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=JobStatus(job["status"]),
        total_files=job["total_files"],
        completed=job["completed"],
        failed=job["failed"],
        progress=overall_progress,
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        documents=documents,
        error=job.get("error")
    )

@app.get("/jobs")
async def list_jobs():
    """
    List all batch processing jobs.
    """
    jobs = get_all_jobs()
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "total_files": job["total_files"],
                "completed": job["completed"],
                "failed": job["failed"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"]
            }
            for job in jobs
        ]
    }

@app.get("/health")
async def health():
    return {"status": "ok"}
