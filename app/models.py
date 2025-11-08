from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel

Category = Literal["Public", "Confidential", "Highly Sensitive", "Unsafe"]

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
    raw_signals: DetectorSignals
    llm_payload: Optional[Dict[str, Any]] = None
    requires_review: bool = False

class HITLUpdate(BaseModel):
    doc_id: str
    new_label: Category
    reviewer: str
    comment: Optional[str] = None
