# Design Document: Lightweight RAG System for Dietary Supplements

## Overview

本系統為一套輕量化 RAG（Retrieval-Augmented Generation）系統，專注於保健食品學術文獻知識庫。系統以三個獨立 Python 腳本為核心，透過 pgvector 向量資料庫、sentence-transformers 本地嵌入模型與 LiteLLM 統一 LLM 介面，實現從 PDF 論文到可查詢知識庫的完整流程。

系統設計原則：
- **輕量化**：無需自架 LLM，使用 HuggingFace Inference API 免費額度
- **本地嵌入**：sentence-transformers 本地模型，不依賴外部嵌入 API
- **冪等性**：重複執行不產生重複資料
- **可追溯性**：所有回答均附帶學術文獻來源引用

---

## Architecture

```mermaid
graph TB
    subgraph "Data Pipeline (data_update.py)"
        A[data/raw/*.pdf] --> B[FileReader]
        B --> C[TextCleaner]
        C --> D[data/processed/*.txt]
        D --> E[TextChunker]
        E --> F[EmbeddingEngine]
        F --> G[VectorStore Writer]
        G --> H[(pgvector DB)]
    end

    subgraph "Query Pipeline (rag_query.py)"
        I[User Query] --> J[QueryEmbedder]
        J --> K[SimilaritySearch]
        K --> H
        H --> L[ContextBuilder]
        L --> M[PromptAssembler]
        M --> N[LiteLLM]
        N --> O[Answer + Citations]
    end

    subgraph "Skill Builder (skill_builder.py)"
        P[Global Questions] --> Q[RAG Query Engine]
        Q --> R[LLM Synthesizer]
        R --> S[SkillDocFormatter]
        S --> T[skill.md]
    end

    subgraph "Infrastructure"
        U[.env] --> V[Config Loader]
        W[docker-compose.yml] --> H
    end
```

### 元件職責

| 元件 | 腳本 | 職責 |
|------|------|------|
| FileReader | data_update.py | 讀取 .pdf/.md/.txt，提取純文字 |
| TextCleaner | data_update.py | 移除 HTML 標籤、頁首頁尾、重複空白 |
| TextChunker | data_update.py | 固定長度 + overlap 分塊 |
| EmbeddingEngine | data_update.py | sentence-transformers 本地嵌入 |
| VectorStore Writer | data_update.py | 寫入 pgvector，支援增量更新 |
| QueryEmbedder | rag_query.py | 將查詢文字轉為向量 |
| SimilaritySearch | rag_query.py | pgvector 餘弦相似度檢索 |
| PromptAssembler | rag_query.py | 組裝含 context 與 citation 的 prompt |
| LiteLLM | rag_query.py / skill_builder.py | 統一 LLM 呼叫介面 |
| SkillDocFormatter | skill_builder.py | 生成符合格式規範的 skill.md |

---

## Components and Interfaces

### data_update.py

```python
# 主要函式介面

def load_config() -> dict:
    """從 .env 載入設定：EMBEDDING_MODEL、PGVECTOR_CONNECTION_STRING"""

def read_file(path: str) -> str:
    """讀取 .pdf/.md/.txt 檔案，回傳純文字內容。不支援格式則記錄警告並回傳 None"""

def clean_text(text: str) -> str:
    """移除 HTML 標籤、頁首頁尾標記、重複空白。冪等函式：clean(clean(x)) == clean(x)"""

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """
    將文字切分為 chunks。
    回傳: [{"text": str, "chunk_index": int}]
    """

def embed_texts(texts: list[str], model_name: str) -> list[list[float]]:
    """使用 sentence-transformers 將文字列表轉為向量列表"""

def compute_file_hash(path: str) -> str:
    """計算檔案 SHA-256 hash，用於增量更新判斷"""

def get_processed_files(conn) -> dict[str, str]:
    """從 Vector_Store 取得已處理檔案的 hash 記錄"""

def upsert_chunks(conn, chunks: list[dict]) -> None:
    """將 chunks 寫入 pgvector，先刪除同來源舊資料再插入"""

def run_update(data_dir: str, rebuild: bool = False) -> None:
    """主流程：掃描 data/raw/，增量或全量更新 Vector_Store"""
```

