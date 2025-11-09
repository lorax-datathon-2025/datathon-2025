from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel

Category = Literal["Public", "Confidential", "Highly Sensitive", "Unsafe"]

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    image_count: int
    legibility_result: float
    status: str = "ingested"

class Citation(BaseModel):
    page: Optional[int] = None
    snippet: str
    image_index: Optional[int] = None
    region: Optional[str] = None
    source: Optional[str] = None

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
    primary_analysis: Optional[Dict[str, Any]] = None
    secondary_analysis: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    legibility_score: Optional[float] = None

class HITLUpdate(BaseModel):
    doc_id: str
    new_label: Category
    reviewer: str
    comment: Optional[str] = None
