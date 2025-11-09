import json
import os
import re
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from .llm_client import SAFETY_SETTINGS, call_llm, call_llm_with_images
from .models import ClassificationResult, Citation, DetectorSignals
from .prompt_lib import get_prompt, get_prompt_flow

TRUNCATE_CHARS = 1200

def get_gemini_reasoning(doc_text: str):
    """Call Gemini to generate structured reasoning about the document."""
    try:
        # API is already configured in llm_client
        model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash-exp")
        model = genai.GenerativeModel(model_name)

        prompt = f"""
        You are an AI document analyst for a compliance and safety classification system.
        
        IMPORTANT: You are ANALYZING content for safety violations, not creating harmful content.
        Your job is to DETECT and CLASSIFY potentially unsafe material so it can be flagged for review.
        
        Review the text below and respond ONLY in valid JSON with this structure. 
            -Critical information is any sensitive data.
            -Sensitivity
                1.	Sensitive/Highly Sensitive: Content that includes PII like SSNs, account/credit card numbers, and proprietary schematics (e.g., defense or next‑gen product designs of military equipment).  
                2.	Confidential: Internal communications and business documents, customer details (names, addresses), and non-public operational content.
                3.	Public: Marketing materials, product brochures, public website content, generic images.
            -Reasoning: Tell us why you pick the sentivity by giving us like "Cite pages containing only public marketing statements; confirm no PII or confidential details." or "Cite the field(s) containing SSN or other PII; show redaction suggestions if supported."
            -Confidence: give us a rating 0-1 of how confident you are about the rating of the sensitivity.
            - Content Safety: Evaluated for Child Safety and should not include Hate speech, exploitative, violent, criminal, political news or cyber-threat content.
                - If safe say "Content is safe for kids"
                - If unsafe, DESCRIBE the safety violations found (e.g., "Contains violent imagery", "Contains hate speech targeting [group]", "Contains explicit content")
:
        {{
        "Critical_info": [string],
        "Sensitivity": "Public" | "Confidential" | "Highly Sensitive",
        "Reasoning": string,
        "Confidence": decimal,
        "Content_safety": string
        }}


        Text:
        {doc_text[:5000]}
        """

        response = model.generate_content(prompt, safety_settings=SAFETY_SETTINGS)
        
        # Check if response was blocked by safety filters
        if not response.candidates:
            return {"error": "Gemini blocked by safety filters (no candidates returned)"}
        
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        
        # Check if blocked by safety
        if finish_reason not in (None, 1, "STOP"):
            safety_ratings = getattr(candidate, "safety_ratings", [])
            return {
                "error": f"Gemini blocked output (finish_reason={finish_reason})",
                "safety_ratings": str(safety_ratings)
            }
        
        raw = response.text.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            return json.loads(match.group(0)) if match else {"error": "Could not parse Gemini JSON", "raw": raw}
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}
    

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
                      signals: DetectorSignals,
                      image_count: int = 0,
                      images_data: List[Dict] = None) -> ClassificationResult:
    if images_data is None:
        images_data = []

    prompt_errors: List[str] = []
    summary_pages: Dict[int, str] = {}
    flow_outputs: Dict[str, Any] = {}
    flow = get_prompt_flow()
    final_node_id: Optional[str] = None

    for node in flow:
        node_id = node["id"]

        if not _should_run_node(node, signals, images_data):
            continue
        if not _dependencies_ready(node, flow_outputs):
            continue

        try:
            if node.get("runner") == "multimodal":
                if not images_data:
                    continue
                prompt_cfg = get_prompt(node["prompt"])
                output = call_llm_with_images(prompt_cfg["content"], images_data)
            else:
                extra_payload = {
                    "detectors": signals.dict(),
                    "prior_results": flow_outputs,
                    "node_id": node_id,
                }
                extra_payload.update(node.get("extra", {}))
                override_pages = summary_pages if node.get("use_summary_pages") and summary_pages else None
                output = _run_prompt(
                    node["prompt"],
                    pages,
                    extra=extra_payload,
                    override_pages=override_pages,
                )
        except Exception as exc:
            print(f"Prompt node '{node_id}' error: {exc}")
            output = {"mock": True, "error": str(exc), "prompt_node": node_id}

        flow_outputs[node_id] = output

        if _output_has_error(output):
            prompt_errors.append(node_id)
            if node.get("stop_on_error", True):
                final_node_id = final_node_id or node_id
                break

        if node.get("collect_summary"):
            _update_summary_pages(output, summary_pages)

        if _stop_conditions_met(node, output):
            final_node_id = final_node_id or node_id
            break

        if node.get("final_node"):
            final_node_id = node_id
            break

    if final_node_id is None:
        for node in reversed(flow):
            node_id = node.get("id")
            if node_id and node_id in flow_outputs:
                final_node_id = node_id
                break

    final_out = flow_outputs.get(final_node_id) if final_node_id else None
    image_analysis_out = flow_outputs.get("image_analysis")

    if not final_out or _output_has_error(final_out):
        final_category, secondary_tags, confidence, citations, explanation = _fallback_decision(signals)
        prompt_tree_result = {
            "final_category": final_category,
            "secondary_tags": secondary_tags,
            "confidence": confidence,
            "citations": [c.dict() for c in citations],
            "explanation": explanation,
            "source": "fallback",
        }
    else:
        try:
            data = final_out if isinstance(final_out, dict) else json.loads(final_out)
            final_category = data["final_category"]
            secondary_tags = data.get("secondary_tags", [])
            confidence = float(data.get("confidence", 0.7))
            citations = [
                Citation(page=c["page"], snippet=c["snippet"])
                for c in data.get("citations", [])
            ]
            citations = _dedupe_citations(citations)
            explanation = data.get("explanation", "")

            if image_analysis_out and not _output_has_error(image_analysis_out):
                for finding in image_analysis_out.get("findings", []):
                    if finding.get("regions_of_concern"):
                        snippet = f"[Image {finding['image_index']}] {finding['description']}"
                        if finding.get("regions_of_concern"):
                            snippet += f" - Regions: {', '.join(finding['regions_of_concern'])}"
                        citations.append(
                            Citation(page=finding.get("page", 0), snippet=snippet)
                        )
            citations = _dedupe_citations(citations)

            prompt_tree_result = {
                "final_category": final_category,
                "secondary_tags": secondary_tags,
                "confidence": confidence,
                "citations": [c.dict() for c in citations],
                "explanation": explanation,
                "source": "prompt_tree",
            }
        except Exception as exc:
            print(f"Error parsing final_out: {exc}")
            final_category, secondary_tags, confidence, citations, explanation = _fallback_decision(signals)
            prompt_tree_result = {
                "final_category": final_category,
                "secondary_tags": secondary_tags,
                "confidence": confidence,
                "citations": [c.dict() for c in citations],
                "explanation": explanation,
                "source": "fallback",
            }

    # Run second LLM opinion (LLM #2: get_gemini_reasoning)
    document_text = "\n".join(pages.values())
    try:
        gemini_result = get_gemini_reasoning(document_text)
    except Exception as e:
        print(f"Error in get_gemini_reasoning: {e}")
        gemini_result = {"error": str(e)}


    # Compare both LLM outputs and calculate agreement
    agreement_score, disagreements = _compute_llm_agreement(prompt_tree_result, gemini_result)
    
    # Decision: Use the more restrictive classification if there's disagreement
    final_category_to_use = _resolve_category_conflict(
        prompt_tree_result["final_category"],
        gemini_result.get("Sensitivity") if "error" not in gemini_result else None
    )
    
    # Use data from the LLM that made the final decision
    if final_category_to_use == gemini_result.get("Sensitivity") and "error" not in gemini_result:
        final_confidence = gemini_result.get("Confidence", confidence)
        final_explanation = gemini_result.get("Reasoning", explanation)
        final_tags = gemini_result.get("Critical_info", secondary_tags) if isinstance(gemini_result.get("Critical_info"), list) else secondary_tags
    else:
        final_confidence = confidence
        final_explanation = explanation
        final_tags = secondary_tags

    # Determine if review is required
    requires_review = (
        final_confidence < 0.8
        or signals.has_unsafe_pattern
        or bool(prompt_errors)
        or agreement_score < 0.7  # Flag if LLMs disagree significantly
        or len(disagreements) > 0
    )

    # Build llm_payload with both LLM outputs
    llm_payload = {
        "prompt_errors": prompt_errors if prompt_errors else [],
        "prompt_tree": prompt_tree_result,
        "prompt_flow": flow_outputs,
        "gemini": gemini_result,
        "dual_llm_validation": {
            "agreement_score": agreement_score,
            "disagreements": disagreements,
            "resolution_strategy": "most_restrictive"
        }
    }

    return ClassificationResult(
        doc_id=doc_id,
        final_category=final_category_to_use,
        secondary_tags=final_tags,
        confidence=final_confidence,
        explanation=final_explanation,
        page_count=len(pages),
        image_count=image_count,
        content_safety=gemini_result.get("Content_safety", "Content is safe for kids") if "error" not in gemini_result else "Content is safe for kids",
        citations=citations,
        raw_signals=signals,
        llm_payload=llm_payload,
        requires_review=requires_review,
        dual_llm_agreement=agreement_score,
        dual_llm_disagreements=disagreements if disagreements else None
    )


