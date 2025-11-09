import json
import os
from typing import Any, Dict

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore


SECONDARY_API_KEY = os.getenv("SECONDARY_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
SECONDARY_MODEL = os.getenv("SECONDARY_LLM_MODEL", "gpt-4o-mini")
SECONDARY_TEMPERATURE = float(os.getenv("SECONDARY_LLM_TEMPERATURE", "0.1"))
SECONDARY_TOP_P = float(os.getenv("SECONDARY_LLM_TOP_P", "0.9"))
SECONDARY_MAX_TOKENS = int(os.getenv("SECONDARY_LLM_MAX_OUTPUT", "800"))

if SECONDARY_API_KEY and OpenAI:
    _client = OpenAI(api_key=SECONDARY_API_KEY)
else:  # pragma: no cover
    _client = None


PROMPT_INSTRUCTIONS = """
You are the secondary compliance adjudicator for DocGuard AI. Your job is to review the provided
document text (which is annotated with explicit page markers such as "=== Page 1 ===") and deliver a
clear, JSON-only verdict about its sensitivity.

When reading the snippet, look for personally identifiable information (PII), confidential internal
data, military or regulated schematics, or any unsafe / disallowed safety content.

Respond ONLY with valid JSON using this schema:
{
  "label": "Public" | "Confidential" | "Highly Sensitive" | "Unsafe",
  "confidence": 0.0-1.0,
  "rationale": "Short explanation that references the relevant page markers",
  "content_safety": "Content is safe for kids" | "Describe any safety concern",
  "critical_info": [ "List of sensitive elements you spotted (if any)" ],
  "needs_review": true | false,
  "citations": [
    { "page": 3, "evidence": "Quoted or paraphrased snippet" }
  ]
}

Set "needs_review" to true if your confidence is below 0.8, if you spotted any potentially unsafe
content, or if the document requires human validation.
""".strip()


def run_secondary_reasoning(doc_text: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError(
            "Secondary LLM client not configured. "
            "Set SECONDARY_LLM_API_KEY or OPENAI_API_KEY and install the openai package."
        )

    try:
        response = _client.chat.completions.create(
            model=SECONDARY_MODEL,
            temperature=SECONDARY_TEMPERATURE,
            top_p=SECONDARY_TOP_P,
            max_tokens=SECONDARY_MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": PROMPT_INSTRUCTIONS},
                {"role": "user", "content": doc_text},
            ],
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        data["model"] = SECONDARY_MODEL
        return data
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Secondary LLM call failed: {exc}") from exc
