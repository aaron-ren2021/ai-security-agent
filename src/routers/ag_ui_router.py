from __future__ import annotations

"""
FastAPI router that exposes the AG-UI streaming endpoints.
"""

import json
import uuid
from typing import Any, Dict, Iterable, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from ag_ui.core.events import (
	RunErrorEvent,
	RunFinishedEvent,
	RunStartedEvent,
	TextMessageContentEvent,
	TextMessageEndEvent,
	TextMessageStartEvent,
)
from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder

from src.routers import rag_router as rag_module

router = APIRouter(prefix="/api/agui", tags=["ag-ui"])

_SSE_HEADERS = {
	"Cache-Control": "no-cache",
	"X-Accel-Buffering": "no",
}


def _ensure_services_ready():
	rag_module.init_vector_and_agents()
	if rag_module.ai_orchestrator is None:
		raise HTTPException(status_code=503, detail="Security orchestrator is not available")


def _latest_user_message(input_payload: RunAgentInput) -> Optional[str]:
	for message in reversed(input_payload.messages):
		if message.role == "user" and message.content:
			return message.content
	return None


def _build_context(input_payload: RunAgentInput) -> Dict[str, str]:
	return {item.description: item.value for item in input_payload.context}


def _chunk_text(text: str, chunk_size: int = 400) -> Iterable[str]:
	for start in range(0, len(text), chunk_size):
		yield text[start : start + chunk_size]


def _build_retrieval_snapshot(
	raw_result: Dict[str, Any],
	multi_agent: bool,
	selected_agent: Optional[str],
	overridden: bool,
) -> Optional[Dict[str, Any]]:
	if not isinstance(raw_result, dict):
		return None
	if multi_agent:
		results = raw_result.get("multi_agent_results")
		if not isinstance(results, dict):
			return None
		sources = []
		for agent_name, agent_payload in results.items():
			if not isinstance(agent_payload, dict):
				continue
			for key in ("relevant_threats", "relevant_rules", "relevant_knowledge"):
				if key in agent_payload and agent_payload[key]:
					sources.append(
						{
							"agent": agent_name,
							"type": key,
							"count": len(agent_payload.get(key, []) or []),
							"items": agent_payload.get(key, []),
						}
					)
		if not sources:
			return None
		return {
			"mode": "multi",
			"agent": selected_agent,
			"overridden": overridden,
			"sources": sources,
		}
	sources = []
	for key in ("relevant_threats", "relevant_rules", "relevant_knowledge"):
		if key in raw_result and raw_result[key]:
			sources.append(
				{
					"agent": raw_result.get("routed_agent") or selected_agent,
					"type": key,
					"count": len(raw_result.get(key, []) or []),
					"items": raw_result.get(key, []),
				}
			)
	if not sources:
		return None
	return {
		"mode": "single",
		"agent": raw_result.get("routed_agent") or selected_agent,
		"overridden": overridden,
		"sources": sources,
	}


def _validate_input(payload: Dict[str, Any]) -> RunAgentInput:
	try:
		return RunAgentInput.model_validate(payload)
	except ValidationError as exc:  # pragma: no cover - defensive branch
		raise HTTPException(status_code=400, detail=f"Invalid AG-UI payload: {exc}") from exc