**CLI 介面：**
```
python data_update.py [--rebuild] [--data-dir <路徑>]
```

### rag_query.py

```python
def embed_query(query: str, model_name: str) -> list[float]:
    """將查詢文字轉為向量"""

def similarity_search(conn, query_vector: list[float], top_k: int = 5) -> list[dict]:
    """
    pgvector 餘弦相似度檢索。
    回傳: [{"text": str, "source_file": str, "chunk_index": int, "score": float}]
    """

def assemble_prompt(query: str, chunks: list[dict], history: list[dict]) -> list[dict]:
    """
    組裝 LiteLLM messages 格式的 prompt。
    包含：system prompt（保健食品領域指令）、對話歷史（最近 3 輪）、context chunks、user query
    """

def format_answer(response: str, chunks: list[dict]) -> str:
    """格式化回答，附加 citation 列表（來源檔案名稱 + 段落編號）"""

def run_query(query: str, top_k: int = 5, model: str = "huggingface/HuggingFaceH4/zephyr-7b-beta") -> str:
    """執行單次 RAG 查詢，回傳含 citation 的回答"""

def run_interactive(top_k: int = 5, model: str = "huggingface/HuggingFaceH4/zephyr-7b-beta") -> None:
    """互動式多輪對話模式，維護最近 3 輪對話歷史"""
```

**CLI 介面：**
```
python rag_query.py [--query "<問題>"] [--top-k <數字>] [--model <模型名稱>]
```

### skill_builder.py

```python
DEFAULT_QUESTIONS = [
    "這個知識庫涵蓋哪些保健食品成分？",
    "各成分的主要功效與適用族群為何？",
    "文獻中最常見的劑量建議範圍為何？",
    "有哪些成分具有交互作用或禁忌症的研究？",
    "目前研究最充分的保健食品成分有哪些？",
]

def load_questions(path: str | None) -> list[str]:
    """載入問題清單，若 path 為 None 則使用 DEFAULT_QUESTIONS"""

def gather_knowledge(questions: list[str], model: str, top_k: int = 5) -> list[dict]:
    """對每個問題執行 RAG 查詢，收集問答對"""

def synthesize_skill_doc(qa_pairs: list[dict], model: str) -> str:
    """透過 LLM 將問答對整合為符合格式規範的 skill.md 內容"""

def validate_skill_doc(content: str) -> bool:
    """驗證 skill.md 包含所有必要章節"""

def run_build(output: str = "skill.md", model: str = "huggingface/HuggingFaceH4/zephyr-7b-beta",
              questions_path: str | None = None) -> None:
    """主流程：收集知識 → 整合 → 驗證 → 輸出"""
```

**CLI 介面：**
```
python skill_builder.py [--output <路徑>] [--model <模型名稱>] [--questions <路徑>]
```

---

## Data Models

### pgvector 資料庫 Schema

```sql
-- 啟用 pgvector 擴充套件
CREATE EXTENSION IF NOT EXISTS vector;

-- 主要 chunks 資料表
CREATE TABLE IF NOT EXISTS document_chunks (
    id          SERIAL PRIMARY KEY,
    source_file VARCHAR(512) NOT NULL,        -- 來源檔案名稱（相對於 data/raw/）
    chunk_index INTEGER NOT NULL,             -- 段落編號（0-based）
    text        TEXT NOT NULL,                -- chunk 文字內容
    embedding   vector(384),                  -- sentence-transformers 向量（384 維）
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (source_file, chunk_index)         -- 防止重複插入
);

-- 向量相似度索引（IVFFlat，適合中小型資料集）
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 檔案處理記錄表（用於增量更新）
CREATE TABLE IF NOT EXISTS processed_files (
    id           SERIAL PRIMARY KEY,
    file_path    VARCHAR(512) UNIQUE NOT NULL, -- 相對路徑
    file_hash    VARCHAR(64) NOT NULL,          -- SHA-256 hash
    processed_at TIMESTAMP DEFAULT NOW()
);
```

