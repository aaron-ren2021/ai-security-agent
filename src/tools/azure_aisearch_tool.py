"""pydantic-ai Tool 封裝 Azure AI Search 查詢能力。

使用方式：
    from pydantic_ai import Agent
    from services.experimental.azure_ai_search import AzureAISearchExperimental, AzureSearchConfig
    from tools.azure_aisearch_tool import azure_search_tool

    search_client = AzureAISearchExperimental(AzureSearchConfig(service_name="<svc>", api_key="<key>", index_name="documents"))
    agent = Agent(
        model="openai:gpt-4o-mini",  # 或 azure-openai provider 標記
        tools=[azure_search_tool(search_client)],
        system_prompt="You are a helpful security assistant. Use the search tool for knowledge retrieval when needed.",
    )

    answer = agent.run_sync("說明零信任(Zero Trust) 的核心原則")
    print(answer)

注意：需先安裝 pydantic-ai >= 0.0.14 並在執行環境中設定 OPENAI / Azure OpenAI 的 API Key。
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence

from pydantic import BaseModel, Field
from pydantic_ai import Tool

from src.services.stable.azure_ai_search import AzureAISearchExperimental

# -------------------------------------------------------------
# Tool 輸入 / 輸出模型定義
# -------------------------------------------------------------


class AzureSearchToolInput(BaseModel):
    """Agent 呼叫工具時可提供的參數。

    任一 (text, vector) 可選。若只提供 text 且有 embedding_fn 則會自動向量化成混合查詢。
    """

    text: Optional[str] = Field(
        None, description="自然語言查詢字串，若同時提供 vector 則進行混合搜尋"
    )
    vector: Optional[List[float]] = Field(
        None, description="已計算好的 embedding 向量 (長度需符合索引設定)"
    )
    top_k: int = Field(5, ge=1, le=50, description="回傳結果數量上限")
    filter: Optional[str] = Field(
        None, description="OData filter，用於條件過濾 (e.g. category eq 'policy')"
    )
    semantic: Optional[bool] = Field(
        None, description="是否啟用語意搜尋 (未指定時採用後端預設)"
    )


class AzureSearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    metadata: dict[str, Any] = {}
    highlights: list[str] | None = None


class AzureSearchToolOutput(BaseModel):
    query_text: str | None = None
    used_vector: bool
    results: List[AzureSearchResult]


# -------------------------------------------------------------
# pydantic-ai Tool 實作
# -------------------------------------------------------------


def azure_search_tool(
    search_client: AzureAISearchExperimental,
    *,
    embedding_fn: Optional[Callable[[str], Sequence[float]]] = None,
    name: str = "azure_search",
    description: str = "查詢內建 Azure AI Search 索引，支援文字/向量/混合/語意檢索。",
) -> Tool[AzureSearchToolInput, AzureSearchToolOutput]:
    """建立一個可供 pydantic-ai Agent 使用的 Azure Search Tool。

    Parameters
    ----------
    search_client : AzureAISearchExperimental
        已初始化的 Search wrapper。
    embedding_fn : Callable[[str], Sequence[float]] | None
        若提供，當呼叫者只給 text 而未提供 vector 時會自動做 embedding。
    name : str
        Tool 名稱 (Agent 內唯一)。
    description : str
        Tool 描述，影響 LLM 是否選用。
    """

    @Tool.register(name=name, description=description)
    def _tool(input_data: AzureSearchToolInput) -> AzureSearchToolOutput:  # type: ignore[misc]
        # 1. 決定向量 (若只給 text 且有 embedding_fn)
        vector = input_data.vector
        if vector is None and input_data.text and embedding_fn:
            try:
                emb = embedding_fn(input_data.text)
                vector = list(map(float, emb))  # copy & ensure float
            except Exception as e:  # pragma: no cover - embedding 例外防護
                raise RuntimeError(f"Embedding function failed: {e}")

        # 2. 呼叫後端搜尋
        hits = search_client.search(
            query_text=input_data.text,
            query_vector=vector,
            top_k=input_data.top_k,
            filter=input_data.filter,
            semantic=input_data.semantic,
        )

        # 3. 整理結果
        results = [AzureSearchResult(**h) for h in hits]
        return AzureSearchToolOutput(
            query_text=input_data.text,
            used_vector=vector is not None,
            results=results,
        )

    return _tool


# -------------------------------------------------------------
# (選擇性) 快速示例: 只在直接執行此檔案時展示，不在匯入時執行。
# -------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover - demo 用
    from src.services.stable.azure_ai_search import AzureSearchConfig, AzureAISearchExperimental

    # 簡易示例；請填入實際 service_name 與 api_key
    cfg = AzureSearchConfig(service_name="YOUR_SEARCH_SERVICE", api_key="YOUR_KEY", index_name="documents")
    client = AzureAISearchExperimental(cfg)

    # 假設已有 embedding 函數 (此處示意用固定長度向量)；實務上請替換成真正 embedding 呼叫
    def dummy_embedding(text: str) -> Sequence[float]:  # pragma: no cover - demo
        return [0.0] * cfg.embedding_dimensions

    tool = azure_search_tool(client, embedding_fn=dummy_embedding)
    # 手動觸發一次 (等同 Agent 會做的事)
    sample_out = tool.run(AzureSearchToolInput(text="示例查詢", top_k=3))  # type: ignore[arg-type]
    print(sample_out.model_dump())
