import json
from typing import Dict, Any
from .models import ClassificationResult, DetectorSignals, Citation
from .prompt_lib import get_prompt
from .llm_client import call_llm

TRUNCATE_CHARS = 1200

def _prepare_pages(pages: Dict[int, str]) -> Dict[int, str]:
    prepared = {}
    for page_num, text in sorted(pages.items()):
        snippet = (text or "").strip()
        if len(snippet) > TRUNCATE_CHARS:
            snippet = snippet[:TRUNCATE_CHARS].rsplit(" ", 1)[0] + " …"
        prepared[page_num] = snippet
    return prepared

def _run_prompt(name: str,
                pages: Dict[int, str],
                extra: Dict[str, Any] = None,
                override_pages: Dict[int, str] = None) -> Any:
    prompt_cfg = get_prompt(name)
    content_payload = {
        "pages": _prepare_pages(override_pages or pages),
        "page_count": len(pages),
        "extra": extra or {}
    }
    messages = [
        {"role": prompt_cfg["role"], "content": prompt_cfg["content"]},
        {"role": "user", "content": json.dumps(content_payload)}
    ]
    try:
        resp = call_llm(messages)
    except Exception as exc:
        # propagate a mock payload so downstream nodes can fall back gracefully
        return {"mock": True, "error": str(exc), "prompt_node": name}
    return resp  # expected to be JSON-like per prompt instructions

def classify_document(doc_id: str,
                      pages: Dict[int, str],
                      signals: DetectorSignals) -> ClassificationResult:
    prompt_errors = []
    summary_pages: Dict[int, str] = {}

    def _has_error(output: Any, node: str):
        if isinstance(output, dict) and output.get("mock"):
            prompt_errors.append(node)

    # Node 1: precheck
    precheck_out = _run_prompt("precheck", pages)
    _has_error(precheck_out, "precheck")
    if isinstance(precheck_out, list):
        for entry in precheck_out:
            if isinstance(entry, dict):
                page = entry.get("page")
                summary = entry.get("summary")
                if page and summary:
                    summary_pages[page] = summary

    # Node 2: PII-specific (only if needed)
    pii_out = None
    if signals.has_pii:
        pii_out = _run_prompt(
            "pii_scan",
            pages,
            extra={"detectors": signals.dict()},
            override_pages=summary_pages or None,
        )
        _has_error(pii_out, "pii_scan")

    # Node 3: unsafe scan (always if any pattern OR as safety net)
    unsafe_out = _run_prompt(
        "unsafe_scan",
        pages,
        extra={"detectors": signals.dict()},
        override_pages=summary_pages or None,
    )
    _has_error(unsafe_out, "unsafe_scan")

    # Node 4: confidentiality scan
    conf_out = _run_prompt(
        "confidentiality_scan",
        pages,
        extra={
            "detectors": signals.dict(),
            "precheck": precheck_out,
            "pii_scan": pii_out,
            "unsafe_scan": unsafe_out,
        },
        override_pages=summary_pages or None,
    )
    _has_error(conf_out, "confidentiality_scan")

    # Node 5: final decision: combine everything.
    final_out = _run_prompt(
        "final_decision",
        pages,
        extra={
            "detectors": signals.dict(),
            "precheck": precheck_out,
            "pii_scan": pii_out,
            "unsafe_scan": unsafe_out,
            "confidentiality_scan": conf_out,
        },
        override_pages=summary_pages or None,
    )
    _has_error(final_out, "final_decision")

    # Parse final_out (assuming LLM returns proper JSON per instructions).
    # Here we handle both real JSON or stubbed mock.
    if isinstance(final_out, dict) and final_out.get("mock"):
        # Fallback heuristic if using stub:
        final_category, secondary_tags, confidence, citations, explanation = (
            _fallback_decision(signals)
        )
    else:
        try:
            # if model returns as JSON string in "content" you’d parse here
            data = final_out if isinstance(final_out, dict) else json.loads(final_out)
            final_category = data["final_category"]
            secondary_tags = data.get("secondary_tags", [])
            confidence = float(data.get("confidence", 0.7))
            citations = [
                Citation(page=c["page"], snippet=c["snippet"])
                for c in data.get("citations", [])
            ]
            explanation = data.get("explanation", "")
        except Exception:
            final_category, secondary_tags, confidence, citations, explanation = (
                _fallback_decision(signals)
            )

<<<<<<< HEAD
    if signals.has_unsafe_pattern:
        requires_review = True
    elif final_category in ["Unsafe","Highly Sensitive"]:
        requires_review = True
    elif confidence < 0.7:
        requires_review = True
    else:
        requires_review = False
=======
    requires_review = (
        confidence < 0.75
        or signals.has_unsafe_pattern
        or bool(prompt_errors)
    )
>>>>>>> origin/main

    return ClassificationResult(
        doc_id=doc_id,
        final_category=final_category,  # type: ignore
        secondary_tags=secondary_tags,
        confidence=confidence,
        citations=citations,
        explanation=explanation,
        raw_signals=signals,
        llm_payload={"prompt_errors": prompt_errors} if prompt_errors else None,
        requires_review=requires_review,
    )

def _fallback_decision(signals: DetectorSignals):
    # Simple deterministic severity ladder
    if signals.has_unsafe_pattern:
        cat = "Unsafe"
        tags = ["Safety-Risk"]
        expl = "Unsafe keywords detected."
    elif signals.has_pii:
        cat = "Highly Sensitive"
        tags = ["PII"]
        expl = "PII patterns detected."
    elif signals.has_internal_markers:
        cat = "Confidential"
        tags = ["Internal"]
        expl = "Internal markers detected."
    else:
        cat = "Public"
        tags = []
        expl = "No sensitive markers found."
    citations = (signals.pii_hits or signals.unsafe_hits)[:3]
    return cat, tags, 0.7, citations, expl