### Chunk 資料結構（Python）

```python
@dataclass
class Chunk:
    text: str
    source_file: str      # 相對於 data/raw/ 的路徑
    chunk_index: int      # 0-based 段落編號
    embedding: list[float] | None = None

@dataclass
class QueryResult:
    text: str
    source_file: str
    chunk_index: int
    score: float          # 餘弦相似度分數（0-1）
```

### Skill Document 格式

```markdown
---
knowledge_domain: Dietary Supplements / Nutraceuticals
data_sources: <N> academic papers
last_updated: YYYY-MM-DD
agent_type: Health & Nutrition Research Assistant
---

# Skill: Dietary Supplements Knowledge Base

## Overview
（200 字以內的知識摘要）

## Core Concepts
（5-15 個核心概念，含具體成分名稱或功效類別）

## Key Trends
（3-10 個研究趨勢）

## Key Entities
（作者、機構、工具、框架等實體列表）

## Methodology & Best Practices
（研究方法與最佳實踐）

## Knowledge Gaps & Limitations
（知識空白與限制）

## Example Q&A
（3-5 組問答對）

## Source References
（來源論文列表）
```

### 環境變數

| 變數名稱 | 說明 | 範例值 |
|----------|------|--------|
| `HF_TOKEN` | HuggingFace API Token | `hf_xxxxxxxxxxxx` |
| `EMBEDDING_PROVIDER` | 嵌入提供者 | `sentence-transformers` |
| `EMBEDDING_MODEL` | 嵌入模型名稱 | `paraphrase-multilingual-MiniLM-L12-v2` |
| `PGVECTOR_CONNECTION_STRING` | PostgreSQL 連線字串 | `postgresql://user:pass@localhost:5432/ragdb` |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 文字清理冪等性

*For any* 文字輸入 `x`，執行清理函式兩次應與執行一次產生相同結果：`clean(clean(x)) == clean(x)`

**Validates: Requirements 2.4**

### Property 2: 分塊完整性

*For any* 非空文字輸入，切分後所有 chunk 的文字內容聯集應涵蓋原始文字的所有實質內容（不遺漏任何非空白字元序列）

**Validates: Requirements 3.4**

### Property 3: 分塊 metadata 完整性

*For any* 文字輸入與來源檔案名稱，生成的每個 chunk 都應包含 `source_file` 和 `chunk_index` 欄位，且 `chunk_index` 應為連續的非負整數序列

**Validates: Requirements 3.3**

### Property 4: 嵌入確定性

*For any* 文字輸入，對同一文字執行嵌入兩次應產生完全相同的向量（逐元素相等）

**Validates: Requirements 4.3**

### Property 5: Vector Store 寫入冪等性

*For any* 相同的 `data/` 目錄內容，執行 `data_update.py` 兩次後，`document_chunks` 資料表中的資料應與執行一次的結果完全相同（相同的行數與內容）

**Validates: Requirements 6.5**

### Property 6: 增量更新正確性

*For any* 檔案集合，若某檔案的 SHA-256 hash 未變更，則增量執行後該檔案對應的 chunks 在 Vector Store 中應保持不變

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 7: 檢索數量上限

*For any* 查詢向量與任意 `top_k` 值（1 ≤ top_k ≤ 100），相似度檢索回傳的結果數量應不超過 `top_k`，且不超過 Vector Store 中的實際 chunk 總數

**Validates: Requirements 7.2**

### Property 8: 回答包含 Citation

*For any* 查詢，若 Vector Store 中存在相關 chunk，RAG 查詢的輸出應包含至少一筆 citation，格式為「來源檔案名稱 + 段落編號」

**Validates: Requirements 7.4, 14.2, 15.2**

### Property 9: 對話歷史保留

*For any* 對話輪數 `n`（n ≥ 3），互動式模式中傳入 LLM 的 messages 應包含最近 3 輪的問答記錄（6 條 user/assistant 訊息）

**Validates: Requirements 8.3**

### Property 10: Skill Document 格式完整性

