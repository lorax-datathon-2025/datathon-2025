import json
import os
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

try:
    from databricks import sql  # type: ignore
except ImportError:  # pragma: no cover
    sql = None  # type: ignore


def _enabled() -> bool:
    return all(
        [
            sql,
            os.getenv("DATABRICKS_SERVER_HOST"),
            os.getenv("DATABRICKS_HTTP_PATH"),
            os.getenv("DATABRICKS_ACCESS_TOKEN"),
        ]
    )


def _get_connection():
    return sql.connect(  # type: ignore[call-arg]
        server_hostname=os.getenv("DATABRICKS_SERVER_HOST"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN"),
    )


def _execute(
    query: str,
    params: Optional[Iterable[Any]] = None,
    *,
    return_exception: bool = False,
    suppress_log: bool = False,
):
    """Execute a query, optionally returning the triggering exception."""

    if not _enabled():
        return (True, None) if return_exception else True
    try:
        with _get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or [])
        return (True, None) if return_exception else True
    except Exception as exc:  # pragma: no cover
        if not suppress_log:
            print(f"[DB] Failed to execute query: {exc}")
        return (False, exc) if return_exception else False


def _ensure_review_queue_table() -> bool:
    """Create the review_queue table if it does not already exist."""

    ddl = """
        CREATE TABLE IF NOT EXISTS review_queue (
            doc_id STRING,
            status STRING,
            created_at TIMESTAMP,
            last_updated_at TIMESTAMP,
            reason_triggers STRING,
            assigned_to STRING,
            category STRING,
            confidence DOUBLE,
            priority STRING,
            resolution_notes STRING
        ) USING DELTA
    """
    success, _ = _execute(ddl, return_exception=True)
    return bool(success)


def insert_doc_record(
    doc_id: str,
    filename: str,
    status: str,
    page_count: int,
    image_count: int,
    legibility_score: Optional[float],
    source_path: str,
) -> None:
    _execute(
        """
        INSERT INTO docs (
            doc_id,
            filename,
            uploaded_at,
            status,
            page_count,
            image_count,
            legibility_score,
            source_path
        )
        VALUES (?, ?, current_timestamp(), ?, ?, ?, ?, ?)
        """,
        (
            doc_id,
            filename,
            status,
            page_count,
            image_count,
            legibility_score,
            source_path,
        ),
    )


def update_doc_record(
    doc_id: str,
    status: Optional[str] = None,
    page_count: Optional[int] = None,
    image_count: Optional[int] = None,
    legibility_score: Optional[float] = None,
) -> None:
    if not _enabled():
        return
    sets = []
    params: list[Any] = []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if page_count is not None:
        sets.append("page_count = ?")
        params.append(page_count)
    if image_count is not None:
        sets.append("image_count = ?")
        params.append(image_count)
    if legibility_score is not None:
        sets.append("legibility_score = ?")
        params.append(legibility_score)
    if not sets:
        return
    params.append(doc_id)
    query = f"UPDATE docs SET {', '.join(sets)} WHERE doc_id = ?"
    _execute(query, params)


def insert_classification_record(doc_id: str, result) -> None:
    if not _enabled():
        return

    citations_json = json.dumps([c.dict() for c in result.citations], ensure_ascii=False)
    primary_json = json.dumps(result.primary_analysis or {}, ensure_ascii=False)
    secondary_json = json.dumps(result.secondary_analysis or {}, ensure_ascii=False)
    summary_json = json.dumps(result.summary or {}, ensure_ascii=False)
    raw_signals_json = json.dumps(result.raw_signals.dict(), ensure_ascii=False)
    llm_payload_json = json.dumps(result.llm_payload or {}, ensure_ascii=False)
    dual_disagreements_json = (
        json.dumps(result.dual_llm_disagreements, ensure_ascii=False)
        if result.dual_llm_disagreements
        else None
    )
    secondary_tags_json = json.dumps(result.secondary_tags or [], ensure_ascii=False)

    insert_full = """
        INSERT INTO classifications (
            doc_id,
            classified_at,
            final_category,
            secondary_tags,
            confidence,
            explanation,
            citations,
            page_count,
            image_count,
            legibility_score,
            content_safety,
            requires_review,
            dual_llm_agreement,
            dual_llm_disagreements,
            primary_analysis,
            secondary_analysis,
            summary,
            raw_signals,
            llm_payload
        )
        VALUES (
            ?, current_timestamp(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """
    params_full = (
        doc_id,
        result.final_category,
        result.secondary_tags,
        result.confidence,
        result.explanation,
        citations_json,
        result.page_count,
        result.image_count,
        result.legibility_score,
        result.content_safety,
        result.requires_review,
        result.dual_llm_agreement,
        dual_disagreements_json,
        primary_json,
        secondary_json,
        summary_json,
        raw_signals_json,
        llm_payload_json,
    )

    success, error = _execute(
        insert_full, params_full, return_exception=True, suppress_log=True
    )
    if success or not error:
        return

    error_msg = str(error)
    if "UNRESOLVED_COLUMN" not in error_msg:
        return

    fallback_sql = """
        INSERT INTO classifications (
            doc_id,
            classified_at,
            final_category,
            secondary_tags,
            confidence
        )
        VALUES (?, current_timestamp(), ?, ?, ?)
    """
    _execute(
        fallback_sql,
        (
            doc_id,
            result.final_category,
            secondary_tags_json,
            result.confidence,
        ),
    )


