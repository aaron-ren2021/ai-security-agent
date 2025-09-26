# routers/router_core.py
# 決策邏輯核心」多 prompt / 聚合演算法,信心值計算,未來可以替換：rule-based router
import json
from typing import List, Dict, Tuple
from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_TEMPLATES = {
    "conservative": """你是資安路由器。列出 2~3 個關鍵線索，反思後輸出 JSON {target, confidence, reason}。
語氣保守，傾向降低信心。""",
    "neutral": """你是資安路由器。列出線索，反思後輸出 JSON {target, confidence, reason}。
語氣中性。""",
    "optimistic": """你是資安路由器。列出線索，反思後輸出 JSON {target, confidence, reason}。
語氣樂觀，傾向提高信心。"""
}

async def call_router_prompt(template: str, question: str) -> Dict:
    resp = await client.chat.completions.create(
        model="o3-mini",
        messages=[
            {"role": "system", "content": template},
            {"role": "user", "content": question}
        ],
        temperature=0.0,
    )
    txt = resp.choices[0].message.content.strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {"target": "unknown", "confidence": 0.0, "reason": "parse error"}

def aggregate_decisions(results: List[Dict]) -> Tuple[str, float]:
    confidences = [r["confidence"] for r in results]
    avg_conf = sum(confidences) / len(confidences)
    best = min(results, key=lambda r: abs(r["confidence"] - avg_conf))
    return best["target"], best["confidence"]

async def router_decide(question: str) -> Dict:
    outputs = []
    for tmpl in PROMPT_TEMPLATES.values():
        res = await call_router_prompt(tmpl, question)
        outputs.append(res)
    target, conf = aggregate_decisions(outputs)
    return {"target": target, "confidence": conf, "raw": outputs}