*For any* RAG 問答輸入，生成的 skill.md 應包含所有必要章節：Metadata、Overview、Core Concepts、Key Trends、Key Entities、Methodology & Best Practices、Knowledge Gaps & Limitations、Example Q&A、Source References

**Validates: Requirements 10.5, 11.1, 11.5, 11.6**

### Property 11: Skill Document 數量約束

*For any* RAG 問答輸入，生成的 skill.md 中：
- Overview 章節字數應不超過 200 字
- Core Concepts 數量應在 5 至 15 個之間
- Key Trends 數量應在 3 至 10 個之間
- Example Q&A 數量應在 3 至 5 組之間

**Validates: Requirements 11.2, 11.3, 11.4, 11.7**

---

## Error Handling

### 錯誤分類與處理策略

| 錯誤類型 | 觸發條件 | 處理方式 |
|----------|----------|----------|
| 不支援的檔案格式 | 遇到 .docx、.xlsx 等格式 | 記錄 WARNING，跳過該檔案，繼續處理其他檔案 |
| PDF 解析失敗 | PDF 損毀或加密 | 記錄 ERROR，跳過該檔案，繼續處理其他檔案 |
| Embedding 模型載入失敗 | 模型不存在或記憶體不足 | 記錄 ERROR，終止執行（無法繼續） |
| Vector Store 連線失敗 | 資料庫未啟動或連線字串錯誤 | 記錄 ERROR，終止執行（無法繼續） |
| LiteLLM 呼叫失敗 | API Token 無效、配額耗盡、網路錯誤 | 記錄 ERROR，輸出錯誤訊息，提示使用者重試 |
| Vector Store 無相關結果 | 查詢向量與所有 chunks 相似度過低 | 回傳「目前知識庫中無相關資訊」訊息，不呼叫 LLM |
| 環境變數缺失 | .env 未設定必要變數 | 啟動時檢查，記錄 ERROR 並列出缺失變數，終止執行 |

### 錯誤訊息格式

```python
# 統一使用 Python logging 模組
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
```

### 無結果處理

當 Vector Store 中無相關 chunk 時（相似度分數低於閾值 0.3，或結果為空），系統應：
1. 不呼叫 LLM（避免幻覺）
2. 回傳固定訊息：「目前知識庫中無與您查詢相關的文獻資料。請確認知識庫已包含相關論文，或嘗試調整查詢關鍵字。」

---

## Testing Strategy

### 測試框架

- **單元測試 / 屬性測試**：`pytest` + `hypothesis`（Python PBT 函式庫）
- **最小迭代次數**：每個屬性測試 100 次（hypothesis 預設）
- **測試標記格式**：`# Feature: lightweight-rag-system, Property {N}: {property_text}`

### 屬性測試（Property-Based Tests）

使用 `hypothesis` 函式庫實作以下屬性測試：

