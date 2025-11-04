"""Experimental Azure AI Search integration built on azure-search-documents SDK."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)

try:
	from azure.search.documents import SearchClient
	from azure.search.documents.indexes import SearchIndexClient
	from azure.search.documents.indexes.models import (
		SearchIndex,
		SimpleField,
		SearchableField,
		SearchField,
		SearchFieldDataType,
		VectorSearch,
		VectorSearchProfile,
		HnswAlgorithmConfiguration,
		SemanticConfiguration,
		SemanticSearch,
		SemanticPrioritizedFields,
		SemanticField,
	)
	from azure.search.documents.models import VectorizedQuery
	from azure.core.credentials import AzureKeyCredential
	from azure.identity import DefaultAzureCredential
	from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
	AZURE_SEARCH_AVAILABLE = True
except ImportError:  # pragma: no cover
	SearchClient = None  # type: ignore
	SearchIndexClient = None  # type: ignore
	SearchIndex = None  # type: ignore
	SimpleField = None  # type: ignore
	SearchableField = None  # type: ignore
	SearchField = None  # type: ignore
	SearchFieldDataType = None  # type: ignore
	VectorSearch = None  # type: ignore
	VectorSearchProfile = None  # type: ignore
	HnswAlgorithmConfiguration = None  # type: ignore
	SemanticConfiguration = None  # type: ignore
	SemanticSearch = None  # type: ignore
	SemanticPrioritizedFields = None  # type: ignore
	SemanticField = None  # type: ignore
	VectorizedQuery = None  # type: ignore
	AzureKeyCredential = None  # type: ignore
	DefaultAzureCredential = None  # type: ignore
	HttpResponseError = Exception  # fallback for typing
	ResourceNotFoundError = Exception
	AZURE_SEARCH_AVAILABLE = False

@dataclass
class AzureSearchConfig:
	service_name: str
	api_key: Optional[str] = None
	index_name: str = "documents"
	vector_field_name: str = "content_vector"
	embedding_dimensions: int = 1536
	analyzer_name: Optional[str] = None
	use_semantic_search: bool = False
	semantic_configuration_name: str = "default-semantic-config"


class AzureAISearchExperimental:
	"""Thin wrapper around the Azure AI Search SDK for experimental flows."""

	def __init__(self, config: AzureSearchConfig):
		if not AZURE_SEARCH_AVAILABLE:
			raise RuntimeError("azure-search-documents SDK is not installed.")

		self.config = config
		endpoint = f"https://{config.service_name}.search.windows.net"

		# Use API key if provided; otherwise attempt DefaultAzureCredential (keyless).
		if getattr(config, 'api_key', None):
			self.credential = AzureKeyCredential(config.api_key)
		else:
			# Use DefaultAzureCredential (MS Entra) if no API key is supplied.
			# This enables keyless authentication flows in production.
			self.credential = DefaultAzureCredential()
			logger.info("Using DefaultAzureCredential for Azure AI Search authentication (keyless)")

		self.search_client = SearchClient(
			endpoint=endpoint,
			index_name=config.index_name,
			credential=self.credential,
		)
		self.index_client = SearchIndexClient(
			endpoint=endpoint,
			credential=self.credential,
		)

	def ensure_index(self, recreate: bool = False) -> None:
		"""Ensure that the Azure AI Search index exists."""
		try:
			if recreate:
				self.index_client.delete_index(self.config.index_name)
				logger.info("Deleted Azure AI Search index %s", self.config.index_name)
		except ResourceNotFoundError:
			pass
		except HttpResponseError as exc:
			logger.error("Failed to delete index %s: %s", self.config.index_name, exc)
			raise

		if self._index_exists():
			return

		try:
			index = self._build_index()
			# Use create_or_update_index so deployments are idempotent.
			self.index_client.create_or_update_index(index)
			logger.info("Created/Updated Azure AI Search index %s", self.config.index_name)
		except HttpResponseError as exc:
			logger.error("Failed to create/update index %s: %s", self.config.index_name, exc)
			raise

	# ... 其餘內部方法 (保留原樣) ...

	def _index_exists(self) -> bool:  # pragma: no cover - simple passthrough
		"""Return True if index already exists.

		We call get_index; if it raises ResourceNotFoundError we return False.
		We intentionally avoid list_indexes for performance & RBAC scope.
		"""
		try:
			self.index_client.get_index(self.config.index_name)
			return True
		except ResourceNotFoundError:
			return False
		except HttpResponseError as exc:
			logger.warning("Index existence check failed (optimistically treat as absent): %s", exc)
			return False

	def _build_index(self) -> SearchIndex:  # type: ignore
		if SearchIndex is None:
			raise RuntimeError("SearchIndex type is not available. Ensure azure-search-documents SDK is installed.")
		fields = [
			SimpleField(name="id", type=SearchFieldDataType.String, key=True),
			SearchableField(
				name="title",
				type=SearchFieldDataType.String,
				analyzer_name=self.config.analyzer_name,
			),
			SearchableField(
				name="content",
				type=SearchFieldDataType.String,
				analyzer_name=self.config.analyzer_name,
			),
			SearchField(
				name=self.config.vector_field_name,
				type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
				searchable=True,
				vector_search_dimensions=self.config.embedding_dimensions,
				vector_search_profile_name="hnsw-profile",
			),
			SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
			SimpleField(
				name="tags",
				type=SearchFieldDataType.Collection(SearchFieldDataType.String),
				filterable=True,
				facetable=True,
			),
			# NOTE: we keep metadata_json for backwards compatibility.
			# If you need to filter/facet on metadata, consider splitting into dedicated fields.
			SimpleField(name="metadata_json", type=SearchFieldDataType.String),
			SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
		]

		vector_search = VectorSearch(
			algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
			profiles=[
				VectorSearchProfile(
					name="hnsw-profile",
					algorithm_configuration_name="hnsw-config",
				)
			],
		)

		semantic_settings = None
		if self.config.use_semantic_search:
			semantic_settings = SemanticSearch(
				configurations=[
					SemanticConfiguration(
						name=self.config.semantic_configuration_name,
						prioritized_fields=SemanticPrioritizedFields(
							title_field=SemanticField(field_name="title"),
							content_fields=[SemanticField(field_name="content")],
							keywords_fields=[SemanticField(field_name="category")],
						),
					)
				]
			)

		index = SearchIndex(
			name=self.config.index_name,
			fields=fields,
			vector_search=vector_search,
			semantic_search=semantic_settings,
		)
		return index

	def index_document(
		self,
		doc_id: str,
		title: str,
		content: str,
		*,
		metadata: Optional[Dict[str, Any]] = None,
		category: Optional[str] = None,
		tags: Optional[Iterable[str]] = None,
		vector: Optional[Sequence[float]] = None,
		created_at: Optional[datetime] = None,
	) -> None:
		"""Upload or update a single document in the Azure AI Search index."""
		document: Dict[str, Any] = {
			"id": doc_id,
			"title": title,
			"content": content,
			"metadata_json": json.dumps(metadata or {}),
		}
		if category:
			document["category"] = category
		if tags:
			document["tags"] = list(tags)
		if created_at:
			document["created_at"] = created_at

		if vector is not None:
			# validate embedding dimension
			if len(vector) != self.config.embedding_dimensions:
				raise ValueError(
					f"Embedding vector length {len(vector)} != expected {self.config.embedding_dimensions}"
				)
			# coerce to floats
			document[self.config.vector_field_name] = [float(x) for x in vector]

		try:
			results = self.search_client.upload_documents(documents=[document])
		except HttpResponseError as exc:
			logger.error("Failed to index document %s: %s", doc_id, exc)
			raise

		failed = [item for item in results if not item.succeeded]
		if failed:
			error_message = failed[0].error_message or "Unknown Azure AI Search failure."
			raise RuntimeError(f"Azure AI Search indexing failed: {error_message}")

	def delete_document(self, doc_id: str) -> None:
		"""Remove a document from the Azure AI Search index."""
		try:
			self.search_client.delete_documents(documents=[{"id": doc_id}])
		except HttpResponseError as exc:
			logger.error("Failed to delete document %s: %s", doc_id, exc)
			raise

	def search(
		self,
		*,
		query_text: Optional[str] = None,
		query_vector: Optional[Sequence[float]] = None,
		top_k: int = 5,
		filter: Optional[str] = None,
		semantic: Optional[bool] = None,
		select: Optional[Sequence[str]] = None,
	) -> List[Dict[str, Any]]:
		"""Execute a hybrid / vector / semantic search.

		Returns a list of dict items with keys: id, title, content, score, metadata, (optional) highlights.
		"""
		if not AZURE_SEARCH_AVAILABLE:  # pragma: no cover - defensive
			raise RuntimeError("azure-search-documents SDK not available")

		search_text = query_text or "*"  # Azure requires a non-empty search_text in most cases
		kwargs: Dict[str, Any] = {}

		if query_vector is not None:
			if len(query_vector) != self.config.embedding_dimensions:
				raise ValueError(
					f"Query vector length {len(query_vector)} != expected {self.config.embedding_dimensions}"
				)
				# If dimensions mismatch, fail early instead of API error.
			vector_query = VectorizedQuery(
				vector=[float(x) for x in query_vector],
				k_nearest_neighbors=top_k,
				fields=self.config.vector_field_name,
			)
			kwargs["vector_queries"] = [vector_query]

		# Decide semantic usage: explicit param wins, else config default.
		use_semantic = self.config.use_semantic_search if semantic is None else semantic
		if use_semantic:
			kwargs["query_type"] = "semantic"
			kwargs["semantic_configuration_name"] = self.config.semantic_configuration_name
			# When using semantic search we can ask for captions / highlights if needed in future.

		if filter:
			kwargs["filter"] = filter
		if select:
			kwargs["select"] = ",".join(select)

		try:
			results_iter = self.search_client.search(
				search_text=search_text,
				top=top_k,
				include_total_count=False,
				**kwargs,
			)
		except HttpResponseError as exc:  # pragma: no cover - network error path
			logger.error("Azure AI Search query failed: %s", exc)
			raise

		items: List[Dict[str, Any]] = []
		for r in results_iter:  # type: ignore
			# r behaves like a dict-like object.
			metadata = self._parse_metadata(r.get("metadata_json"))  # type: ignore
			score = r.get("@search.score", 0.0)  # type: ignore
			item: Dict[str, Any] = {
				"id": r.get("id"),  # type: ignore
				"title": r.get("title", ""),  # type: ignore
				"content": r.get("content", ""),  # type: ignore
				"score": float(score) if score is not None else 0.0,
				"metadata": metadata,
			}
			highlights = r.get("@search.highlights")  # type: ignore
			collected = self._collect_highlights(highlights)
			if collected:
				item["highlights"] = collected
			items.append(item)

		return items

	# ---- 之後若還有 search / query / helper methods, 保持原樣 ----

	@staticmethod
	def _parse_metadata(serialized: Optional[str]) -> Dict[str, Any]:
		if not serialized:
			return {}
		try:
			return json.loads(serialized)
		except json.JSONDecodeError:
			logger.debug("Failed to decode metadata JSON: %s", serialized)
			return {"raw": serialized}

	@staticmethod
	def _collect_highlights(raw_highlights: Any) -> Optional[List[str]]:
		if not raw_highlights or not isinstance(raw_highlights, dict):
			return None
		collected: List[str] = []
		for values in raw_highlights.values():
			if isinstance(values, list):
				collected.extend(values)
		return collected or None


# ------------------------------------------------------------
# CLI / 單檔執行支援
# ------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover - 供使用者本地操作示例
	import argparse
	import os
	import sys
	from pathlib import Path
	import io

	# 嘗試載入專案根目錄 .env（若使用者只建立檔案但未 export 環境變數）
	try:  # pragma: no cover - 若無 dotenv 仍可運作
		from dotenv import load_dotenv  # type: ignore
	except Exception:  # pragma: no cover
		load_dotenv = None  # type: ignore

	def _auto_load_env():  # pragma: no cover - 輕量輔助
		if load_dotenv is None:
			return
		# 自底向上尋找第一個含 .env 的目錄
		for p in Path(__file__).resolve().parents:
			candidate = p / ".env"
			if candidate.exists():
				load_dotenv(candidate, override=False)
				break

	_auto_load_env()

	def _upload_to_blob_simple(file_path: Path) -> tuple[str, dict]:
		"""簡化版本：上傳檔案到 Azure Blob 並進行基本內容提取"""
		try:
			from azure.storage.blob import BlobServiceClient
			
			# 獲取 Azure 環境變數
			storage_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
			storage_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
			container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'documents')
			
			if not all([storage_name, storage_key]):
				raise ValueError("缺少 Azure Storage 環境變數：需要 AZURE_STORAGE_ACCOUNT_NAME 和 AZURE_STORAGE_ACCOUNT_KEY")
			
			# 1. 上傳到 Blob Storage
			blob_service = BlobServiceClient(
				account_url=f"https://{storage_name}.blob.core.windows.net",
				credential=storage_key
			)
			
			blob_name = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{file_path.name}"
			blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
			
			with open(file_path, 'rb') as f:
				blob_client.upload_blob(f, overwrite=True)
			
			blob_url = blob_client.url
			print(f"🌐 檔案上傳到 Blob: {blob_url}")
			
			# 2. 基本的本地文字提取
			content = ""
			if file_path.suffix.lower() == '.pdf':
				try:
					import fitz  # PyMuPDF
					doc = fitz.open(file_path)
					for page in doc:
						content += page.get_text()
					doc.close()
					print(f"✅ PyMuPDF 成功提取 {len(content)} 字符")
				except ImportError:
					print("⚠️  PyMuPDF 未安裝，使用檔案名稱作為內容")
					content = f"PDF 檔案：{file_path.name}"
			else:
				# 其他檔案類型直接讀取文字
				content = file_path.read_text(encoding="utf-8", errors="ignore")
				print(f"✅ 文字檔案讀取 {len(content)} 字符")
			
			metadata = {
				"blob_url": blob_url,
				"file_type": file_path.suffix.lower(),
				"file_size": file_path.stat().st_size,
				"processing_method": "blob_storage_simple"
			}
			
			return content, metadata
			
		except Exception as e:
			print(f"❌ Azure Blob 處理失敗: {e}")
			raise



	def _handle_ingest_command(client: AzureAISearchExperimental, config: AzureSearchConfig, args) -> None:
		"""處理 ingest 命令"""
		from pathlib import Path
		
		folder = Path(args.dir)
		if not folder.exists() or not folder.is_dir():
			raise SystemExit(f"資料夾不存在或不是資料夾: {folder}")
		
		# 可選重建
		client.ensure_index(recreate=args.recreate)
		pattern = args.pattern
		files = list(folder.glob(pattern))
		if not files:
			print(f"無檔案符合 {pattern} (資料夾: {folder})")
			sys.exit(0)
		
		print(f"找到 {len(files)} 個檔案，開始上傳...")
		zero_vec = [0.0] * config.embedding_dimensions if args.zero_vector else None
		
		for i, f in enumerate(files, 1):
			try:
				file_extension = f.suffix.lower()
				
				# 根據參數選擇處理方式
				if args.force_text or file_extension not in ['.pdf', '.txt', '.docx', '.html', '.md']:
					# 強制文字處理或不支援的格式
					print(f"[{i}/{len(files)}] 📄 作為純文字檔案處理 {f.name}...")
					text = f.read_text(encoding="utf-8", errors="ignore")
					metadata = {"source_file": f.name, "processing_method": "text"}
				else:
					# 使用 Azure Blob Storage 上傳並簡單提取內容
					print(f"[{i}/{len(files)}] 🌐 上傳到 Azure Blob {f.name}...")
					text, metadata = _upload_to_blob_simple(f)
				
				if not text.strip():
					print(f"[{i}/{len(files)}] {f.name} -> 空內容，略過")
					continue
				
				doc_id = f.stem
				client.index_document(
					doc_id=doc_id,
					title=f.name,
					content=text,
					metadata=metadata,
					category=args.category,
					tags=args.tags,
					vector=zero_vec,
					created_at=datetime.utcnow(),
				)
				print(f"[{i}/{len(files)}] 索引完成 id={doc_id}")
				
			except Exception as e:  # pragma: no cover - 使用者檔案例外
				print(f"[{i}/{len(files)}] {f.name} 失敗: {e}")
		
		print("批次 ingest 完成。")
		print(f"可以使用以下命令搜尋：python {__file__} search --text '您的查詢字串'")

	def _handle_upload_and_search_command(client: AzureAISearchExperimental, config: AzureSearchConfig, args) -> None:
		"""處理 upload-and-search 命令"""
		from pathlib import Path
		
		file_path = Path(args.file)
		if not file_path.exists():
			raise SystemExit(f"檔案不存在: {file_path}")
		
		print(f"=== 開始處理檔案: {file_path.name} ===")
		
		# 確保索引存在
		client.ensure_index(recreate=False)
		
		try:
			file_extension = file_path.suffix.lower()
			doc_id = f"{file_path.stem}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
			
			# 根據參數選擇處理方式
			if args.force_text or file_extension not in ['.pdf', '.txt', '.docx', '.html', '.md']:
				# 強制文字處理或不支援的格式
				print("📄 作為純文字檔案處理...")
				text = file_path.read_text(encoding="utf-8", errors="ignore")
				metadata = {"source_file": file_path.name, "processing_method": "text"}
				print(f"✅ 文字檔案讀取成功，內容長度: {len(text)} 字符")
			else:
				# 使用 Azure Blob Storage 上傳並簡單提取內容
				print(f"🌐 上傳到 Azure Blob {file_extension.upper()} 檔案...")
				text, metadata = _upload_to_blob_simple(file_path)
				if text:
					print(f"✅ 檔案處理成功，提取內容長度: {len(text)} 字符")
					if metadata.get('blob_url'):
						print(f"🌐 Blob URL: {metadata['blob_url']}")
				else:
					raise ValueError(f"{file_extension.upper()} 檔案處理失敗，無法提取內容")
			
			if not text.strip():
				raise ValueError("檔案內容為空")
			
			# 上傳到索引
			print(f"📤 將文件上傳到 Azure AI Search (ID: {doc_id})...")
			client.index_document(
				doc_id=doc_id,
				title=file_path.name,
				content=text,
				metadata=metadata,
				category=args.category,
				tags=args.tags,
				vector=None,  # 讓系統自動生成 embedding
				created_at=datetime.utcnow(),
			)
			print("✅ 文件已成功索引到 Azure AI Search")
			
			# 等待一小段時間確保索引完成
			import time
			print("⏳ 等待索引完成...")
			time.sleep(2)
			
			# 執行搜尋
			print(f"🔍 執行搜尋查詢: '{args.query}'")
			results = client.search(
				query_text=args.query,
				top_k=5,
				semantic=config.use_semantic_search
			)
			
			print(f"\n=== 搜尋結果 ({len(results)} 筆) ===")
			if results:
				for i, r in enumerate(results, 1):
					print(f"\n[{i}] 文件 ID: {r['id']}")
					print(f"    標題: {r['title']}")
					print(f"    相關性分數: {r['score']:.4f}")
					print(f"    內容摘要: {r['content'][:200]}...")
					if r.get('highlights'):
						print("    重點標記:")
						for h in r['highlights']:
							print(f"      - {h}")
					if r.get('metadata'):
						metadata_info = r['metadata']
						if isinstance(metadata_info, dict) and metadata_info.get('blob_url'):
							print(f"    Blob URL: {metadata_info['blob_url']}")
			else:
				print("❌ 未找到相符的結果")
				print("💡 建議：")
				print("   - 檢查查詢關鍵字是否正確")
				print("   - 嘗試使用文件中的其他關鍵字")
				print("   - 確認文件內容是否包含相關資訊")
			
			print(f"\n=== 完成！文件 ID: {doc_id} ===")
			
		except Exception as e:
			print(f"❌ 處理失敗: {e}")
			raise SystemExit(1)

	def build_parser() -> argparse.ArgumentParser:
		parser = argparse.ArgumentParser(
			prog="azure_ai_search",
			description="AzureAISearchExperimental 單檔操作：建立索引 / 上傳文件 / 搜尋 / 刪除 / demo",
		)
		sub = parser.add_subparsers(dest="command", required=True)

		# init / recreate index
		p_init = sub.add_parser("init", help="建立索引；若已存在則跳過")
		p_init.add_argument("--recreate", action="store_true", help="若存在則刪除後重建")

		# index document
		p_index = sub.add_parser("index", help="上傳或更新單一文件")
		p_index.add_argument("--id", required=True, help="文件 ID")
		p_index.add_argument("--title", required=True, help="標題")
		p_index.add_argument("--content", required=True, help="內容文字")
		p_index.add_argument("--category", help="分類 (可做 filter)")
		p_index.add_argument("--tags", nargs="*", help="標籤 (多值)")
		p_index.add_argument("--metadata", help="JSON 格式的額外中繼資料，例如 '{\"author\": \"me\"}'")
		p_index.add_argument("--zero-vector", action="store_true", help="使用全 0 向量 (僅測試用)")

		# search
		p_search = sub.add_parser("search", help="執行搜尋 (文字 / 向量 / 混合)")
		p_search.add_argument("--text", help="純文字查詢字串")
		p_search.add_argument("--zero-vector", action="store_true", help="附帶一個全 0 查詢向量 (模擬混合查詢)")
		p_search.add_argument("--top", type=int, default=5, help="回傳筆數 (default=5)")
		p_search.add_argument("--semantic", action="store_true", help="啟用語意搜尋")
		p_search.add_argument("--filter", help="OData filter 條件")

		# delete
		p_delete = sub.add_parser("delete", help="刪除文件")
		p_delete.add_argument("--id", required=True, help="文件 ID")

		# demo: 全流程
		sub.add_parser("demo", help="示範：建立索引 -> 上傳一筆 sample -> 搜尋 -> 刪除")

		# env: 顯示關鍵環境變數 (除錯用)
		p_env = sub.add_parser("env", help="顯示目前載入的關鍵 Azure 相關環境變數 (遮罩金鑰)")

		# ingest: 批次將某資料夾 (預設 test_files) 底下的文字檔加入索引
		p_ingest = sub.add_parser("ingest", help="批次上傳資料夾中文件 (預設掃描 *.txt, 支援 *.pdf)")
		p_ingest.add_argument("--dir", default="test_files", help="來源資料夾，預設 test_files")
		p_ingest.add_argument("--pattern", default="*.txt", help="檔案匹配 (glob)，預設 *.txt，也可用 *.pdf")
		p_ingest.add_argument("--recreate", action="store_true", help="開始前重建索引")
		p_ingest.add_argument("--zero-vector", action="store_true", help="為每個文件附加全 0 向量 (僅測試用)")
		p_ingest.add_argument("--category", default="ingested", help="批次文件的 category 欄位值")
		p_ingest.add_argument("--tags", nargs="*", default=["bulk"], help="批次文件的 tags (預設 ['bulk'])")
		p_ingest.add_argument("--force-text", action="store_true", help="強制將所有檔案作為純文字處理（不上傳到 Azure Blob）")

		# upload-and-search: 上傳單一檔案並立即搜尋
		p_upload_search = sub.add_parser("upload-and-search", help="上傳檔案到 Azure 並執行搜尋測試")
		p_upload_search.add_argument("--file", required=True, help="要上傳的檔案路徑")
		p_upload_search.add_argument("--query", required=True, help="搜尋查詢字串")
		p_upload_search.add_argument("--force-text", action="store_true", help="強制作為純文字處理（不上傳到 Azure Blob）")
		p_upload_search.add_argument("--category", default="test", help="文件分類")
		p_upload_search.add_argument("--tags", nargs="*", default=["test"], help="文件標籤")

		return parser

	def load_config() -> AzureSearchConfig:
		service_name = os.getenv("AZURE_SEARCH_SERVICE_NAME")
		if not service_name:
			raise SystemExit("環境變數 AZURE_SEARCH_SERVICE_NAME 未設定")
		api_key = os.getenv("AZURE_SEARCH_API_KEY")  # 可為 None => 使用 DefaultAzureCredential
		index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents")
		use_semantic = os.getenv("AZURE_SEARCH_USE_SEMANTIC", "true").lower() in {"1", "true", "yes"}
		return AzureSearchConfig(
			service_name=service_name,
			api_key=api_key,
			index_name=index_name,
			use_semantic_search=use_semantic,
		)

	parser = build_parser()
	args = parser.parse_args()

	config = load_config()
	client = AzureAISearchExperimental(config)

	if args.command == "init":
		client.ensure_index(recreate=args.recreate)
		print(f"Index '{config.index_name}' ready (recreate={args.recreate})")

	elif args.command == "index":
		metadata = {}
		if args.metadata:
			try:
				metadata = json.loads(args.metadata)
			except json.JSONDecodeError as e:
				raise SystemExit(f"metadata 不是合法 JSON: {e}")
		vector = None
		if args.zero_vector:
			vector = [0.0] * config.embedding_dimensions
		client.index_document(
			doc_id=args.id,
			title=args.title,
			content=args.content,
			metadata=metadata,
			category=args.category,
			tags=args.tags,
			vector=vector,
			created_at=datetime.utcnow(),
		)
		print(f"Indexed document id={args.id}")

	elif args.command == "search":
		query_vector = [0.0] * config.embedding_dimensions if args.zero_vector else None
		results = client.search(
			query_text=args.text,
			query_vector=query_vector,
			top_k=args.top,
			filter=args.filter,
			semantic=args.semantic or None,
		)
		print(f"Got {len(results)} results:")
		for i, r in enumerate(results, 1):
			print(f"[{i}] id={r['id']} score={r['score']:.4f} title={r['title']!r}")
			if r.get('highlights'):
				print("    highlights:")
				for h in r['highlights']:
					print(f"      - {h}")

	elif args.command == "delete":
		client.delete_document(args.id)
		print(f"Deleted document id={args.id}")

	elif args.command == "demo":
		print("[1] 確保索引存在 (若不存在則建立)...")
		client.ensure_index(recreate=False)
		doc_id = "demo-doc-001"
		print("[2] 上傳示例文件 demo-doc-001 ...")
		client.index_document(
			doc_id=doc_id,
			title="示例文件",
			content="這是一個示範文件內容，用於 Azure AI Search 單檔執行 demo。",
			metadata={"purpose": "demo"},
			category="demo",
			tags=["example", "demo"],
			vector=[0.0] * config.embedding_dimensions,
			created_at=datetime.utcnow(),
		)
		print("[3] 執行搜尋 text='示例' ...")
		results = client.search(query_text="示例", top_k=3)
		for r in results:
			print(f"- {r['id']} score={r['score']:.4f} title={r['title']}")
		print("[4] 清理刪除示例文件 ...")
		client.delete_document(doc_id)
		print("Demo 完成。")

	elif args.command == "env":
		# 遮罩金鑰輸出，供使用者確認是否成功載入 .env
		def mask(v: str | None, keep: int = 4):
			if not v:
				return "<unset>"
			return v[:keep] + "***" if len(v) > keep else "***"
		keys = [
			"AZURE_SEARCH_SERVICE_NAME",
			"AZURE_SEARCH_API_KEY", 
			"AZURE_SEARCH_INDEX_NAME",
			"AZURE_SEARCH_USE_SEMANTIC",
			"AZURE_OPENAI_API_KEY",
			"AZURE_OPENAI_ENDPOINT",
			"AZURE_STORAGE_ACCOUNT_NAME",
			"AZURE_STORAGE_ACCOUNT_KEY",
			"AZURE_STORAGE_CONTAINER_NAME", 
			"AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
			"AZURE_DOCUMENT_INTELLIGENCE_KEY",
		]
		print("目前主要環境變數：")
		for k in keys:
			print(f"  {k} = {mask(os.getenv(k))}")
		sys.exit(0)

	elif args.command == "ingest":
		_handle_ingest_command(client, config, args)

	elif args.command == "upload-and-search":
		_handle_upload_and_search_command(client, config, args)

	else:  # defensive
		parser.print_help()
		raise SystemExit(1)


