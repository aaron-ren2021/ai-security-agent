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


def _build_retrieval_snapshot(raw_result: Dict[str, any], multi_agent: bool, selected_agent: Optional[str], overridden: bool) -> Optional[Dict[str, any]]:
	"""萃取可視化的檢索 / 來源資訊供前端快速渲染。

	返回格式:
	{
	  'mode': 'single' | 'multi',
	  'agent': 'threat_analysis',
	  'overridden': True/False,
	  'sources': [ { 'agent': 'threat_analysis', 'type': 'relevant_threats', 'items': [...] }, ... ]
	}
	"""
	if not isinstance(raw_result, dict):
		return None

	if multi_agent:
		results = raw_result.get('multi_agent_results')
		if not isinstance(results, dict):
			return None
		sources = []
		for agent_name, agent_payload in results.items():
			if not isinstance(agent_payload, dict):
				continue
			for key in ('relevant_threats', 'relevant_rules', 'relevant_knowledge'):
				if key in agent_payload and agent_payload[key]:
					sources.append({
						'agent': agent_name,
						'type': key,
						'count': len(agent_payload.get(key, []) or []),
						'items': agent_payload.get(key, [])
					})
		if not sources:
			return None
		return {
			'mode': 'multi',
			'agent': selected_agent,
			'overridden': overridden,
			'sources': sources,
		}
	else:
		# 單一 agent 結果
		sources = []
		for key in ('relevant_threats', 'relevant_rules', 'relevant_knowledge'):
			if key in raw_result and raw_result[key]:
				sources.append({
					'agent': raw_result.get('routed_agent') or selected_agent,
					'type': key,
					'count': len(raw_result.get(key, []) or []),
					'items': raw_result.get(key, [])
				})
		if not sources:
			return None
		return {
			'mode': 'single',
			'agent': raw_result.get('routed_agent') or selected_agent,
			'overridden': overridden,
			'sources': sources,
		}


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

	# 支援前端以 /agent <name> 指令臨時覆寫 agent，例如: /agent threat_analysis 最近的釣魚攻擊趨勢
	if query.startswith("/agent"):
		parts = query.split()
		if len(parts) >= 2:
			selected_agent = parts[1]
			# 移除指令後的真正查詢內容；若沒有則給一個 placeholder
			query = " ".join(parts[2:]) or "請進行分析"
			# 也把覆寫資訊放入 context 供後續紀錄
			context_override_flag = True
	else:
		context_override_flag = False

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

		# 在主回答開始前，先傳送一個檢索快照事件，方便前端顯示「引用來源 / 風險資訊」等
		try:
			retrieval_payload = _build_retrieval_snapshot(raw_result, multi_agent=multi_agent, selected_agent=selected_agent, overridden=context_override_flag)
			if retrieval_payload:
				# 用特殊前綴標記，前端可攔截 [[RETRIEVAL_SNAPSHOT]] 進行 JSON 解析
				marker = "[[RETRIEVAL_SNAPSHOT]]" + json.dumps(retrieval_payload, ensure_ascii=False)
				yield encoder.encode(TextMessageStartEvent(message_id=message_id, role="assistant"))
				yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta=marker))
				# 後續的主回答再使用新的 message id，避免混淆
				message_id_main = str(uuid.uuid4())
				yield encoder.encode(TextMessageStartEvent(message_id=message_id_main, role="assistant"))
				for chunk in _chunk_text(response_text):
					yield encoder.encode(TextMessageContentEvent(message_id=message_id_main, delta=chunk))
				yield encoder.encode(TextMessageEndEvent(message_id=message_id_main))
				yield encoder.encode(RunFinishedEvent(thread_id=thread_id, run_id=run_id, result=raw_result))
				return
		except Exception:  # 靜默忽略快照錯誤，退回原本流程
			pass

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
