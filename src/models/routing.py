# models/routing.py （RoutingDecision）資料模型

from pydantic import BaseModel
from typing import Literal, Optional, List, Dict

class RoutingDecision(BaseModel):
    target: Literal["threat_analysis", "network_security", "account_security", "general_response", "unknown"]
    confidence: float
    reason: Optional[str] = None
    raw: Optional[List[Dict]] = None   # 存放多 prompt 輸出，方便 debug
