# 全面 PydanticAI 版本 ,# orchestration / workflow
# - Router 與每個下游專家都是 PydanticAI Agent
# - 交棒走 router.tool handoff，並用 usage=ctx.usage 讓用量回灌到父 run
# - 多輪 routing、fallback、120字摘要
# - __main__ 直接走 analyze() demo
# - 直接呼叫llm 當作router 給出信心分數決定專家agent

import os
import json
import time
from enum import Enum
from typing import Literal, Optional, List, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, UsageLimits, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.azure import AzureProvider

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

# Azure AI Search 整合
from src.services.stable.azure_ai_search import AzureAISearchExperimental, AzureSearchConfig
from src.tools.azure_aisearch_tool import azure_search_tool, AzureSearchToolInput, AzureSearchToolOutput

load_dotenv()

# ========== Env 檢查 ==========
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
REQUIRED_ENVS = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "OPENAI_API_VERSION"]
missing = [k for k in ["AZURE_OPENAI_DEPLOYMENT", "AZURE_AI_PROJECT_ENDPOINT", *REQUIRED_ENVS] if not os.getenv(k)]
if missing:
    raise RuntimeError(f"缺少必要環境變數: {', '.join(missing)}")

# Azure AI Search 環境變數（可選）
AZURE_SEARCH_SERVICE_NAME = os.getenv("AZURE_SEARCH_SERVICE_NAME")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents")

# ========== 規則與常數 ==========
ROUTER_INSTRUCTIONS = os.getenv(
    "ROUTER_INSTRUCTIONS",
    (
        "你是資安路由器，只輸出 JSON(target, confidence)。\n"
        "規則：\n"
        "- 有攻擊者/IOC/TTP/入侵跡象 → threat_analysis\n"
        "- 有主機/埠/服務/版本/弱掃/誤設 → network_security\n"
        "- 有帳號/密碼/MFA/權限/登入異常 → account_security\n"
        "- 模糊或閒聊 → general_response\n"
        "confidence 介於 0~1；若極度不確定，target=unknown。"
    ),
)
SUMMARIZER_INSTRUCTIONS = (
    "請產出 JSON，格式為 {\"summary\": \"不超過120字的繁中摘要\", \"concluded\": 布林}。"
    "有明確處置建議/結論時 concluded=true；否則 false。"
)

CONF_THRESHOLD = float(os.getenv("ROUTER_CONF_THRESHOLD", "0.55"))
_max_rounds_raw = os.getenv("ROUTER_MAX_ROUNDS", "2")
try:
    MAX_ROUNDS = int(_max_rounds_raw)
except ValueError:
    MAX_ROUNDS = 3

# 專家 Azure Agent IDs（可在 .env 覆蓋）
AGENT_IDS = {
    "threat_analysis": os.getenv("AGENT_THREAT_ID", "asst_wQTilJKeeNzL6dKTGXG5ynEW"),
    "network_security": os.getenv("AGENT_NETWORK_ID", "asst_Blv8Anlvv0FfP5bG7e19kGFU"),
    "account_security": os.getenv("AGENT_ACCOUNT_ID", "asst_89bKLUBlHjIFTRe6xqcejT8q"),
    "general_response": os.getenv("AGENT_GENERAL_ID", "asst_UIt2UKGS0cpTclQrOVm1XEfi"),
}

# ========== 型別 ==========
class AgentType(str, Enum):
    THREAT_ANALYSIS = "threat_analysis"
    NETWORK_SECURITY = "network_security"
    ACCOUNT_SECURITY = "account_security"
    GENERAL_RESPONSE = "general_response"
    UNKNOWN = "unknown"

class Route(BaseModel):
    target: Literal["threat_analysis", "network_security", "account_security", "general_response", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)

class SpecialistResult(BaseModel):
    target: str
    agent_id: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None
    latency_s: Optional[float] = None
    search_results: Optional[List[Dict[str, Any]]] = None  # 新增：搜尋結果
    knowledge_used: bool = False  # 新增：是否使用了知識庫

class OrchestratedOutput(BaseModel):
    route: Route
    result: SpecialistResult
    steps: List[str] = Field(default_factory=list)
    summary: Optional[str] = None

class SumOut(BaseModel):
    summary: str
    concluded: bool  # 這輪是否已有清楚結論/建議

# ========== 共用 LLM 與 Azure Project Client ==========
base_model = OpenAIChatModel(DEPLOYMENT, provider=AzureProvider())
project = AIProjectClient(credential=DefaultAzureCredential(), endpoint=AI_PROJECT_ENDPOINT)

