import json
import os
from typing import Dict, Any, List

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

MODEL_NAME = os.getenv("GEMINI_MODEL", "models/gemini-1.5-pro-latest")
TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("GEMINI_TOP_P", "0.9"))
MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT", "1024"))

genai.configure(api_key=API_KEY)

MODEL = genai.GenerativeModel(
    MODEL_NAME,
    generation_config={
        "response_mime_type": "application/json",
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    },
)

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUAL", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

ROLE_MAP = {
    "system": "user",     
    "assistant": "model",
    "tool": "model",
}

def _extract_text(candidate) -> str:
    parts = getattr(candidate.content, "parts", []) or []
    text_chunks = [
        part.text
        for part in parts
        if getattr(part, "text", None)
    ]
    return "".join(text_chunks).strip()

def call_llm(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    formatted = []
    for msg in messages:
        role = ROLE_MAP.get(msg["role"], msg["role"])
        formatted.append({"role": role, "parts": [{"text": msg["content"]}]})

    try:
        response = MODEL.generate_content(
            formatted,
            safety_settings=SAFETY_SETTINGS,
        )
        if not response.candidates:
            raise ValueError("Gemini returned no candidates")
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason not in (None, 1, "STOP"):
            safety = getattr(candidate, "safety_ratings", None)
            raise ValueError(
                f"Gemini blocked output (finish_reason={finish_reason}, safety={safety})"
            )

        text = _extract_text(candidate)
        if not text:
            print(f"DEBUG: Gemini candidate: {candidate}")
            print(f"DEBUG: Candidate parts: {getattr(candidate.content, 'parts', None)}")
            raise ValueError("Gemini response did not contain text output")
        
        # Try to parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"DEBUG: Failed to parse JSON. Raw text: {text[:500]}")
            raise ValueError(f"Gemini returned invalid JSON: {e}") from e
    except Exception as exc:
        raise RuntimeError(f"Gemini call failed: {exc}") from exc


def call_llm_with_images(prompt: str, images_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Call Gemini with text prompt and images for multimodal analysis.
    
    Args:
        prompt: Text prompt for the model
        images_data: List of dicts with 'data' (base64), 'page', and 'index'
    
    Returns:
        Parsed JSON response from the model
    """
    try:
        # Build content parts: prompt + images
        parts = [{"text": prompt}]
        
        # Add images (limit to first 10 for API constraints)
        for img in images_data[:10]:
            parts.append({
                "inline_data": {
                    "mime_type": f"image/{img.get('ext', 'png')}",
                    "data": img["data"]
                }
            })
        
        response = MODEL.generate_content(
            parts,
            safety_settings=SAFETY_SETTINGS,
        )
        
        if not response.candidates:
            raise ValueError("Gemini returned no candidates")
        
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        
        if finish_reason not in (None, 1, "STOP"):
            safety = getattr(candidate, "safety_ratings", None)
            raise ValueError(
                f"Gemini blocked output (finish_reason={finish_reason}, safety={safety})"
            )
        
        text = _extract_text(candidate)
        if not text:
            raise ValueError("Gemini response did not contain text output")
        
        return json.loads(text)
    except Exception as exc:
        raise RuntimeError(f"Gemini vision call failed: {exc}") from exc