```python
from hypothesis import given, settings
from hypothesis import strategies as st

# Property 1: 文字清理冪等性
@given(st.text())
@settings(max_examples=100)
def test_clean_text_idempotent(text):
    # Feature: lightweight-rag-system, Property 1: clean(clean(x)) == clean(x)
    assert clean_text(clean_text(text)) == clean_text(text)

# Property 2: 分塊完整性
@given(st.text(min_size=1), st.integers(min_value=64, max_value=1024),
       st.integers(min_value=0, max_value=63))
@settings(max_examples=100)
def test_chunking_completeness(text, chunk_size, overlap):
    # Feature: lightweight-rag-system, Property 2: chunks cover all content
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    all_text = " ".join(c["text"] for c in chunks)
    # 驗證原始文字的所有非空白 token 都出現在 chunks 中
    ...

# Property 3: 分塊 metadata 完整性
@given(st.text(min_size=1), st.text(min_size=1))
@settings(max_examples=100)
def test_chunk_metadata(text, source_file):
    # Feature: lightweight-rag-system, Property 3: each chunk has source_file and chunk_index
    chunks = chunk_text(text, source_file=source_file)
    for i, chunk in enumerate(chunks):
        assert "source_file" in chunk
        assert "chunk_index" in chunk
        assert chunk["chunk_index"] == i

# Property 4: 嵌入確定性（使用 mock 避免實際載入模型）
@given(st.text(min_size=1, max_size=512))
@settings(max_examples=100)
def test_embedding_deterministic(text):
    # Feature: lightweight-rag-system, Property 4: embed(x) == embed(x)
    vec1 = embed_texts([text], model_name=TEST_MODEL)[0]
    vec2 = embed_texts([text], model_name=TEST_MODEL)[0]
    assert vec1 == vec2

# Property 7: 檢索數量上限
@given(st.integers(min_value=1, max_value=20))
@settings(max_examples=100)
def test_retrieval_top_k(top_k):
    # Feature: lightweight-rag-system, Property 7: results <= top_k
    results = similarity_search(mock_conn, query_vector, top_k=top_k)
    assert len(results) <= top_k

# Property 8: 回答包含 Citation
@given(st.text(min_size=1))
@settings(max_examples=100)
def test_answer_contains_citation(query):
    # Feature: lightweight-rag-system, Property 8: answer includes citation
    answer = format_answer(mock_response, mock_chunks)
    assert any(chunk["source_file"] in answer for chunk in mock_chunks)

# Property 9: 對話歷史保留
@given(st.integers(min_value=3, max_value=10))
@settings(max_examples=100)
def test_conversation_history(n_turns):
    # Feature: lightweight-rag-system, Property 9: messages include last 3 turns
    history = generate_mock_history(n_turns)
    messages = assemble_prompt("test query", [], history)
    user_msgs = [m for m in messages if m["role"] == "user"]
    assert len([m for m in user_msgs if m.get("is_history")]) >= 3

# Property 10 & 11: Skill Document 格式完整性與數量約束
@given(st.lists(st.fixed_dictionaries({
    "question": st.text(min_size=1),
    "answer": st.text(min_size=1)
}), min_size=1, max_size=10))
@settings(max_examples=100)
def test_skill_doc_format(qa_pairs):
    # Feature: lightweight-rag-system, Property 10: skill.md contains all required sections
    content = synthesize_skill_doc(qa_pairs, model=MOCK_MODEL)
    required_sections = ["## Overview", "## Core Concepts", "## Key Trends",
                         "## Key Entities", "## Methodology", "## Knowledge Gaps",
                         "## Example Q&A", "## Source References"]
    for section in required_sections:
        assert section in content
```

### 單元測試（Example-Based Tests）

| 測試項目 | 測試內容 |
|----------|----------|
| 環境變數讀取 | 設定 EMBEDDING_MODEL，驗證系統使用該模型名稱 |
| 預設模型名稱 | 不設定 --model，驗證使用 `huggingface/HuggingFaceH4/zephyr-7b-beta` |
| --rebuild 旗標 | 執行後驗證 Vector Store 被清空再重建 |
| 退出指令 | 輸入 exit/quit，驗證互動模式結束 |
| 預設問題清單 | 驗證 DEFAULT_QUESTIONS 包含五個指定問題 |
| LiteLLM 錯誤處理 | 模擬 API 錯誤，驗證輸出錯誤訊息 |
| 無結果處理 | 空 Vector Store 查詢，驗證回傳無結果訊息 |

### 整合測試（Integration Tests）

| 測試項目 | 測試內容 |
|----------|----------|
| 完整 RAG 流程 | 使用 mock LLM，驗證 Query Embedding → Search → Prompt → LLM 依序執行 |
| Skill Builder 整合 | 使用 mock LLM，驗證所有問題的回答都被傳入整合 prompt |
| Study Population 指令 | 驗證 prompt 中包含要求說明 Study_Population 的指令 |

### Smoke Tests

| 測試項目 | 測試內容 |
|----------|----------|
| .env.example 存在 | 驗證包含四個必要環境變數 |
| docker-compose.yml 存在 | 驗證 pgvector 服務設定正確 |
| requirements.txt 存在 | 驗證包含所有必要套件 |
| README.md 存在 | 驗證包含必要章節 |
