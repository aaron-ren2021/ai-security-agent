from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from sqlalchemy import or_

from src.models.palo import PaloAltoLog
from src.services.postgres_hybrid_service import PostgresHybridSearchService


class ScanResult(BaseModel):
    severity: str = Field(..., description="IOC severity classification: low, medium, high, or critical.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="System confidence for the severity classification.")
    sources: List[str] = Field(default_factory=list, description="Supporting evidence titles/content snippets.")
    first_seen: Optional[str] = Field(None, description="ISO timestamp for earliest sighting if available.")
    last_seen: Optional[str] = Field(None, description="ISO timestamp for latest sighting if available.")
    requires_approval: bool = Field(
        default=False,
        description="Set to True when severity is high or critical and a human analyst must approve follow-up actions.",
    )
    log_matches: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relevant Palo Alto log entries that matched the IOC.",
    )


_SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def _lookup_postgres(query: str, top_k: int = 5):
    """Fetch related context from the Postgres hybrid search tool."""
    service = PostgresHybridSearchService.get_instance()
    if not service:
        return []
    try:
        return service.search_query(query, top_k=top_k)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Postgres hybrid lookup failed: {exc}")
        return []


def _estimate_severity(results) -> str:
    if not results:
        return "medium"
    best_score = max(getattr(r, "hybrid_score", 0.0) for r in results)
    if best_score >= 0.85:
        return "critical"
    if best_score >= 0.65:
        return "high"
    if best_score >= 0.4:
        return "medium"
    return "low"


def _extract_sources(results) -> List[str]:
    sources = []
    for res in results:
        title = getattr(res, "title", None)
        if title:
            sources.append(title)
        else:
            content = getattr(res, "content", "")
            if content:
                sources.append(content[:120])
        if len(sources) >= 5:
            break
    return sources


def _ioc_in_text(ioc: str, value: Optional[str]) -> bool:
    if not ioc or not value:
        return False
    return ioc.lower() in value.lower()


def _ioc_in_tags(ioc: str, tags: Optional[List[Any]]) -> bool:
    if not ioc or not tags:
        return False
    lowered = ioc.lower()
    for tag in tags:
        if isinstance(tag, str) and lowered in tag.lower():
            return True
    return False


def _lookup_palo_logs(ioc: str, limit: int = 20):
    try:
        indicator_like = f"%{ioc}%"
        query = (
            PaloAltoLog.query.filter(
                or_(
                    PaloAltoLog.src_ip == ioc,
                    PaloAltoLog.dst_ip == ioc,
                    PaloAltoLog.session_id == ioc,
                    PaloAltoLog.user == ioc,
                    PaloAltoLog.threat_name.ilike(indicator_like),
                    PaloAltoLog.rule_name.ilike(indicator_like),
                    PaloAltoLog.url.ilike(indicator_like),
                )
            )
            .order_by(PaloAltoLog.event_time.desc(), PaloAltoLog.received_at.desc())
            .limit(limit)
        )
        rows = query.all()
        if rows:
            return rows

        fallback_rows = (
            PaloAltoLog.query.order_by(PaloAltoLog.event_time.desc(), PaloAltoLog.received_at.desc())
            .limit(limit * 3)
            .all()
        )
        matches = []
        for row in fallback_rows:
            if (
                _ioc_in_text(ioc, row.src_ip)
                or _ioc_in_text(ioc, row.dst_ip)
                or _ioc_in_text(ioc, row.user)
                or _ioc_in_text(ioc, row.rule_name)
                or _ioc_in_text(ioc, row.threat_name)
                or _ioc_in_text(ioc, row.url)
                or _ioc_in_tags(ioc, row.tags)
            ):
                matches.append(row)
            if len(matches) >= limit:
                break
        return matches
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Palo Alto log lookup failed: {exc}")
        return []


def _serialize_log_row(row: PaloAltoLog) -> Dict[str, Any]:
    return {
        "id": row.id,
        "time": (row.event_time or row.received_at).isoformat() if row.event_time or row.received_at else None,
        "src_ip": row.src_ip,
        "dst_ip": row.dst_ip,
        "action": row.action,
        "app": row.app,
        "rule": row.rule_name,
        "severity": row.severity,
        "threat": row.threat_name,
        "tags": row.tags or [],
    }


security_agent = Agent(
    instructions=(
        "You are the security investigation agent for the AI Security platform.\n"
        "- Always begin by querying the Postgres hybrid knowledge base to gather context "
        "about the user's prompt or indicator.\n"
        "- Review the evidence before deciding whether the scan_ioc tool needs to be invoked. "
        "Only call the tool when you have confirmed that the IOC requires deeper inspection.\n"
        "- When scan_ioc reports severity high or critical, mark the finding for human-in-the-loop "
        "approval and remind the operator that a human must review the action plan."
    ),
)


@security_agent.tool
async def scan_ioc(ctx: RunContext[None], ioc: str) -> ScanResult:
    """Analyze an IOC using structured evidence and determine severity."""
    results = _lookup_postgres(ioc, top_k=5)
    log_rows = _lookup_palo_logs(ioc, limit=15)
    severity = _estimate_severity(results)
    severity_rank = _SEVERITY_ORDER.index(severity)
    requires_approval = severity_rank >= _SEVERITY_ORDER.index("high")

    sources = _extract_sources(results)
    now = datetime.utcnow().isoformat()
    log_matches = [_serialize_log_row(row) for row in log_rows]
    timestamps = [
        ts
        for ts in (row.event_time or row.received_at for row in log_rows)
        if ts is not None
    ]
    if timestamps:
        first_seen = min(timestamps).isoformat()
        last_seen = max(timestamps).isoformat()
    elif results:
        first_seen = last_seen = now
    else:
        first_seen = last_seen = None

    scan_result = ScanResult(
        severity=severity,
        confidence=0.9 if severity_rank >= 2 else 0.65,
        sources=sources,
        first_seen=first_seen,
        last_seen=last_seen,
        requires_approval=requires_approval,
        log_matches=log_matches,
    )

    if requires_approval:
        ctx.log("High severity IOC detected. Human approval required before remediation.")

    return scan_result
