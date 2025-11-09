from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import json

from .models import UploadResponse, ClassificationResult, HITLUpdate
from .storage import save_document, save_extracted, get_document_pages, get_document_images, get_meta, save_classification
from .utils_text import extract_generic
from .detectors import run_detectors
from .orchestrator import classify_document
from .hitl import apply_hitl_update

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
async def classify(doc_id: str, pretty: bool = False):
    pages = get_document_pages(doc_id)
    if not pages:
        raise HTTPException(status_code=404, detail="Document not found or not processed.")
    
    meta = get_meta(doc_id)
    image_count = meta.get("image_count", 0)
    images_data = get_document_images(doc_id)

    signals = run_detectors(pages)
    result = classify_document(doc_id, pages, signals, image_count, images_data)
    save_classification(doc_id, result)

    if pretty:
        serialized = json.dumps(result.dict(), indent=2, ensure_ascii=False)
        return Response(content=serialized + "\n", media_type="application/json")

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

@app.get("/health")
async def health():
    return {"status": "ok"}
