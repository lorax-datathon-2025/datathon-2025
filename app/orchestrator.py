import json
import os
from typing import Any, Dict, List, Optional

from .llm_client import call_llm, call_llm_with_images
from .models import ClassificationResult, Citation, DetectorSignals
from .prompt_lib import get_prompt, get_prompt_flow
from .secondary_llm import run_secondary_reasoning

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
                      signals: DetectorSignals,
                      image_count: int = 0,
                      images_data: List[Dict] = None,
                      legibility_score: Optional[float] = None) -> ClassificationResult:
    if images_data is None:
        images_data = []

    prompt_errors: List[str] = []
    summary_pages: Dict[int, str] = {}
    flow_outputs: Dict[str, Any] = {}
    audit_citations: List[Citation] = []
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

        if not _output_has_error(output):
            audit_citations.extend(_collect_citations(node_id, output))
        else:
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
    citations: List[Citation] = []

    if not final_out or _output_has_error(final_out):
        final_category, secondary_tags, confidence, citations, explanation = _fallback_decision(signals)
        if citations:
            audit_citations.extend(citations)
        citations = _dedupe_citations(audit_citations) if audit_citations else citations
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
            final_decision_citations = [
                Citation(
                    page=c.get("page"),
                    snippet=c.get("snippet", ""),
                    image_index=c.get("image_index"),
                    region=c.get("region"),
                    source="final_decision",
                )
                for c in data.get("citations", [])
                if isinstance(c, dict) and c.get("snippet")
            ]
            if final_decision_citations:
                audit_citations.extend(final_decision_citations)
            citations = (
                _dedupe_citations(audit_citations)
                if audit_citations
                else final_decision_citations
            )
            explanation = data.get("explanation", "")

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
            if citations:
                audit_citations.extend(citations)
            citations = _dedupe_citations(audit_citations) if audit_citations else citations
            prompt_tree_result = {
                "final_category": final_category,
                "secondary_tags": secondary_tags,
                "confidence": confidence,
                "citations": [c.dict() for c in citations],
                "explanation": explanation,
                "source": "fallback",
            }

    primary_analysis = _build_primary_analysis(
        prompt_tree_result, os.getenv("GEMINI_MODEL", "models/gemini-1.5-pro-latest")
    )

    document_text = _format_pages_for_secondary(pages)
    try:
        secondary_raw = run_secondary_reasoning(document_text)
    except Exception as exc:
        print(f"Secondary LLM error: {exc}")
        secondary_raw = {"error": str(exc)}
    secondary_analysis = _structure_secondary_analysis(secondary_raw)

    agreement_score, disagreements = _compute_llm_agreement(primary_analysis, secondary_analysis)

    secondary_label = (
        secondary_analysis.get("label")
        if not secondary_analysis.get("error")
        else None
    )
    final_category_to_use = _resolve_category_conflict(
        primary_analysis.get("category"),
        secondary_label,
    )

    if final_category_to_use == secondary_label and not secondary_analysis.get("error"):
        final_confidence = secondary_analysis.get("confidence", confidence)
        final_explanation = secondary_analysis.get("explanation", explanation)
        final_tags = secondary_analysis.get("critical_info") or secondary_tags
    else:
        final_confidence = confidence
        final_explanation = explanation
        final_tags = secondary_tags

    content_safety = secondary_analysis.get("content_safety") or "Content is safe for kids"

    review_triggers = _collect_review_triggers(
        final_confidence,
        signals,
        prompt_errors,
        agreement_score,
        disagreements,
        secondary_analysis,
    )
    requires_review = bool(review_triggers)

    summary = _build_summary_block(
        final_category_to_use,
        final_confidence,
        final_tags,
        requires_review,
        review_triggers,
        agreement_score,
        disagreements,
        content_safety,
        legibility_score,
    )

    llm_payload = {
        "prompt_errors": prompt_errors if prompt_errors else [],
        "prompt_flow": flow_outputs,
        "primary_raw": prompt_tree_result,
        "secondary_llm": secondary_analysis.get("raw"),
        "dual_llm_validation": {
            "agreement_score": agreement_score,
            "disagreements": disagreements,
            "resolution_strategy": "most_restrictive",
            "secondary_model": secondary_analysis.get("model"),
        },
    }

    primary_analysis_view = {k: v for k, v in primary_analysis.items() if v is not None}
    secondary_analysis_view = {
        k: v
        for k, v in secondary_analysis.items()
        if k in {"model", "label", "confidence", "explanation", "content_safety", "critical_info", "needs_review", "citations"}
        and v is not None
    }

    return ClassificationResult(
        doc_id=doc_id,
        final_category=final_category_to_use,
        secondary_tags=final_tags,
        confidence=final_confidence,
        explanation=final_explanation,
        page_count=len(pages),
        image_count=image_count,
        content_safety=content_safety,
        citations=citations,
        raw_signals=signals,
        llm_payload=llm_payload,
        requires_review=requires_review,
        dual_llm_agreement=agreement_score,
        dual_llm_disagreements=disagreements if disagreements else None,
        primary_analysis=primary_analysis_view,
        secondary_analysis=secondary_analysis_view,
        summary=summary,
        legibility_score=legibility_score,
    )


