
# fastapi_app.py
# FastAPI wrapper for PydanticAI multi-agent handoff framework
#
# Usage:
#   pip install fastapi "uvicorn[standard]"
#   uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --reload
#
# Endpoints:
#   GET  /health         -> env & dependency sanity check
#   POST /analyze        -> { "input": "<text>" } -> routing + handoff result
#   POST /route-only     -> { "input": "<text>" } -> just return router decision (debug)

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict

import src.services.experimental.multi_agent as mr  # uses analyze(), coordinator, etc.

app = FastAPI(title="PydanticAI Multi-Agent Router API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    input: str

@app.get("/health")
def health() -> Dict[str, Any]:
    problems = []
    if not mr.DEPLOYMENT:
        problems.append("Missing AZURE_OPENAI_DEPLOYMENT")
    if not mr.AI_PROJECT_ENDPOINT:
        problems.append("Missing AZURE_AI_PROJECT_ENDPOINT")
    # AzureProvider envs are validated lazily by provider; we can surface hints:
    for k in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "OPENAI_API_VERSION"):
        if not os.getenv(k):
            problems.append(f"Missing {k}")
    status = "ok" if not problems else "degraded"
    return {
        "status": status,
        "deployment": mr.DEPLOYMENT,
        "project_endpoint": mr.AI_PROJECT_ENDPOINT,
        "problems": problems,
    }

@app.post("/analyze")
def analyze(body: AnalyzeRequest) -> Dict[str, Any]:
    try:
        return mr.analyze(body.input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/route-only")
def route_only(body: AnalyzeRequest) -> Dict[str, Any]:
    try:
        route = mr.coordinator.decide(body.input)
        # Return pydantic model as dict
        return {"route": route.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
