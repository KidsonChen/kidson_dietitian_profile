# 保健食品 RAG 系統

一套輕量化 Retrieval-Augmented Generation（RAG）系統，專注於**保健食品（Dietary Supplements / Nutraceuticals）**學術文獻知識庫，支援成分功效查詢、劑量建議查詢，並自動生成 AI Agent 可用的技能文件。

---

## 1. 專案簡介

### 知識主題

保健食品（Dietary Supplements / Nutraceuticals）學術文獻，涵蓋 Omega-3、薑黃素（Curcumin）、維生素 C/D、鈣、鎂、益生菌等常見成分的功效、劑量建議與禁忌症研究。

### 資料來源

使用者自行放置於 `data/raw/` 的學術論文 PDF 檔案。系統目前已內建 18 篇論文，涵蓋：

- Calcium、Magnesium、Iron、Iodine、Zinc、Selenium
- Vitamin C、Vitamin D、Multivitamin
- Omega-3、Coenzyme Q10、Curcumin、Lutein、Melatonin
- Glucosamine、Probiotics、Dietary Fiber
- Tolerable Upper Intake Levels（可耐受上限攝取量）

### 核心功能

- **成分功效查詢**：查詢特定成分（如魚油 Omega-3）的生理功效與適用族群，附學術文獻引用
- **劑量建議查詢**：查詢特定成分的建議攝取量，依不同研究族群分別列出
- **互動式多輪問答**：維護對話歷史，支援追問與上下文連貫回答
- **技能文件生成**：自動掃描知識庫，生成符合 Agent Skill 格式的 `skill.md`

### 技術選型

| 元件 | 技術 | 說明 |
|------|------|------|
| 向量資料庫 | pgvector（PostgreSQL 擴充套件） | 輕量、無需額外服務，與 PostgreSQL 整合 |
| 嵌入模型 | sentence-transformers | 本地執行、免費、支援中英文多語言 |
| LLM 介面 | LiteLLM + HuggingFace Inference API | 統一介面、免費額度、可輕易切換模型 |
| 預設 LLM | `HuggingFaceH4/zephyr-7b-beta` | 透過 HuggingFace 免費 Inference API 存取 |
| 預設嵌入模型 | `paraphrase-multilingual-MiniLM-L12-v2` | 384 維向量，支援中英文 |

---

## 2. 系統架構

```mermaid
graph LR
    A[data/raw/] --> B[data_update.py]
    B --> C{Chunking\nStrategy}
    C --> D[Embedding Model\nsentence-transformers]
    D --> E[(pgvector)]
    E --> F[rag_query.py]
    F --> G[LiteLLM\nHuggingFace API]
    G --> H[skill_builder.py]
    H --> I[skill.md]
```

### 完整資料流程

```mermaid
graph TB
    subgraph "Data Pipeline (data_update.py)"
        A[data/raw/*.pdf] --> B[FileReader]
        B --> C[TextCleaner]
        C --> D[data/processed/*.txt]
        D --> E[TextChunker\n512字元 + 64字元 overlap]
        E --> F[EmbeddingEngine\nsentence-transformers]
        F --> G[VectorStore Writer\n增量更新 SHA-256]
        G --> H[(pgvector DB)]
    end

    subgraph "Query Pipeline (rag_query.py)"
        I[User Query] --> J[QueryEmbedder]
        J --> K[SimilaritySearch\n餘弦相似度]
        K --> H
        H --> L[ContextBuilder]
        L --> M[PromptAssembler\n含對話歷史]
        M --> N[LiteLLM]
        N --> O[Answer + Citations]
    end

    subgraph "Skill Builder (skill_builder.py)"
        P[5個全域問題] --> Q[RAG Query Engine]
        Q --> R[LLM Synthesizer]
        R --> S[SkillDocFormatter]
        S --> T[skill.md]
    end
```

---

## 3. 快速開始

### 環境需求

- Python 3.10+
- Docker & Docker Compose
- HuggingFace 帳號（免費，用於取得 `HF_TOKEN`）

### 安裝步驟

**1. Clone 專案**

```bash
git clone <repository-url>
cd <project-directory>
```

**2. 安裝 Python 套件**

```bash
pip install -r requirements.txt
```

**3. 設定環境變數**

```bash
cp .env.example .env
```

開啟 `.env`，填入你的 HuggingFace API Token：

```
HF_TOKEN=hf_your_token_here
```