def _should_run_node(node_cfg: Dict[str, Any], signals: DetectorSignals, images_data: List[Dict]) -> bool:
    conditions = node_cfg.get("conditions") or {}
    if conditions.get("has_images") and not images_data:
        return False

    for attr in conditions.get("signals_true", []):
        if not getattr(signals, attr, False):
            return False

    for attr in conditions.get("signals_false", []):
        if getattr(signals, attr, False):
            return False

    return True


def _dependencies_ready(node_cfg: Dict[str, Any], outputs: Dict[str, Any]) -> bool:
    deps = node_cfg.get("depends_on") or []
    return all(dep in outputs for dep in deps)


def _output_has_error(output: Any) -> bool:
    return isinstance(output, dict) and output.get("mock")


def _update_summary_pages(output: Any, summary_pages: Dict[int, str]) -> None:
    if isinstance(output, list):
        for entry in output:
            if not isinstance(entry, dict):
                continue
            page = entry.get("page")
            summary = entry.get("summary")
            if page and summary:
                summary_pages[page] = summary


def _stop_conditions_met(node_cfg: Dict[str, Any], output: Any) -> bool:
    conditions = node_cfg.get("stop_if") or []
    if not conditions:
        return False
    for cond in conditions:
        field = cond.get("path") or cond.get("field")
        if not field:
            continue
        value = _extract_path_value(output, field)
        if "equals" in cond:
            if value == cond["equals"]:
                return True
        elif value:
            return True
    return False


