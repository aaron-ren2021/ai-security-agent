from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

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
    severity = _estimate_severity(results)
    severity_rank = _SEVERITY_ORDER.index(severity)
    requires_approval = severity_rank >= _SEVERITY_ORDER.index("high")

    sources = _extract_sources(results)
    now = datetime.utcnow().isoformat()
    scan_result = ScanResult(
        severity=severity,
        confidence=0.9 if severity_rank >= 2 else 0.65,
        sources=sources,
        first_seen=now if results else None,
        last_seen=now if results else None,
        requires_approval=requires_approval,
    )

    if requires_approval:
        ctx.log("High severity IOC detected. Human approval required before remediation.")

    return scan_result
