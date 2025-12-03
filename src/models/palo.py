from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Index

from src.models.auth import db


JSONType = db.JSON


class PaloAltoLog(db.Model):
    """Normalized Palo Alto Networks log entry produced by the tagging pipeline."""

    __tablename__ = "palo_logs"

    id = db.Column(db.Integer, primary_key=True)
    log_uid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    event_time = db.Column(db.DateTime, nullable=True, index=True)
    log_type = db.Column(db.String(32), nullable=True, index=True)
    subtype = db.Column(db.String(64), nullable=True, index=True)
    src_ip = db.Column(db.String(45), nullable=True, index=True)
    src_port = db.Column(db.Integer, nullable=True)
    dst_ip = db.Column(db.String(45), nullable=True, index=True)
    dst_port = db.Column(db.Integer, nullable=True)
    protocol = db.Column(db.String(16), nullable=True)
    nat_src_ip = db.Column(db.String(45), nullable=True)
    nat_dst_ip = db.Column(db.String(45), nullable=True)
    action = db.Column(db.String(32), nullable=True, index=True)
    rule_name = db.Column(db.String(128), nullable=True, index=True)
    app = db.Column(db.String(128), nullable=True)
    threat_name = db.Column(db.String(255), nullable=True)
    threat_category = db.Column(db.String(128), nullable=True, index=True)
    severity = db.Column(db.String(32), nullable=True, index=True)
    direction = db.Column(db.String(16), nullable=True, index=True)
    user = db.Column(db.String(128), nullable=True, index=True)
    url = db.Column(db.Text, nullable=True)
    url_category = db.Column(db.String(128), nullable=True)
    session_id = db.Column(db.String(128), nullable=True, index=True)
    device_name = db.Column(db.String(128), nullable=True)
    vsys = db.Column(db.String(64), nullable=True)
    tags = db.Column(JSONType, nullable=False, default=list)
    extra = db.Column(JSONType, nullable=False, default=dict)
    raw_log = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_palo_logs_src_dst", "src_ip", "dst_ip"),
        Index("ix_palo_logs_time_severity", "event_time", "severity"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "log_uid": self.log_uid,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "log_type": self.log_type,
            "subtype": self.subtype,
            "src_ip": self.src_ip,
            "src_port": self.src_port,
            "dst_ip": self.dst_ip,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "nat_src_ip": self.nat_src_ip,
            "nat_dst_ip": self.nat_dst_ip,
            "action": self.action,
            "rule_name": self.rule_name,
            "app": self.app,
            "threat_name": self.threat_name,
            "threat_category": self.threat_category,
            "severity": self.severity,
            "direction": self.direction,
            "user": self.user,
            "url": self.url,
            "url_category": self.url_category,
            "session_id": self.session_id,
            "device_name": self.device_name,
            "vsys": self.vsys,
            "tags": self.tags or [],
            "extra": self.extra or {},
        }
