# Postgres + pgvector 中文混合檢索

## 容器準備

```bash
docker run --rm -d --name pgvector-zh-postgres-1 \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=postgres \
  ankane/pgvector-zh:latest
```

這個映像內建 `pgvector`、`zhparser` 和常見的中文分詞，啟動後可以直接建立文檔表。

## 建立資料表

```sql
CREATE TABLE documents (
  id SERIAL PRIMARY KEY,
  title TEXT,
  content TEXT,
  embedding VECTOR(1536),
  tsv tsvector
);

CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON documents USING gin (tsv);
```

每次插入時，請使用 `pgvector` 生成 embedding 並更新 `tsv` 為 `to_tsvector('chinese', content)`。

## 使用 pgvector-zh 工具

服務會自動向 OpenAI 串接 `text-embedding-3-large`，並混合向量與中文全文分詞結果。可從 `/api/search/postgres/hybrid` 傳遞以下範例 payload：

```json
{
  "query": "2025 年最新釣魚攻擊策略",
  "top_k": 5,
  "language": "chinese",
  "vector_weight": 0.7,
  "text_weight": 0.3
}
```

如果有 Agent 需要呼叫這個工具，已經在 `PostgresHybridSearchService` 裡註冊，可透過 Pydantic-AI agent config 使用 `postgres_hybrid_search` 工具名稱直接調用。
