from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from src.models.auth import db
from src.models.palo import PaloAltoLog


_SEVERITY_ORDER = ["informational", "low", "medium", "high", "critical"]
_SEVERITY_RANK = {name: idx for idx, name in enumerate(_SEVERITY_ORDER)}


def _severity_rank(value: Optional[str]) -> int:
    if not value:
        return _SEVERITY_RANK["low"]
    return _SEVERITY_RANK.get(value.lower(), _SEVERITY_RANK["low"])


class PaloLogInput(BaseModel):
    """Normalized payload from Filebeat/Kafka before persistence."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    log_uid: Optional[str] = Field(None, description="Unique identifier from upstream pipeline.")
    received_at: Optional[datetime] = Field(
        None,
        validation_alias=AliasChoices("@timestamp", "received_at"),
    )
    event_time: Optional[datetime] = Field(
        None,
        validation_alias=AliasChoices("event_time", "generated_time"),
    )
    log_type: Optional[str] = Field(None, validation_alias=AliasChoices("type", "log_type"))
    subtype: Optional[str] = None
    src_ip: Optional[str] = Field(None, validation_alias=AliasChoices("src_ip", "source.ip", "source_ip"))
    src_port: Optional[int] = None
    dst_ip: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("dst_ip", "destination.ip", "destination_ip"),
    )
    dst_port: Optional[int] = None
    protocol: Optional[str] = None
    nat_src_ip: Optional[str] = None
    nat_dst_ip: Optional[str] = None
    action: Optional[str] = Field(None, validation_alias=AliasChoices("action", "event.action"))
    rule_name: Optional[str] = None
    app: Optional[str] = None
    threat_name: Optional[str] = None
    threat_category: Optional[str] = None
    severity: Optional[str] = Field(None, validation_alias=AliasChoices("severity", "threat.severity"))
    direction: Optional[str] = Field(None, validation_alias=AliasChoices("direction", "network.direction"))
    user: Optional[str] = None
    url: Optional[str] = None
    url_category: Optional[str] = None
    session_id: Optional[str] = None
    device_name: Optional[str] = None
    vsys: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)
    raw_log: Optional[str] = Field(None, validation_alias=AliasChoices("raw", "event.original"))

    def resolved_uid(self) -> str:
        if self.log_uid:
            return self.log_uid
        base = self.session_id or self.raw_log
        if not base:
            serialized = json.dumps(
                self.model_dump(
                    exclude_none=True,
                    exclude={"tags", "extra"},
                    by_alias=True,
                    mode="json",
                    sort_keys=True,
                ),
                sort_keys=True,
            )
            base = serialized
        return hashlib.sha1(base.encode("utf-8")).hexdigest()

    def merged_extra(self) -> Dict[str, Any]:
        merged = dict(self.extra)
        if self.model_extra:
            merged.update(self.model_extra)
        return merged


class PaloTagRule(BaseModel):
    """Declarative rule describing when to add tags to a log entry."""

    name: str
    add_tags: List[str]
    actions: Optional[List[str]] = None
    directions: Optional[List[str]] = None
    users: Optional[List[str]] = None
    apps: Optional[List[str]] = None
    threat_categories: Optional[List[str]] = None
    min_severity: Optional[str] = None
    severities: Optional[List[str]] = None
    log_types: Optional[List[str]] = None
    subtypes: Optional[List[str]] = None
    contains: Optional[List[str]] = Field(
        default=None,
        description="Case-insensitive substrings to match in threat name / URL.",
    )

    def _matches_list(self, value: Optional[str], candidates: Optional[Sequence[str]]) -> bool:
        if not candidates:
            return True
        if not value:
            return False
        return value.lower() in {c.lower() for c in candidates}

    def applies(self, record: PaloLogInput) -> bool:
        if not self._matches_list(record.action, self.actions):
            return False
        if not self._matches_list(record.direction, self.directions):
            return False
        if not self._matches_list(record.user, self.users):
            return False
        if not self._matches_list(record.app, self.apps):
            return False
        if not self._matches_list(record.threat_category, self.threat_categories):
            return False
        if not self._matches_list(record.log_type, self.log_types):
            return False
        if not self._matches_list(record.subtype, self.subtypes):
            return False
        if self.severities and not self._matches_list(record.severity, self.severities):
            return False
        if self.min_severity:
            if _severity_rank(record.severity) < _severity_rank(self.min_severity):
                return False
        if self.contains:
            haystack = " ".join(
                filter(
                    None,
                    [
                        record.threat_name,
                        record.url,
                        record.rule_name,
                        record.extra.get("event_description") if isinstance(record.extra, dict) else None,
                    ],
                )
            ).lower()
            if not all(token.lower() in haystack for token in self.contains):
                return False
        return True


class PaloLogTagger:
    """Applies tag rules to normalized Palo Alto log entries."""

    def __init__(self, rules: Sequence[PaloTagRule]) -> None:
        self.rules = list(rules)

    def tag_record(self, record: PaloLogInput) -> List[str]:
        tags: Set[str] = set(record.tags or [])
        for rule in self.rules:
            if rule.applies(record):
                tags.update(rule.add_tags)
        return sorted(tags)


def load_tag_rules(path: str | Path) -> List[PaloTagRule]:
    with open(path, "r", encoding="utf-8") as f:
        raw_rules = yaml.safe_load(f) or []
    return [PaloTagRule.model_validate(item) for item in raw_rules]


def ingest_palo_log(payload: Dict[str, Any], *, tagger: Optional[PaloLogTagger] = None, commit: bool = True) -> PaloAltoLog:
    record = PaloLogInput.model_validate(payload)
    if tagger:
        tags = tagger.tag_record(record)
    else:
        tags = sorted(set(record.tags or []))
    log_uid = record.resolved_uid()
    received_at = record.received_at or datetime.utcnow()
    event_time = record.event_time or received_at
    extra_payload = record.merged_extra()

    existing = PaloAltoLog.query.filter_by(log_uid=log_uid).first()
    attributes = dict(
        log_uid=log_uid,
        received_at=received_at,
        event_time=event_time,
        log_type=record.log_type,
        subtype=record.subtype,
        src_ip=record.src_ip,
        src_port=record.src_port,
        dst_ip=record.dst_ip,
        dst_port=record.dst_port,
        protocol=record.protocol,
        nat_src_ip=record.nat_src_ip,
        nat_dst_ip=record.nat_dst_ip,
        action=record.action,
        rule_name=record.rule_name,
        app=record.app,
        threat_name=record.threat_name,
        threat_category=record.threat_category,
        severity=record.severity,
        direction=record.direction,
        user=record.user,
        url=record.url,
        url_category=record.url_category,
        session_id=record.session_id,
        device_name=record.device_name,
        vsys=record.vsys,
        tags=tags,
        extra=extra_payload,
        raw_log=record.raw_log,
    )

    if existing:
        for key, value in attributes.items():
            setattr(existing, key, value)
        obj = existing
    else:
        obj = PaloAltoLog(**attributes)
        db.session.add(obj)

    if commit:
        db.session.commit()
    return obj


def ingest_palo_logs_bulk(
    payloads: Iterable[Dict[str, Any]],
    *,
    tagger: Optional[PaloLogTagger] = None,
    batch_size: int = 200,
) -> int:
    """Bulk-ingest Kafka batches efficiently."""

    count = 0
    for payload in payloads:
        ingest_palo_log(payload, tagger=tagger, commit=False)
        count += 1
        if count % batch_size == 0:
            db.session.commit()
    db.session.commit()
    return count