def insert_audit_event(doc_id: str, event_type: str, payload: dict) -> None:
    _execute(
        """
        INSERT INTO audit_log (doc_id, event_time, event_type, payload)
        VALUES (?, current_timestamp(), ?, ?)
        """,
        (doc_id, event_type, json.dumps(payload, ensure_ascii=False)),
    )


def upsert_review_queue(
    doc_id: str,
    category: str,
    confidence: float,
    triggers: list[str],
    priority: str = "normal",
) -> None:
    if not _ensure_review_queue_table():
        return
    _execute(
        """
        MERGE INTO review_queue AS target
        USING (SELECT ? AS doc_id) AS source
        ON target.doc_id = source.doc_id
        WHEN MATCHED THEN UPDATE SET
            status = 'open',
            last_updated_at = current_timestamp(),
            reason_triggers = ?,
            category = ?,
            confidence = ?,
            priority = ?
        WHEN NOT MATCHED THEN INSERT (
            doc_id, status, created_at, last_updated_at, reason_triggers,
            assigned_to, category, confidence, priority
        )
        VALUES (?, 'open', current_timestamp(), current_timestamp(), ?, NULL, ?, ?, ?)
        """,
        (
            doc_id,
            json.dumps(triggers),
            category,
            confidence,
            priority,
            doc_id,
            json.dumps(triggers),
            category,
            confidence,
            priority,
        ),
    )


def close_review_item(doc_id: str, reviewer: str, resolution: str) -> None:
    if not _ensure_review_queue_table():
        return
    _execute(
        """
        UPDATE review_queue
        SET status = 'closed',
            assigned_to = ?,
            resolution_notes = ?,
            last_updated_at = current_timestamp()
        WHERE doc_id = ?
        """,
        (reviewer, resolution, doc_id),
    )


def _query_all(query: str, params: Optional[Iterable[Any]] = None) -> list[dict]:
    if not _enabled():
        return []
    try:
        with _get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or [])
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:  # pragma: no cover
        print(f"[DB] Failed to query: {exc}")
        return []


def list_documents(limit: int = 100) -> list[dict]:
    return _query_all(
        """
        SELECT doc_id, filename, uploaded_at, status, page_count,
               image_count, legibility_score, source_path
        FROM docs
        ORDER BY uploaded_at DESC
        LIMIT ?
        """,
        (limit,),
    )


def get_document_record(doc_id: str) -> Optional[dict]:
    rows = _query_all(
        """
        SELECT doc_id, filename, uploaded_at, status, page_count,
               image_count, legibility_score, source_path
        FROM docs
        WHERE doc_id = ?
        """,
        (doc_id,),
    )
    return rows[0] if rows else None


def list_classifications(doc_id: str, limit: int = 5) -> list[dict]:
    return _query_all(
        """
        SELECT *
        FROM classifications
        WHERE doc_id = ?
        ORDER BY classified_at DESC
        LIMIT ?
        """,
        (doc_id, limit),
    )


def list_audit_events(doc_id: str, limit: int = 20) -> list[dict]:
    return _query_all(
        """
        SELECT *
        FROM audit_log
        WHERE doc_id = ?
        ORDER BY event_time DESC
        LIMIT ?
        """,
        (doc_id, limit),
    )


