// API service for backend communication
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export interface UploadResponse {
  doc_id: string;
  filename: string;
  page_count: number;
  image_count: number;
  legibility_result: number;
  status: string;
}

export interface Citation {
  page: number;
  snippet: string;
  image_index?: number | null;
  region?: string | null;
  source?: string;
  evidence?: string;
}

export interface ClassificationResponse {
  doc_id: string;
  final_category: string;
  secondary_tags: string[];
  confidence: number;
  citations: Citation[];
  explanation: string;
  page_count: number;
  image_count: number;
  content_safety: string;
  raw_signals: {
    has_pii: boolean;
    pii_hits: string[];
    has_unsafe_pattern: boolean;
    unsafe_hits: string[];
    has_internal_markers: boolean;
    notes: string[];
  };
  requires_review: boolean;
  dual_llm_agreement: number;
  dual_llm_disagreements: any;
  primary_analysis: {
    engine: string;
    model: string;
    category: string;
    secondary_tags: string[];
    confidence: number;
    explanation: string;
    citations: Citation[];
  };
  secondary_analysis: {
    model: string;
    label: string;
    confidence: number;
    explanation: string;
    content_safety: string;
    critical_info: string[];
    needs_review: boolean;
    citations: Citation[];
  };
  summary: {
    decision: {
      category: string;
      confidence: number;
      secondary_tags: string[];
    };
    review: {
      required: boolean;
      triggers: string[];
    };
    agreement: {
      score: number;
      disagreements: string[];
    };
    content_safety: string;
    legibility: {
      average_score: number;
    };
  };
  legibility_score: number;
}

export interface DocumentMetadata {
  doc_id: string;
  filename: string;
  page_count: number;
  image_count: number;
  status: string;
  classification?: ClassificationResponse;
}

export interface HITLUpdate {
  new_label: string;
  feedback: string;
}

/**
 * Upload a document for analysis
 */
export const uploadDocument = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
};

/**
 * Classify an uploaded document
 */
export const classifyDocument = async (docId: string): Promise<ClassificationResponse> => {
  const response = await fetch(`${API_BASE_URL}/classify/${docId}`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Classification failed" }));
    throw new Error(error.detail || "Classification failed");
  }

  return response.json();
};

/**
 * Get document metadata and classification results
 */
export const getDocument = async (docId: string): Promise<DocumentMetadata> => {
  const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
    method: "GET",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to fetch document" }));
    throw new Error(error.detail || "Failed to fetch document");
  }

  return response.json();
};

/**
 * Submit human-in-the-loop feedback
 */
export const submitHITLFeedback = async (
  docId: string,
  update: HITLUpdate
): Promise<{ message: string }> => {
  const response = await fetch(`${API_BASE_URL}/hitl`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      doc_id: docId,
      ...update,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to submit feedback" }));
    throw new Error(error.detail || "Failed to submit feedback");
  }

  return response.json();
};

/**
 * Delete a document
 */
export const deleteDocument = async (docId: string): Promise<{ status: string; doc_id: string }> => {
  const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to delete document" }));
    throw new Error(error.detail || "Failed to delete document");
  }

  return response.json();
};

/**
 * Check API health
 */
export const checkHealth = async (): Promise<{ status: string }> => {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("API health check failed");
  }

  return response.json();
};
