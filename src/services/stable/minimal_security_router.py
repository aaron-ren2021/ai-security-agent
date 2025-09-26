# minimal_security_router.py
# PoC: 最精簡版「智能路由」→ 呼叫 Azure 上的 3 位專家 agent + 一個閒聊 agent
# 需求：pip install "pydantic-ai-slim[openai]" httpx python-dotenv


from enum import Enum
from typing import Literal, Dict, Any
import os
import json
import time
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.providers.azure import AzureProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai import Agent
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

load_dotenv()  

# 從 env 拿部署名稱 & endpoint & api key
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")  # e.g. "my-gpt4-dep"
# OpenAI 對話模型 endpoint (通常是 *.openai.azure.com)
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("OPENAI_API_VERSION")

# AI Project (Agent) 用的 endpoint（通常包含 /api/projects/<project-name>）
project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or azure_openai_endpoint

# Debug flag
DEBUG = os.getenv("SECURITY_ROUTER_DEBUG", "0") in ("1", "true", "True")

def _mask(v: str | None, keep: int = 4) -> str:
    if not v:
        return "<empty>"
    return v[:keep] + "***" if len(v) > keep else "***"

def dlog(*args):
    if DEBUG:
        print("[security-router-debug]", *args)

def validate_config():
    problems = []
    if not deployment_name:
        problems.append("缺少 AZURE_OPENAI_DEPLOYMENT")
    if not azure_openai_endpoint:
        problems.append("缺少 AZURE_OPENAI_ENDPOINT (OpenAI Chat 用)")
    if not project_endpoint:
        problems.append("缺少 AZURE_AI_PROJECT_ENDPOINT 或 AZURE_OPENAI_ENDPOINT")
    else:
        # 判斷使用者是否把 OpenAI endpoint 當成 Project endpoint 用
        if "/api/projects/" not in project_endpoint:
            problems.append("提供的 project_endpoint 未含 /api/projects/<project>，AIProjectClient 可能 404")
    if problems:
        dlog("設定檢查警告:")
        for p in problems:
            dlog(" -", p)
    dlog(
        f"deployment={deployment_name} openai_endpoint={azure_openai_endpoint} project_endpoint={project_endpoint} api_key={_mask(api_key)} version={api_version}"
    )

validate_config()


# 建立 model 實例（指定 Azure provider）
'''model = OpenAIChatModel(
    deployment_name,
    provider=AzureProvider(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        api_version=api_version,
    )
)'''



# 不傳任何參數給 AzureProvider()
model = OpenAIChatModel(
    deployment_name,
    provider=AzureProvider()  # 讓它自己從環境變數撈 (需正確 AZURE_OPENAI_* 變數)
)


# Azure AI Project Client
try:
    project = AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=project_endpoint,
    )
    dlog("AIProjectClient 建立成功")
except Exception as e:
    project = None
    dlog(f"AIProjectClient 建立失敗: {e}")

# Agent IDs
AGENT_IDS = {
    "threat_analysis": "asst_wQTilJKeeNzL6dKTGXG5ynEW",
    "network_security": "asst_Blv8Anlvv0FfP5bG7e19kGFU", 
    "account_security": "asst_89bKLUBlHjIFTRe6xqcejT8q",
    "general_response": "asst_UIt2UKGS0cpTclQrOVm1XEfi"
}

# ---------- 1) AgentType（精簡＆一致命名） ----------
class AgentType(str, Enum):
    THREAT_ANALYSIS = "threat_analysis"
    NETWORK_SECURITY = "network_security"
    ACCOUNT_SECURITY = "account_security"
    GENERAL_RESPONSE = "general_response"
    UNKNOWN = "unknown"  # 低信心時的保底

# ---------- 2) Router 的輸出 Schema（含信心） ----------
class Route(BaseModel):
    target: Literal[
        "threat_analysis", "network_security", "account_security",
        "general_response", "unknown"
    ]
    confidence: float

# ---------- 3) Router（用 Azure OpenAI，MVP 版本在程式定義） ----------
router = Agent(
    model,
    output_type=Route,
    instructions=os.getenv(
        "ROUTER_INSTRUCTIONS",
        (   
            "你是資安路由器，只輸出 JSON(target, confidence)。\n"
            "規則：\n"
            "- 有攻擊者/IOC/TTP/入侵跡象 → threat_analysis\n"
            "- 有主機/埠/服務/版本/弱掃/誤設 → network_security\n"
            "- 有帳號/密碼/MFA/權限/登入異常 → account_security\n"
            "- 模糊或閒聊 → general_response\n"
            "confidence 介於 0~1；若極度不確定，target=unknown。"
        )
    ),
)

