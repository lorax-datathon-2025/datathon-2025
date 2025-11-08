import json
import os
from typing import Dict, Any, List

import google.generativeai as genai

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
            raise ValueError("Gemini response did not contain text output")
        return json.loads(text)
    except Exception as exc:
        raise RuntimeError(f"Gemini call failed: {exc}") from exc