# ========== Azure AI Search 初始化 ==========
search_client = None
if AZURE_SEARCH_SERVICE_NAME:
    try:
        search_config = AzureSearchConfig(
            service_name=AZURE_SEARCH_SERVICE_NAME,
            api_key=AZURE_SEARCH_API_KEY,
            index_name=AZURE_SEARCH_INDEX_NAME,
            use_semantic_search=True
        )
        search_client = AzureAISearchExperimental(search_config)
        print(f"✓ Azure AI Search 已初始化: {AZURE_SEARCH_SERVICE_NAME}/{AZURE_SEARCH_INDEX_NAME}")
    except Exception as e:
        print(f"⚠️ Azure AI Search 初始化失敗: {e}")
        search_client = None
else:
    print("ℹ️ 未設定 AZURE_SEARCH_SERVICE_NAME，跳過 Azure AI Search 初始化")

# ========== Azure 呼叫封裝（供下游 Agent 的 tool 使用） ==========
def _call_azure_agent(agent_type: str, text: str, thread_id: Optional[str] = None, search_results: Optional[List[Dict[str, Any]]] = None) -> SpecialistResult:
    """呼叫 Azure Agent，可選擇性傳入搜尋結果以增強回應。"""
    start = time.time()
    agent_id = AGENT_IDS.get(agent_type)
    if not agent_id:
        return SpecialistResult(target=agent_type, error=f"Unknown agent_type {agent_type}")
    
    try:
        ag = project.agents.get_agent(agent_id)
        # 重用 thread_id；沒有就新建
        thread = project.agents.threads.create() if not thread_id else type("T", (), {"id": thread_id})
        
        # 如果有搜尋結果，加入到提示中
        enhanced_text = text
        if search_results:
            knowledge_context = "\n".join([
                f"【參考文件】 {doc.get('title', 'Unknown')}: {doc.get('content', '')[:200]}..."
                for doc in search_results[:3]  # 只取前3個最相關的結果
            ])
            enhanced_text = f"【知識庫參考】\n{knowledge_context}\n\n【用戶查詢】\n{text}"
        
        project.agents.messages.create(thread_id=thread.id, role="user", content=enhanced_text)
        run = project.agents.runs.create_and_process(thread_id=thread.id, agent_id=ag.id)
        
        if run.status == "failed":
            return SpecialistResult(
                target=agent_type, 
                agent_id=agent_id, 
                error=f"Run failed: {run.last_error}",
                search_results=search_results,
                knowledge_used=bool(search_results)
            )
        
        msgs = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        replies = [m.text_messages[-1].text.value for m in msgs if m.role == "assistant" and getattr(m, "text_messages", None)]
        latency = round(time.time() - start, 3)
        
        return SpecialistResult(
            target=agent_type, 
            agent_id=agent_id, 
            response=(replies[-1] if replies else "(空回應)"), 
            latency_s=latency,
            search_results=search_results,
            knowledge_used=bool(search_results)
        )
    except Exception as e:
        return SpecialistResult(
            target=agent_type, 
            error=str(e), 
            latency_s=round(time.time()-start, 3),
            search_results=search_results,
            knowledge_used=bool(search_results)
        )

# ========== 下游：PydanticAI 原生專家 Agents（各自有 tool 直呼 Azure） ==========
def make_specialist_agent(name: str) -> Agent[None, SpecialistResult]:
    tools = []
    
    # 基本 Azure Agent 調用工具
    async def invoke_backend(_: RunContext[None], text: str, thread_id: Optional[str] = None) -> SpecialistResult:
        return _call_azure_agent(name, text, thread_id=thread_id)
    
    # 添加 Azure AI Search 工具（如果可用）
    if search_client:
        search_tool = azure_search_tool(
            search_client,
            name=f"{name}_search",
            description=f"查詢 {name} 相關的知識庫文檔，用於增強回答準確性。"
        )
        tools.append(search_tool)
    
    agent = Agent(
        base_model,
        output_type=SpecialistResult,
        tools=tools,
        instructions=f"""你是 {name} 專家代理。你有以下能力：
        1. 呼叫後端 Azure Agent 處理複雜分析
        2. {'查詢知識庫文檔以增強回答' if search_client else '直接回應查詢'}
        
        處理流程：
        1. 如果需要參考文檔或最佳實踐，先使用搜尋工具
        2. 結合搜尋結果和你的專業知識
        3. 必要時調用後端 Azure Agent 進行深度分析
        4. 提供結構化的專業回應"""
    )
    
    @agent.tool
    async def invoke_backend_tool(_: RunContext[None], text: str, thread_id: Optional[str] = None) -> SpecialistResult:
        return _call_azure_agent(name, text, thread_id=thread_id)

    return agent