@router.post("/agentic_chat")
async def agentic_chat(request: Request):
	payload = await request.json()
	run_input = _validate_input(payload)
	query = _latest_user_message(run_input)
	if not query:
		raise HTTPException(status_code=400, detail="需要使用者訊息才能執行對話流程")

	context_override_flag = False
	if query.startswith("/agent"):
		parts = query.split()
		if len(parts) >= 2:
			selected_agent = parts[1]
			query = " ".join(parts[2:]) or "請進行分析"
			context_override_flag = True
	else:
		selected_agent = None

	context = _build_context(run_input)
	selected_agent = selected_agent or context.get("agent")
	multi_agent = context.get("multi_agent") == "true"

	if isinstance(run_input.forwarded_props, dict):
		selected_agent = selected_agent or run_input.forwarded_props.get("agent")
		if "multi_agent" in run_input.forwarded_props:
			multi_agent = bool(run_input.forwarded_props["multi_agent"])

	_ensure_services_ready()
	orchestrator = rag_module.ai_orchestrator

	assert orchestrator is not None  # mypy hint

	encoder = EventEncoder(accept=request.headers.get("accept"))
	thread_id = run_input.thread_id or str(uuid.uuid4())
	run_id = run_input.run_id or str(uuid.uuid4())

	def generate():
		message_id = str(uuid.uuid4())
		yield encoder.encode(RunStartedEvent(thread_id=thread_id, run_id=run_id))

		try:
			if multi_agent:
				raw_result = orchestrator.multi_agent_analysis(query, context=context)
				response_text = raw_result.get("synthesis") or json.dumps(raw_result, ensure_ascii=False)
			else:
				raw_result = orchestrator.analyze_query(query, context=context, agent_name=selected_agent)
				response_text = raw_result.get("analysis") or raw_result.get("response")
				if not response_text:
					response_text = json.dumps(raw_result, ensure_ascii=False)
		except Exception as exc:  # pragma: no cover - keep streaming on failure
			yield encoder.encode(RunErrorEvent(message=str(exc)))
			return

		try:
			retrieval_payload = _build_retrieval_snapshot(
				raw_result,
				multi_agent=multi_agent,
				selected_agent=selected_agent,
				overridden=context_override_flag,
			)
			if retrieval_payload:
				marker = "[[RETRIEVAL_SNAPSHOT]]" + json.dumps(retrieval_payload, ensure_ascii=False)
				yield encoder.encode(TextMessageStartEvent(message_id=message_id, role="assistant"))
				yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta=marker))
				message_id_main = str(uuid.uuid4())
				yield encoder.encode(TextMessageStartEvent(message_id=message_id_main, role="assistant"))
				for chunk in _chunk_text(response_text):
					yield encoder.encode(TextMessageContentEvent(message_id=message_id_main, delta=chunk))
				yield encoder.encode(TextMessageEndEvent(message_id=message_id_main))
				yield encoder.encode(RunFinishedEvent(thread_id=thread_id, run_id=run_id, result=raw_result))
				return
		except Exception:  # pragma: no cover - fallback to standard streaming
			pass

		yield encoder.encode(TextMessageStartEvent(message_id=message_id, role="assistant"))
		for chunk in _chunk_text(response_text):
			yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta=chunk))
		yield encoder.encode(TextMessageEndEvent(message_id=message_id))
		yield encoder.encode(RunFinishedEvent(thread_id=thread_id, run_id=run_id, result=raw_result))

	return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/awp")
async def awp_endpoint(request: Request):
	payload = await request.json()
	run_input = _validate_input(payload)
	query = _latest_user_message(run_input)
	if not query:
		raise HTTPException(status_code=400, detail="需要使用者訊息才能執行對話流程")

	encoder = EventEncoder(accept=request.headers.get("accept"))
	thread_id = run_input.thread_id or str(uuid.uuid4())
	run_id = run_input.run_id or str(uuid.uuid4())
	message_id = str(uuid.uuid4())

	def generate():
		yield encoder.encode(RunStartedEvent(thread_id=thread_id, run_id=run_id))
		yield encoder.encode(TextMessageStartEvent(message_id=message_id, role="assistant"))
		for chunk in _chunk_text(query, chunk_size=10):
			yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta=chunk))
		yield encoder.encode(TextMessageEndEvent(message_id=message_id))
		yield encoder.encode(
			RunFinishedEvent(
				thread_id=thread_id,
				run_id=run_id,
				result={"mode": "awp-echo", "length": len(query)},
			)
		)

	return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)