def _extract_path_value(payload: Any, path: str) -> Any:
    if payload is None:
        return None
    current = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


def _dedupe_citations(citations: List[Citation]) -> List[Citation]:
    seen = set()
    unique: List[Citation] = []
    for cite in citations:
        key = (cite.page, cite.snippet[:100].strip())
        if key not in seen:
            seen.add(key)
            unique.append(cite)
    return unique


def _compute_llm_agreement(prompt_tree_result: Dict[str, Any], gemini_result: Dict[str, Any]) -> tuple:
    """Compare two LLM outputs and return (agreement_score, list_of_disagreements)."""
    if "error" in gemini_result:
        return 0.0, ["gemini_error"]
    
    disagreements = []
    score_components = []
    
    # Compare categories
    pt_cat = prompt_tree_result.get("final_category", "")
    gem_cat = gemini_result.get("Sensitivity", "")
    if pt_cat == gem_cat:
        score_components.append(1.0)
    else:
        score_components.append(0.0)
        disagreements.append(f"category: prompt_tree={pt_cat}, gemini={gem_cat}")
    
    # Compare confidence (within 0.2 is considered agreement)
    pt_conf = prompt_tree_result.get("confidence", 0.7)
    gem_conf = gemini_result.get("Confidence", 0.7)
    if abs(pt_conf - gem_conf) < 0.2:
        score_components.append(1.0)
    else:
        score_components.append(0.5)
        disagreements.append(f"confidence_gap: {abs(pt_conf - gem_conf):.2f}")
    
    # Overall agreement score
    agreement_score = sum(score_components) / len(score_components)
    
    return agreement_score, disagreements


def _resolve_category_conflict(cat1: str, cat2: str = None) -> str:
    """Resolve conflicting categories by choosing the more restrictive one.
    Priority: Unsafe > Highly Sensitive > Confidential > Public
    """
    if not cat2:
        return cat1
    
    priority = {
        "Unsafe": 4,
        "Highly Sensitive": 3,
        "Confidential": 2,
        "Public": 1
    }
    
    return cat1 if priority.get(cat1, 0) >= priority.get(cat2, 0) else cat2


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