threat_agent   = make_specialist_agent("threat_analysis")
network_agent  = make_specialist_agent("network_security")
account_agent  = make_specialist_agent("account_security")
general_agent  = make_specialist_agent("general_response")

CHILDREN: Dict[str, Agent] = {
    "threat_analysis": threat_agent,
    "network_security": network_agent,
    "account_security": account_agent,
    "general_response": general_agent,
}

# ========== Router 與 Summarizer（PydanticAI） ==========
router = Agent(base_model, output_type=Route, instructions=ROUTER_INSTRUCTIONS)
summarizer = Agent(base_model, output_type=SumOut, instructions=SUMMARIZER_INSTRUCTIONS)

# Router 的 handoff 工具：把 usage 和 thread_id 交給子代理
@router.tool
async def handoff(ctx: RunContext[None], target: str, text: str, thread_id: Optional[str] = None) -> SpecialistResult:
    child = CHILDREN.get(target, general_agent)
    # thread_id 也傳下去；usage 用 ctx.usage
    return await child.run({"text": text, "thread_id": thread_id}, usage=ctx.usage)

# ========== 協調器：多輪 + fallback + 摘要 + usage 限制 ==========
class Coordinator:
    def __init__(self, threshold: float = CONF_THRESHOLD, max_rounds: int = MAX_ROUNDS):
        self.threshold = threshold
        self.max_rounds = max_rounds
        self.history: List[str] = []
        self.thread_id: Optional[str] = None   # <── 新增：保存 Azure thread

    def start_dialog(self):
        # 開一個新 thread；之後 continue_dialog 都重用
        self.thread_id = project.agents.threads.create().id

    def continue_dialog(self, text: str) -> OrchestratedOutput:
        if not self.thread_id:
            self.start_dialog()
        return self._run_core(text, thread_id=self.thread_id)

    # 原 run() 改成呼叫 core；為了相容，也保留 run() 會新開 thread
    def run(self, text: str) -> OrchestratedOutput:
        self.start_dialog()
        return self._run_core(text, thread_id=self.thread_id)

    def _route(self, text: str) -> Route:
        return router.run_sync(text, usage_limits=UsageLimits(request_limit=5, total_tokens_limit=2000)).output

    def _normalize(self, route: Route) -> str:
        tgt = route.target
        if route.confidence < self.threshold and tgt != AgentType.GENERAL_RESPONSE.value:
            tgt = AgentType.GENERAL_RESPONSE.value
        if tgt == AgentType.UNKNOWN.value:
            tgt = AgentType.GENERAL_RESPONSE.value
        return tgt

    def _delegate(self, target: str, text: str, thread_id: Optional[str]) -> SpecialistResult:
        """委託給專家代理，可選擇性先進行知識搜尋以增強回應。"""
        search_results = None
        
        # 如果 Azure AI Search 可用，先進行知識檢索
        if search_client:
            try:
                # 根據不同專家類型調整搜尋策略
                search_filters = {
                    "threat_analysis": "category eq 'threat' or category eq 'malware' or category eq 'attack'",
                    "network_security": "category eq 'network' or category eq 'firewall' or category eq 'infrastructure'",
                    "account_security": "category eq 'identity' or category eq 'access' or category eq 'authentication'",
                    "general_response": None  # 不限制分類
                }
                
                filter_condition = search_filters.get(target)
                
                # 執行搜尋
                hits = search_client.search(
                    query_text=text,
                    top_k=3,
                    filter=filter_condition,
                    semantic=True
                )
                
                if hits:
                    search_results = hits
                    print(f"🔍 為 {target} 找到 {len(hits)} 個相關文檔")
            
            except Exception as e:
                print(f"⚠️ 知識搜尋失敗: {e}")
        
        # 呼叫 Azure 後端，傳入搜尋結果
        return _call_azure_agent(target, text, thread_id=thread_id, search_results=search_results)

    def _summarize(self, user_input: str, agent_response: str) -> SumOut:
        hist = "\n".join(self.history)
        cur  = f"User: {user_input}\nAssistant: {agent_response}"
        full = f"{hist}\n{cur}" if hist else cur
        def _summarize_text(text: str) -> SumOut:
            r = summarizer.run_sync(text, usage_limits=UsageLimits(request_limit=3, total_tokens_limit=1000))
            return r.output

        try:
            out = _summarize_text(full)
        except UsageLimitExceeded:
            # 若累積歷史過長導致超量，改用當前輪對話重新摘要
            try:
                out = _summarize_text(cur)
            except UsageLimitExceeded:
                # 連單輪都失敗時，直接 fallback 到靜態摘要，避免中斷流程
                truncated = (agent_response or "無回應").strip()
                if len(truncated) > 120:
                    truncated = truncated[:117] + "..."
                return SumOut(summary=f"摘要失敗（超出使用限制）。重點：{truncated}", concluded=False)

        # 強韌處理
        if not out or not isinstance(out, SumOut):
            return SumOut(summary="無需摘要", concluded=False)
        if not (out.summary or "").strip():
            out.summary = "無需摘要"
        return out

    def _run_core(self, text: str, thread_id: Optional[str]) -> OrchestratedOutput:
        steps, route, sres = [], None, None
        cur = text
        round_usages: List[Dict[str, Any]] = []   # <── 每輪 usage 記錄

        for i in range(1, self.max_rounds + 1):
            steps.append(f"Round {i}: route")
            r = router.run_sync(cur, usage_limits=UsageLimits(request_limit=5, total_tokens_limit=2000))
            route = r.output
            steps.append(f"  -> {route.target} ({route.confidence})")
            # 記 usage（社群常用法：從 RunResult 取 usage 彙總）:contentReference[oaicite:3]{index=3}
            # usage 可能在某些情況下不是具有 model_dump 的物件（例如被覆寫成函式），需安全檢查
            if getattr(r, "usage", None) and hasattr(r.usage, "model_dump"):
                try:
                    round_usages.append({"phase": f"route_{i}", **r.usage.model_dump()})
                except Exception as e:  # 極端失敗忽略，不影響主流程
                    steps.append(f"  (warn) route usage serialize failed: {e}")

            tgt = self._normalize(route)
            steps.append(f"  handoff -> {tgt}")

            sres = self._delegate(tgt, cur, thread_id)

            # 這輪摘要 + 提早停止判斷
            sum_out = self._summarize(cur, (sres.response or ""))
            steps.append(f"  summarized: concluded={sum_out.concluded}")
            # 把摘要也寫回 thread 給下一輪
            project.agents.messages.create(thread_id=thread_id, role="assistant", content=f"[摘要]\n{sum_out.summary}")
            self.history.append(sum_out.summary)
            if len(self.history) > 20:
                self.history = self.history[-20:]

            if sres and not sres.error and sum_out.concluded:
                steps.append("  concluded=true -> stop")
                return OrchestratedOutput(route=route, result=sres, steps=steps, summary=sum_out.summary)

            if sres and not sres.error:
                steps.append("  ok but not concluded -> maybe next round")
            else:
                steps.append("  error -> retry")
                cur = "[RETRY]\n" + cur

        # 超過 MAX_ROUNDS：fallback
        steps.append("Fallback: general_response")
        route = Route(target=AgentType.GENERAL_RESPONSE.value, confidence=1.0)
        sres = self._delegate("general_response", cur, thread_id)
        sum_out = self._summarize(cur, (sres.response or ""))
        steps.append("  finalized with fallback")
        project.agents.messages.create(thread_id=thread_id, role="assistant", content=f"[摘要]\n{sum_out.summary}")

        # Azure Agent 目前無法回傳 usage；只會彙整路由階段的用量資訊
        # 把 usage summary 放進 steps
        steps.append(f"USAGE_SUMMARY={json.dumps(round_usages, ensure_ascii=False)}")
        return OrchestratedOutput(route=route, result=sres, steps=steps, summary=sum_out.summary)

coordinator = Coordinator()

def analyze(text: str) -> Dict[str, Any]:
    out = coordinator.run(text)
    return json.loads(json.dumps(out.model_dump(), ensure_ascii=False))

if __name__ == "__main__":
    samples = [
        "主機 192.168.1.1 發現未授權的 SSH 登入，請協助分析並提出建議。",
        "什麼是零信任網路架構？請說明其核心原則。",
        "發現使用者帳號異常登入行為，如何進行調查？",
        "網路掃描發現開放的 RDP 埠，有什麼安全風險？",
    ]
    
    print(f"🔍 Azure AI Search 狀態: {'已啟用' if search_client else '未啟用'}")
    print(f"📊 測試案例數量: {len(samples)}")
    print("="*60)
    
    for i, s in enumerate(samples, 1):
        print(f"\n🔹 測試案例 {i}/{len(samples)}")
        print("=== INPUT ===")
        print(s)
        print("=== OUTPUT ===")
        result = analyze(s)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 顯示是否使用了知識庫
        if result.get('result', {}).get('knowledge_used'):
            print("💡 此回應使用了知識庫檢索")
        
        print("-" * 60)
