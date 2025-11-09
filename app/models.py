from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

Category = Literal["Public", "Confidential", "Highly Sensitive", "Unsafe"]

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    image_count: int
    status: str = "ingested"

class Citation(BaseModel):
    page: int
    snippet: str

class DetectorSignals(BaseModel):
    has_pii: bool = False
    pii_hits: List[Citation] = []
    has_unsafe_pattern: bool = False
    unsafe_hits: List[Citation] = []
    has_internal_markers: bool = False
    notes: List[str] = []

class ClassificationResult(BaseModel):
    doc_id: str
    final_category: Category
    secondary_tags: List[str]
    confidence: float
    citations: List[Citation]
    explanation: str
    page_count: int
    image_count: int
    content_safety: str
    raw_signals: DetectorSignals
    llm_payload: Optional[Dict[str, Any]] = None
    requires_review: bool = False
    dual_llm_agreement: Optional[float] = None  # 0-1: how much the two LLMs agree
    dual_llm_disagreements: Optional[List[str]] = None  # List of fields where LLMs disagree

class HITLUpdate(BaseModel):
    doc_id: str
    new_label: Category
    reviewer: str
    comment: Optional[str] = None

class BatchUploadResponse(BaseModel):
    job_id: str
    total_files: int
    status: JobStatus
    message: str

class DocumentStatus(BaseModel):
    doc_id: str
    filename: str
    status: str
    progress: float  # 0-100
    error: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_files: int
    completed: int
    failed: int
    progress: float  # 0-100
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentStatus]
    error: Optional[str] = None