# ---------- 4) 呼叫 Azure AI Agent 的通用函式 ----------
def call_azure_ai_agent(agent_type: str, user_message: str) -> Dict[str, Any]:
    """直接調用 Azure AI Agent，附加偵錯資訊與延遲重試 (簡易)。"""
    if project is None:
        return {"error": "AIProjectClient 未初始化 (endpoint 或認證錯誤)"}
    start = time.time()
    agent_id = AGENT_IDS.get(agent_type)
    if not agent_id:
        return {"error": f"Unknown agent type: {agent_type}"}
    dlog(f"準備呼叫 agent_type={agent_type} agent_id={agent_id}")
    try:
        agent = project.agents.get_agent(agent_id)
        dlog("取得 agent 成功")
    except Exception as e:
        return {"error": f"get_agent 失敗: {e}", "agent_id": agent_id}

    try:
        thread = project.agents.threads.create()
        dlog(f"建立 thread: {thread.id}")
    except Exception as e:
        return {"error": f"threads.create 失敗: {e}"}

    try:
        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        dlog(f"送出使用者訊息 msg_id={message.id}")
    except Exception as e:
        return {"error": f"messages.create 失敗: {e}"}

    # 嘗試 run，加入一次重試
    last_exc = None
    for attempt in (1, 2):
        try:
            run = project.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent.id
            )
            dlog(f"run.status={run.status}")
            if run.status == "failed":
                return {"error": f"Agent run failed: {run.last_error}", "thread_id": thread.id}
            break
        except Exception as e:
            last_exc = e
            dlog(f"run 嘗試 {attempt} 失敗: {e}")
            time.sleep(0.8)
    else:
        return {"error": f"runs.create_and_process 失敗: {last_exc}"}

    try:
        messages = project.agents.messages.list(
            thread_id=thread.id,
            order=ListSortOrder.ASCENDING
        )
    except Exception as e:
        return {"error": f"messages.list 失敗: {e}", "thread_id": thread.id}

    assistant_responses = []
    for msg in messages:
        if msg.role == "assistant" and getattr(msg, "text_messages", None):
            try:
                assistant_responses.append(msg.text_messages[-1].text.value)
            except Exception:
                pass

    elapsed = round(time.time() - start, 3)
    if not assistant_responses:
        dlog("assistant 無回覆 (可能仍在處理或工具調用)")
    return {
        "response": assistant_responses[-1] if assistant_responses else "No response from agent",
        "thread_id": thread.id,
        "agent_id": agent_id,
        "elapsed_sec": elapsed
    }

# ---------- 5) 主流程：路由 → 呼叫對應 Azure AI Agent ----------
def analyze(text: str) -> Dict[str, Any]:
    route = router.run_sync(text).output
    target = route.target
    conf = route.confidence
    dlog(f"router 輸出 target={target} confidence={conf}")

    if conf < 0.55 and target != AgentType.GENERAL_RESPONSE.value:
        dlog(f"低信心 {conf} → 改送 general_response")
        target = AgentType.GENERAL_RESPONSE.value

    if target == AgentType.UNKNOWN.value:
        result = call_azure_ai_agent("general_response", f"[UNKNOWN ROUTE]\n{text}")
    else:
        result = call_azure_ai_agent(target, text)

    return {"route": {"target": target, "confidence": conf}, "result": result}

# ---------- 6) Demo ----------
if __name__ == "__main__":
    samples = [
        "主機 10.0.3.12 開 22,443,9200,Elasticsearch 未啟用認證",
        "AD 帳號弱密碼 10 個,MFA 覆蓋率不足 60%",
        "發現 Beacon 與 TTP T1041、IOC: 45.66.77.88",
        "有點偏瘦，有沒有保持健康體重的方法？",
    ]
    for s in samples:
        out = analyze(s)
        print("\n=== INPUT ===")
        print(s)
        print("=== OUTPUT ===")
        print(json.dumps(out, ensure_ascii=False, indent=2))



