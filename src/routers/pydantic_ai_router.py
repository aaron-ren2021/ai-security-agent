from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.models.schemas import PydanticTextRequest

router = APIRouter(prefix="/api/pydantic", tags=["pydantic-ai"])

_coordinator = None
_analyze_callable = None
_fallback_available = False


@dataclass
class _SimpleRouteResult:
	target: str
	confidence: float


def _simple_route(query: str) -> _SimpleRouteResult:
	text = (query or "").lower()
	if any(k in text for k in ["帳號", "login", "mfa", "權限"]):
		return _SimpleRouteResult("account_security", 0.72)
	if any(k in text for k in ["攻擊", "威脅", "ioc", "入侵", "釣魚"]):
		return _SimpleRouteResult("threat_analysis", 0.75)
	if any(k in text for k in ["網路", "主機", "服務", "埠", "latency", "延遲"]):
		return _SimpleRouteResult("network_security", 0.68)
	return _SimpleRouteResult("general_response", 0.5)


def _lazy_import() -> bool:
	global _coordinator, _analyze_callable, _fallback_available
	if _coordinator is not None:
		return True
	try:
		from src.services.stable.multi_agent_multiround import coordinator, analyze

		_coordinator = coordinator
		_analyze_callable = analyze
		return True
	except Exception as exc:  # pragma: no cover - only executed when optional deps missing
		print(f"[pydantic_ai] 初始化失敗，使用 fallback: {exc}")
		_fallback_available = True
		return False


def _extract_text(payload: PydanticTextRequest) -> str:
	return payload.normalized_text()


@router.get("/health")
async def health():
	ok = _lazy_import()
	return {"ok": ok, "fallback": _fallback_available}


@router.post("/route")
async def route_only(payload: PydanticTextRequest):
	_lazy_import()  # even if it fails we still have fallback
	text = _extract_text(payload)
	if not text:
		raise HTTPException(status_code=400, detail="missing query")
	if _coordinator:
		try:
			route = _coordinator._route(text)  # pylint: disable=protected-access
			return {"route": json.loads(route.model_dump_json()), "fallback": False}
		except Exception as exc:
			raise HTTPException(status_code=500, detail=str(exc)) from exc
	result = _simple_route(text)
	return {
		"route": {"target": result.target, "confidence": result.confidence},
		"fallback": True,
	}


@router.post("/analyze")
async def analyze_full(payload: PydanticTextRequest):
	_lazy_import()
	text = _extract_text(payload)
	if not text:
		raise HTTPException(status_code=400, detail="missing query")
	if _analyze_callable and _coordinator:
		try:
			result = _analyze_callable(text)
			return {"success": True, "result": result, "fallback": False}
		except Exception as exc:
			raise HTTPException(status_code=500, detail=str(exc)) from exc
	route = _simple_route(text)
	return {
		"success": True,
		"fallback": True,
		"result": {
			"route": {"target": route.target, "confidence": route.confidence},
			"summary": "(fallback) 未載入完整協調器，僅提供簡易路由結果。",
			"steps": ["simple_route"],
		},
	}
