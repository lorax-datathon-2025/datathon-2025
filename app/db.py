import json
import os
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


def _execute(query: str, params: Optional[Iterable[Any]] = None) -> None:
    if not _enabled():
        return
    try:
        with _get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or [])
    except Exception as exc:  # pragma: no cover
        print(f"[DB] Failed to execute query: {exc}")


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

    _execute(
        """
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
        """,
        (
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
        ),
    )