其餘變數使用預設值即可（詳見[環境變數說明](#4-環境變數說明)）。

**4. 啟動 pgvector 資料庫**

```bash
docker-compose up -d
```

確認服務啟動：

```bash
docker-compose ps
```

**5. 放入論文 PDF**

將學術論文 PDF 放入 `data/raw/` 目錄（系統已內建 18 篇論文，可直接使用）。

### 執行流程

**建立向量索引（首次使用或新增文件後）**

```bash
python data_update.py
```

**全量重建索引**

```bash
python data_update.py --rebuild
```

**單次查詢**

```bash
python rag_query.py --query "魚油 Omega-3 的功效是什麼？"
```

**指定檢索數量與模型**

```bash
python rag_query.py --query "維生素 D 每日建議攝取量" --top-k 10 --model huggingface/HuggingFaceH4/zephyr-7b-beta
```

**互動式多輪問答**

```bash
python rag_query.py
```

進入互動模式後，輸入 `exit` 或 `quit` 結束。

**生成 skill.md 技能文件**

```bash
python skill_builder.py
```

**指定輸出路徑與自訂問題**

```bash
python skill_builder.py --output my_skill.md --questions custom_questions.txt
```

---

## 4. 環境變數說明

`.env` 檔案包含以下環境變數：

| 變數名稱 | 必填 | 說明 | 範例值 |
|----------|------|------|--------|
| `HF_TOKEN` | 是 | HuggingFace 帳號的 API Token，用於存取 HuggingFace Inference API 免費額度。前往 [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) 取得。 | `hf_xxxxxxxxxxxx` |
| `EMBEDDING_PROVIDER` | 否 | 嵌入模型提供者，目前支援 `sentence-transformers`（本地執行）。 | `sentence-transformers` |
| `EMBEDDING_MODEL` | 否 | sentence-transformers 模型名稱。預設使用支援中英文的多語言模型。 | `paraphrase-multilingual-MiniLM-L12-v2` |
| `PGVECTOR_CONNECTION_STRING` | 否 | PostgreSQL 連線字串，指向 pgvector 資料庫。使用 `docker-compose up -d` 啟動的預設服務時，使用預設值即可。 | `postgresql://raguser:ragpassword@localhost:5432/ragdb` |

---

## 5. 設計決策說明

### 為何選擇 pgvector

pgvector 是 PostgreSQL 的向量擴充套件，直接整合於現有的關聯式資料庫中，無需額外部署獨立的向量資料庫服務（如 Pinecone、Weaviate）。對於中小型知識庫（數千至數萬個 chunk），pgvector 的 IVFFlat 索引提供足夠的查詢效能，且透過 Docker Compose 一鍵啟動，大幅降低部署複雜度。

### 為何選擇 sentence-transformers

sentence-transformers 在本地執行，不依賴任何外部嵌入 API，確保系統在無網路或 API 配額耗盡時仍可正常建立索引。`paraphrase-multilingual-MiniLM-L12-v2` 模型支援 50+ 種語言（含中文與英文），使用者可以中文或英文名稱查詢相同的保健食品成分（如「薑黃素」與「Curcumin」）。

### 為何選擇 LiteLLM + HuggingFace Inference API

LiteLLM 提供統一的 LLM 呼叫介面，透過 `huggingface/<model-name>` 格式即可切換不同的 HuggingFace 模型，無需修改程式碼。HuggingFace Inference API 提供免費額度，適合個人研究與原型開發，無需自架 LLM 服務。

### Chunking 策略

系統採用**固定長度 + overlap** 策略：

- **Chunk 大小**：512 字元（預設）
- **Overlap**：64 字元（前後 chunk 重疊部分）

Overlap 設計確保跨 chunk 邊界的語義資訊不會遺失，提升檢索相關性。使用者可透過程式碼參數調整 `chunk_size` 與 `overlap` 大小。

### 增量更新機制

每次執行 `data_update.py` 時，系統會：

1. 計算 `data/raw/` 中每個檔案的 **SHA-256 hash**
2. 與 `processed_files` 資料表中的記錄比對
3. 僅重新處理 hash 變更（新增或修改）的檔案
4. 跳過未變更的檔案，避免重複嵌入與寫入

此機制確保重複執行不會產生重複資料（冪等性），同時大幅縮短增量更新的執行時間。使用 `--rebuild` 旗標可強制清除所有資料並全量重建。
