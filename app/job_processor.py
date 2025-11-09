"""
Background job processor for batch document classification.
"""
import asyncio
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from .storage import (
    get_document_pages, 
    get_document_images, 
    get_meta,
    save_classification,
    update_job_status,
    update_document_in_job,
    get_job
)
from .detectors import run_detectors
from .orchestrator import classify_document

# Thread pool for CPU-bound operations
executor = ThreadPoolExecutor(max_workers=8)

def process_single_document(job_id: str, doc_id: str):
    """Process a single document (synchronous version for thread pool)."""
    try:
        # Update status to processing
        update_document_in_job(job_id, doc_id, "processing", progress=10.0)
        
        # Get document data
        pages = get_document_pages(doc_id)
        if not pages:
            raise ValueError("Document not found or not processed")
        
        meta = get_meta(doc_id)
        image_count = meta.get("image_count", 0)
        images_data = get_document_images(doc_id)
        
        update_document_in_job(job_id, doc_id, "processing", progress=30.0)
        
        # Run detectors
        signals = run_detectors(pages)
        
        update_document_in_job(job_id, doc_id, "processing", progress=60.0)
        
        # Classify document
        result = classify_document(doc_id, pages, signals, image_count, images_data)
        
        update_document_in_job(job_id, doc_id, "processing", progress=90.0)
        
        # Save classification
        save_classification(doc_id, result)
        
        # Mark as completed
        update_document_in_job(job_id, doc_id, "completed", progress=100.0)
        
        return {"success": True, "doc_id": doc_id}
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"Error processing document {doc_id}: {error_msg}")
        print(traceback.format_exc())
        update_document_in_job(job_id, doc_id, "failed", progress=0.0, error=error_msg)
        return {"success": False, "doc_id": doc_id, "error": error_msg}


def process_batch_job(job_id: str):
    """Process all documents in a batch job (synchronous for BackgroundTasks)."""
    try:
        job = get_job(job_id)
        if not job:
            return
        
        doc_ids = job.get("doc_ids", [])
        
        # Update job status to processing
        update_job_status(job_id, "processing")
        
        # Process documents concurrently using ThreadPoolExecutor
        futures = [executor.submit(process_single_document, job_id, doc_id) for doc_id in doc_ids]
        
        # Wait for all to complete
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Future failed: {e}")
                print(traceback.format_exc())
        
        # Check if all succeeded
        job = get_job(job_id)
        if job["failed"] > 0:
            update_job_status(job_id, "completed")  # Completed with some failures
        else:
            update_job_status(job_id, "completed")
        
        return results
        
    except Exception as e:
        print(f"Batch job {job_id} failed: {e}")
        print(traceback.format_exc())
        update_job_status(job_id, "failed")
        raise
