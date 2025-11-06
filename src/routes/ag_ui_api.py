"""
AG-UI protocol bridge endpoints for the security orchestrator.

This blueprint exposes the existing security agents through the AG-UI
Server-Sent Events contract so that AG-UI clients (e.g. CopilotKit Dojo)
can collaborate with the Flask backend.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, Iterable, Optional

from flask import Blueprint, Response, request, stream_with_context

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

from src.routes import rag_api as rag_module


ag_ui_bp = Blueprint("ag_ui", __name__)


def _ensure_services_ready():
	"""
	Lazily initialise shared services from the RAG blueprint.

	The RAG blueprint already owns the lifecycle of the vector store and
	orchestrator. Re-using its initialiser keeps the dependency wiring in one
	place and avoids duplicating environment handling.
	"""
	rag_module.initialize_services()
	if rag_module.ai_orchestrator is None:
		raise RuntimeError("Security orchestrator is not available")


def _latest_user_message(input_payload: RunAgentInput) -> Optional[str]:
	for message in reversed(input_payload.messages):
		if message.role == "user" and message.content:
			return message.content
	return None


def _build_context(input_payload: RunAgentInput) -> Dict[str, str]:
	return {ctx.description: ctx.value for ctx in input_payload.context}


def _chunk_text(text: str, chunk_size: int = 400) -> Iterable[str]:
	for start in range(0, len(text), chunk_size):
		yield text[start : start + chunk_size]


@ag_ui_bp.route("/agentic_chat", methods=["POST"])
def agentic_chat():
	"""
	Primary AG-UI endpoint for chat-style interactions.
	"""
	_ensure_services_ready()

	payload = request.get_json(silent=True)
	if not payload:
		return Response(
			"Missing JSON payload",
			status=400,
			mimetype="text/plain",
		)

	try:
		run_input = RunAgentInput.model_validate(payload)
	except Exception as exc:  # pragma: no cover - defensive parsing
		return Response(f"Invalid AG-UI payload: {exc}", status=400, mimetype="text/plain")

	query = _latest_user_message(run_input)
	if not query:
		return Response("需要使用者訊息才能執行對話流程", status=400, mimetype="text/plain")

	context = _build_context(run_input)
	selected_agent = context.get("agent")
	multi_agent = context.get("multi_agent") == "true"

	if isinstance(run_input.forwarded_props, dict):
		selected_agent = selected_agent or run_input.forwarded_props.get("agent")
		if "multi_agent" in run_input.forwarded_props:
			multi_agent = bool(run_input.forwarded_props["multi_agent"])

	orchestrator = rag_module.ai_orchestrator
	assert orchestrator is not None  # 型別提示

	encoder = EventEncoder(accept=request.headers.get("accept"))
	thread_id = run_input.thread_id or str(uuid.uuid4())
	run_id = run_input.run_id or str(uuid.uuid4())
	message_id = str(uuid.uuid4())

	def generate():
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

		yield encoder.encode(TextMessageStartEvent(message_id=message_id, role="assistant"))

		for chunk in _chunk_text(response_text):
			yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta=chunk))

		yield encoder.encode(TextMessageEndEvent(message_id=message_id))

		yield encoder.encode(RunFinishedEvent(thread_id=thread_id, run_id=run_id, result=raw_result))

	headers = {
		"Content-Type": "text/event-stream",
		"Cache-Control": "no-cache",
		"X-Accel-Buffering": "no",
	}

	return Response(stream_with_context(generate()), status=200, headers=headers)
