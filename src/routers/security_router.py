# routers/security_router.py
# 包裝成pydanticai 做成 tool / agent
from pydantic_ai import Agent, RunContext
from models.routing import RoutingDecision
from routers.router_core import router_decide

async def router_decision_tool(ctx: RunContext[None], question: str) -> RoutingDecision:
    decision = await router_decide(question)
    return RoutingDecision(**decision)

security_router_agent = Agent[None, RoutingDecision](
    model="azure:gpt-4o-mini",   # 或 openai:...
    system_prompt="你是資安路由器，請呼叫 router_decision_tool 來決策。",
    tools=[router_decision_tool],
)