def _build_primary_analysis(tree_result: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    return {
        "engine": tree_result.get("source", "prompt_tree"),
        "model": model_name,
        "category": tree_result.get("final_category"),
        "secondary_tags": tree_result.get("secondary_tags", []),
        "confidence": tree_result.get("confidence"),
        "explanation": tree_result.get("explanation", ""),
        "citations": tree_result.get("citations", []),
    }


def _structure_secondary_analysis(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base_raw: Dict[str, Any] = raw or {}
    if not isinstance(base_raw, dict):
        base_raw = {"raw_value": base_raw}

    analysis: Dict[str, Any] = {
        "raw": base_raw,
        "model": base_raw.get("model") or os.getenv("SECONDARY_LLM_MODEL", "gpt-4o-mini"),
    }
    if not base_raw or base_raw.get("error"):
        analysis.update(
            {
                "label": None,
                "confidence": 0.0,
                "explanation": base_raw.get("error") or "Secondary LLM unavailable",
                "content_safety": None,
                "critical_info": [],
                "needs_review": True,
                "citations": [],
                "error": base_raw.get("error") or "secondary_llm_error",
            }
        )
        return analysis

    label = base_raw.get("label") or base_raw.get("Sensitivity")
    confidence = float(base_raw.get("confidence", base_raw.get("Confidence", 0.7)))
    explanation = base_raw.get("rationale") or base_raw.get("Reasoning") or ""
    content_safety = base_raw.get("content_safety") or base_raw.get("Content_safety")
    critical_info = base_raw.get("critical_info") or base_raw.get("Critical_info") or []
    if not isinstance(critical_info, list):
        critical_info = [str(critical_info)]
    citations = base_raw.get("citations") or base_raw.get("Citations") or []
    if not isinstance(citations, list):
        citations = []
    needs_review = bool(base_raw.get("needs_review") or base_raw.get("Requires_review") or (confidence < 0.8))

    analysis.update(
        {
            "label": label,
            "confidence": confidence,
            "explanation": explanation,
            "content_safety": content_safety,
            "critical_info": critical_info,
            "needs_review": needs_review,
            "citations": citations,
            "error": None,
        }
    )
    return analysis


def _collect_review_triggers(
    final_confidence: float,
    signals: DetectorSignals,
    prompt_errors: List[str],
    agreement_score: float,
    disagreements: List[str],
    secondary_analysis: Dict[str, Any],
) -> List[str]:
    triggers: List[str] = []
    if final_confidence < 0.8:
        triggers.append("low_confidence")
    if signals.has_unsafe_pattern:
        triggers.append("unsafe_detector")
    if prompt_errors:
        triggers.append("prompt_errors")
    if agreement_score < 0.7 or disagreements:
        triggers.append("llm_disagreement")
    if secondary_analysis.get("needs_review"):
        triggers.append("secondary_llm_flag")
    return triggers


def _build_summary_block(
    final_category: Optional[str],
    final_confidence: float,
    secondary_tags: List[str],
    requires_review: bool,
    review_triggers: List[str],
    agreement_score: float,
    disagreements: List[str],
    content_safety: str,
    legibility_score: Optional[float],
) -> Dict[str, Any]:
    summary = {
        "decision": {
            "category": final_category,
            "confidence": final_confidence,
            "secondary_tags": secondary_tags,
        },
        "review": {"required": requires_review, "triggers": review_triggers},
        "agreement": {"score": agreement_score, "disagreements": disagreements},
        "content_safety": content_safety,
    }
    if legibility_score is not None:
        summary["legibility"] = {"average_score": legibility_score}
    return summary


def _format_pages_for_secondary(pages: Dict[int, str], max_chars: int = 8000) -> str:
    chunks: List[str] = []
    used = 0
    for page_num, text in sorted(pages.items()):
        header = f"=== Page {page_num} ===\n"
        body = (text or "").strip()
        if len(body) > TRUNCATE_CHARS:
            body = body[:TRUNCATE_CHARS].rsplit(" ", 1)[0] + " …"
        entry = header + body + "\n"
        if used + len(entry) > max_chars:
            remaining = max_chars - used
            if remaining > 0:
                chunks.append(entry[:remaining])
            break
        chunks.append(entry)
        used += len(entry)
        if used >= max_chars:
            break
    return "\n".join(chunks)


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


def _collect_citations(node_id: str, output: Any) -> List[Citation]:
    citations: List[Citation] = []
    if output is None:
        return citations
    if isinstance(output, dict) and output.get("mock"):
        return citations
    try:
        if node_id == "pii_scan":
            for span in output.get("pii_spans", []):
                if not isinstance(span, dict):
                    continue
                page = span.get("page")
                text = span.get("text")
                if text:
                    citations.append(
                        Citation(page=page, snippet=text, source=node_id)
                    )
        elif node_id == "unsafe_scan":
            for cite in output.get("citations", []):
                if not isinstance(cite, dict):
                    continue
                page = cite.get("page")
                text = cite.get("text")
                if text:
                    citations.append(
                        Citation(page=page, snippet=text, source=node_id)
                    )
        elif node_id == "confidentiality_scan":
            for cite in output.get("citations", []):
                if not isinstance(cite, dict):
                    continue
                page = cite.get("page")
                snippet = cite.get("snippet")
                if snippet:
                    citations.append(
                        Citation(page=page, snippet=snippet, source=node_id)
                    )
        elif node_id == "final_decision":
            for cite in output.get("citations", []):
                if not isinstance(cite, dict):
                    continue
                snippet = cite.get("snippet")
                if snippet:
                    citations.append(
                        Citation(
                            page=cite.get("page"),
                            snippet=snippet,
                            image_index=cite.get("image_index"),
                            region=cite.get("region"),
                            source=node_id,
                        )
                    )
        elif node_id == "image_analysis":
            for finding in output.get("findings", []):
                if not isinstance(finding, dict):
                    continue
                description = finding.get("description")
                if not description:
                    continue
                regions = finding.get("regions_of_concern") or []
                region_text = ", ".join(regions) if regions else None
                citations.append(
                    Citation(
                        page=finding.get("page"),
                        snippet=description,
                        image_index=finding.get("image_index"),
                        region=region_text,
                        source=node_id,
                    )
                )
    except Exception as exc:
        print(f"Warning: unable to extract citations for node '{node_id}': {exc}")
    return citations


def _dedupe_citations(citations: List[Citation]) -> List[Citation]:
    seen = set()
    unique: List[Citation] = []
    for cite in citations:
        snippet_key = (cite.snippet or "").strip()
        key = (
            cite.page,
            cite.image_index,
            (cite.region or "").strip(),
            (cite.source or ""),
            snippet_key[:120],
        )
        if key not in seen:
            seen.add(key)
            unique.append(cite)
    return unique


def _compute_llm_agreement(primary_analysis: Dict[str, Any], secondary_analysis: Dict[str, Any]) -> tuple:
    """Compare two LLM outputs and return (agreement_score, list_of_disagreements)."""
    if secondary_analysis.get("error"):
        return 0.0, ["secondary_llm_error"]

    disagreements: List[str] = []
    score_components: List[float] = []

    pt_cat = primary_analysis.get("category", "")
    sec_cat = secondary_analysis.get("label", "")
    if pt_cat and sec_cat and pt_cat == sec_cat:
        score_components.append(1.0)
    else:
        score_components.append(0.0)
        disagreements.append(f"category: primary={pt_cat}, secondary={sec_cat}")

    pt_conf = float(primary_analysis.get("confidence", 0.7) or 0.7)
    sec_conf = float(secondary_analysis.get("confidence", 0.7) or 0.7)
    if abs(pt_conf - sec_conf) < 0.2:
        score_components.append(1.0)
    else:
        score_components.append(0.5)
        disagreements.append(f"confidence_gap: {abs(pt_conf - sec_conf):.2f}")

    agreement_score = sum(score_components) / len(score_components)
    return agreement_score, disagreements


def _resolve_category_conflict(cat1: Optional[str], cat2: Optional[str] = None) -> Optional[str]:
    """Resolve conflicting categories by choosing the more restrictive one.
    Priority: Unsafe > Highly Sensitive > Confidential > Public
    """
    if not cat1:
        return cat2
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
