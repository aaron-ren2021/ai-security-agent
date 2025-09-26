# tools/router_tool.py
from pydantic_ai import Tool, RunContext
from models.routing import RoutingDecision
from router import router_decide  

async def router_decision_tool(ctx: RunContext[None], question: str) -> RoutingDecision:
    decision = await router_decide(question)
    return RoutingDecision(**decision)

router_tool = Tool(
    name="router_decision",
    description="根據使用者輸入，做出路由決策 (target + confidence)",
    func=router_decision_tool,
)