def list_review_queue(status: str = "open", limit: int = 50) -> list[dict]:
    if not _ensure_review_queue_table():
        return []
    return _query_all(
        """
        SELECT *
        FROM review_queue
        WHERE status = ?
        ORDER BY priority DESC, created_at DESC
        LIMIT ?
        """,
        (status, limit),
    )


def get_summary() -> dict:
    status_rows = _query_all(
        "SELECT status, COUNT(*) AS count FROM docs GROUP BY status"
    )
    category_rows = _query_all(
        """
        SELECT final_category, COUNT(*) AS count
        FROM classifications
        GROUP BY final_category
        """
    )
    review_rows = _query_all(
        """
        SELECT requires_review, COUNT(*) AS count
        FROM classifications
        GROUP BY requires_review
        """
    )
    return {
        "by_status": status_rows,
        "by_category": category_rows,
        "by_requires_review": review_rows,
    }


def list_dashboard_documents(limit: int = 50) -> list[dict]:
    """
    Return the most recent documents along with their latest classification snapshot.
    """

    return _query_all(
        """
        WITH latest AS (
            SELECT
                doc_id,
                final_category,
                confidence,
                requires_review,
                content_safety,
                page_count,
                image_count,
                legibility_score,
                classified_at,
                ROW_NUMBER() OVER (PARTITION BY doc_id ORDER BY classified_at DESC) AS row_num
            FROM classifications
        )
        SELECT
            d.doc_id,
            d.filename,
            d.uploaded_at,
            d.status,
            COALESCE(latest.page_count, d.page_count) AS page_count,
            COALESCE(latest.image_count, d.image_count) AS image_count,
            COALESCE(latest.legibility_score, d.legibility_score) AS legibility_score,
            latest.final_category,
            latest.confidence,
            latest.requires_review,
            latest.content_safety,
            latest.classified_at
        FROM docs d
        LEFT JOIN latest
            ON latest.doc_id = d.doc_id
           AND latest.row_num = 1
        ORDER BY d.uploaded_at DESC
        LIMIT ?
        """,
        (limit,),
    )


def get_average_confidence() -> float:
    rows = _query_all("SELECT AVG(confidence) AS avg_confidence FROM classifications")
    if not rows:
        return 0.0
    avg = rows[0].get("avg_confidence")
    return float(avg) if avg is not None else 0.0


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes"}


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def _derive_counts(summary: dict, fallback_total: int, avg_confidence: float) -> dict:
    status_total = sum(row.get("count", 0) for row in summary.get("by_status", []))
    category_rows = {
        (row.get("final_category") or row.get("FINAL_CATEGORY") or ""): row.get(
            "count", 0
        )
        for row in summary.get("by_category", [])
    }
    review_rows = {
        str(row.get("requires_review")).strip().lower(): row.get("count", 0)
        for row in summary.get("by_requires_review", [])
    }
    flagged = category_rows.get("Unsafe", 0)
    needs_review = review_rows.get("true", 0)
    return {
        "total": status_total or fallback_total,
        "public": category_rows.get("Public", 0),
        "confidential": category_rows.get("Confidential", 0),
        "highlySensitive": category_rows.get("Highly Sensitive", 0),
        "unsafe": flagged,
        "needsReview": needs_review,
        "averageConfidence": round(avg_confidence * 100, 1),
    }


def get_dashboard_snapshot(limit: int = 50) -> dict:
    documents_raw = list_dashboard_documents(limit)
    summary = get_summary()
    avg_confidence = get_average_confidence()

    documents = []
    for row in documents_raw:
        final_category = row.get("final_category") or "Unclassified"
        confidence = row.get("confidence")
        confidence_value = float(confidence) if confidence is not None else None
        requires_review = _coerce_bool(row.get("requires_review"))
        documents.append(
            {
                "docId": row.get("doc_id"),
                "filename": row.get("filename") or row.get("doc_id"),
                "uploadedAt": _iso(row.get("uploaded_at")),
                "status": row.get("status"),
                "pageCount": row.get("page_count"),
                "imageCount": row.get("image_count"),
                "legibilityScore": row.get("legibility_score"),
                "finalCategory": final_category,
                "requiresReview": requires_review,
                "confidence": confidence_value,
                "contentSafety": row.get("content_safety"),
                "classifiedAt": _iso(row.get("classified_at")),
                "unsafe": final_category == "Unsafe",
            }
        )

    counts = _derive_counts(summary, len(documents), avg_confidence)

    return {
        "documents": documents,
        "counts": counts,
        "summary": summary,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "limit": limit,
    }
