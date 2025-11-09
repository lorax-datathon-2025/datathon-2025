import json
from typing import Dict, Any, List
from .models import ClassificationResult, DetectorSignals, Citation
from .prompt_lib import get_prompt
from .llm_client import call_llm, call_llm_with_images
import google.generativeai as genai
import os, json, re

TRUNCATE_CHARS = 1200

def get_gemini_reasoning(doc_text: str):
    """Call Gemini to generate structured reasoning about the document."""
    try:
        # API is already configured in llm_client
        model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash-exp")
        model = genai.GenerativeModel(model_name)

        # Safety settings to allow analysis of potentially unsafe content
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUAL", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

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

        response = model.generate_content(prompt, safety_settings=safety_settings)
        
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
    prompt_errors = []
    summary_pages: Dict[int, str] = {}
    image_analysis_out = None

    def _has_error(output: Any, node: str):
        if isinstance(output, dict) and output.get("mock"):
            prompt_errors.append(node)
    
    def _dedupe_citations(citations: List[Citation]) -> List[Citation]:
        """Remove duplicate citations based on page and snippet similarity."""
        seen = set()
        unique = []
        for cite in citations:
            # Create a normalized key (page + first 100 chars of snippet)
            key = (cite.page, cite.snippet[:100].strip())
            if key not in seen:
                seen.add(key)
                unique.append(cite)
        return unique

    # Node 0: Image analysis (if images present)
    if images_data and len(images_data) > 0:
        try:
            prompt_cfg = get_prompt("image_analysis")
            prompt_text = prompt_cfg["content"]
            image_analysis_out = call_llm_with_images(prompt_text, images_data)
        except Exception as exc:
            print(f"Image analysis error: {exc}")
            image_analysis_out = {"mock": True, "error": str(exc), "prompt_node": "image_analysis"}
            _has_error(image_analysis_out, "image_analysis")

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
            "image_analysis": image_analysis_out,
        },
        override_pages=summary_pages or None,
    )
    _has_error(final_out, "final_decision")

    # Track all categories detected across nodes for multi-category scenarios
    detected_categories = set()
    
    # Check unsafe scan
    if unsafe_out and isinstance(unsafe_out, dict) and unsafe_out.get("unsafe_found"):
        detected_categories.add("Unsafe")
    
    # Check confidentiality scan
    if conf_out and isinstance(conf_out, dict):
        primary_cat = conf_out.get("primary_category")
        if primary_cat:
            detected_categories.add(primary_cat)
        if conf_out.get("is_unsafe"):
            detected_categories.add("Unsafe")
    
    # Check image analysis
    if image_analysis_out and not image_analysis_out.get("mock"):
        for finding in image_analysis_out.get("findings", []):
            sensitivity = finding.get("sensitivity")
            if sensitivity:
                detected_categories.add(sensitivity)

    # Parse final_out (assuming LLM returns proper JSON per instructions).
    # Here we handle both real JSON or stubbed mock.
    if isinstance(final_out, dict) and final_out.get("mock"):
        # Fallback heuristic if using stub:
        final_category, secondary_tags, confidence, citations, explanation = (
            _fallback_decision(signals)
        )
    else:
        try:
            # if model returns as JSON string in "content" you'd parse here
            data = final_out if isinstance(final_out, dict) else json.loads(final_out)
            final_category = data["final_category"]
            secondary_tags = data.get("secondary_tags", [])
            confidence = float(data.get("confidence", 0.7))
            citations = [
                Citation(page=c["page"], snippet=c["snippet"])
                for c in data.get("citations", [])
            ]
            # Deduplicate citations to remove duplicates from node aggregation
            citations = _dedupe_citations(citations)
            explanation = data.get("explanation", "")
            
            # Add all detected categories to secondary_tags if multiple categories apply
            # This allows TC5 to show both "Unsafe" and "Confidential"
            if len(detected_categories) > 1:
                # Remove the final_category from detected set to get other applicable categories
                other_categories = detected_categories - {final_category}
                # Remove "Public" if there are any higher-sensitivity categories
                # Public is the default and shouldn't be shown alongside Confidential/Highly Sensitive/Unsafe
                if other_categories - {"Public"}:
                    other_categories = other_categories - {"Public"}
                # Replace secondary_tags with ONLY the other category names (no thematic tags)
                secondary_tags = list(other_categories)
            
            # Add image findings to citations if present
            if image_analysis_out and not image_analysis_out.get("mock"):
                for finding in image_analysis_out.get("findings", []):
                    if finding.get("regions_of_concern") or finding.get("identifiable_elements"):
                        snippet = f"[Image {finding['image_index']}] {finding['description']}"
                        
                        # Add identifiable elements (serial numbers, part numbers, etc.)
                        if finding.get("identifiable_elements"):
                            identifiers = finding["identifiable_elements"]
                            if identifiers:
                                snippet += f" - Identifiable Elements: {', '.join(identifiers)}"
                        
                        # Add regions of concern
                        if finding.get("regions_of_concern"):
                            regions = finding["regions_of_concern"]
                            if regions:
                                snippet += f" - Regions: {', '.join(regions)}"
                        
                        citations.append(Citation(page=finding["page"], snippet=snippet))
        except Exception as e:
            print(f"Error parsing final_out: {e}")
            final_category, secondary_tags, confidence, citations, explanation = (
                _fallback_decision(signals)
            )

    """ if signals.has_unsafe_pattern:
        requires_review = True
    elif final_category in ["Unsafe","Highly Sensitive"]:
        requires_review = True
    elif confidence < 0.7:
        requires_review = True
    else:
        requires_review = False """
    
    # Store prompt tree results (LLM #1)
    prompt_tree_result = {
        "final_category": final_category,
        "secondary_tags": secondary_tags,
        "confidence": confidence,
        "citations": citations,
        "explanation": explanation,
        "source": "prompt_tree"
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
