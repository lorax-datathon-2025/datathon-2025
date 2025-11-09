# This is the correct ending for classify_document function
# Copy this to replace lines 233-268 in orchestrator.py

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
