import os, json
import google.generativeai as genai

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")
genai.configure(api_key=API_KEY)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
MODEL = genai.GenerativeModel(
    MODEL_NAME,
    generation_config={
        "response_mime_type": "application/json",
        "temperature": 0.2,
        "top_p": 0.9,
        "max_output_tokens": 1024,
    },
)

def call_llm(messages):
    formatted = [
        {"role": m["role"], "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    try:
        resp = MODEL.generate_content(formatted)
        text = resp.candidates[0].content[0].text
        return json.loads(text)
    except Exception as exc:
        # optional: log resp, request ID, etc.
        raise RuntimeError(f"Gemini call failed: {exc}")