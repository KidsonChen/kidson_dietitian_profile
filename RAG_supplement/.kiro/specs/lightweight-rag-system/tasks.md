# Implementation Plan: Lightweight RAG System for Dietary Supplements

## Overview

以 Python 實作三個核心腳本（`data_update.py`、`rag_query.py`、`skill_builder.py`），搭配 pgvector 向量資料庫、sentence-transformers 本地嵌入模型與 LiteLLM 統一 LLM 介面，建立完整的保健食品學術文獻 RAG 系統。

## Tasks

- [x] 1. 建立專案基礎結構與環境設定
  - 建立 `data/raw/`、`data/processed/` 目錄結構
  - 建立 `.env.example`，包含 `HF_TOKEN`、`EMBEDDING_PROVIDER`、`EMBEDDING_MODEL`、`PGVECTOR_CONNECTION_STRING` 四個環境變數範本
  - 建立 `docker-compose.yml`，設定 pgvector（PostgreSQL + pgvector 擴充套件）服務
  - 建立 `requirements.txt`，列出所有必要套件：`psycopg2-binary`、`pgvector`、`sentence-transformers`、`litellm`、`pypdf2` 或 `pdfplumber`、`python-dotenv`、`pytest`、`hypothesis`
  - _Requirements: 12.1, 12.2, 12.3_

- [x] 2. 實作 data_update.py — 核心工具函式
  - [x] 2.1 實作 `load_config()` 與環境變數驗證
    - 從 `.env` 讀取 `EMBEDDING_MODEL`、`PGVECTOR_CONNECTION_STRING`
    - 啟動時檢查必要環境變數，缺失時記錄 ERROR 並列出缺失變數後終止執行
    - _Requirements: 5.2, 4.2_

  - [x] 2.2 實作 `read_file(path: str) -> str`
    - 支援 `.pdf`（使用 pdfplumber 或 PyPDF2 提取文字）、`.md`、`.txt` 三種格式
    - 不支援格式時記錄 WARNING 並回傳 `None`，繼續處理其他檔案
    - PDF 解析失敗時記錄 ERROR 並回傳 `None`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.3 實作 `clean_text(text: str) -> str`
    - 移除 HTML 標籤（使用 regex）、頁首頁尾標記、重複空白
    - 確保函式為冪等函式：`clean(clean(x)) == clean(x)`
    - _Requirements: 2.1, 2.3, 2.4_

  - [ ]* 2.4 撰寫 Property 1 屬性測試：文字清理冪等性
    - **Property 1: `clean(clean(x)) == clean(x)`**
    - 使用 `hypothesis` 的 `st.text()` 策略，`max_examples=100`
    - **Validates: Requirements 2.4**

  - [x] 2.5 實作 `chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]`
    - 固定長度加 overlap 策略切分文字
    - 每個 chunk 包含 `text`、`source_file`、`chunk_index` 欄位
    - 確保所有 chunk 聯集涵蓋原始文字的完整內容
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 2.6 撰寫 Property 2 屬性測試：分塊完整性
    - **Property 2: 切分後所有 chunk 文字聯集涵蓋原始文字所有實質內容**
    - 使用 `st.text(min_size=1)`、`st.integers` 策略
    - **Validates: Requirements 3.4**

  - [ ]* 2.7 撰寫 Property 3 屬性測試：分塊 metadata 完整性
    - **Property 3: 每個 chunk 包含 `source_file` 和 `chunk_index`，且 `chunk_index` 為連續非負整數**
    - **Validates: Requirements 3.3**

- [x] 3. 實作 data_update.py — 嵌入與向量寫入
  - [x] 3.1 實作 `embed_texts(texts: list[str], model_name: str) -> list[list[float]]`
    - 使用 sentence-transformers 本地模型將文字列表轉為向量列表
    - Embedding 模型載入失敗時記錄 ERROR 並終止執行
    - _Requirements: 4.1, 4.2, 4.4_

  - [ ]* 3.2 撰寫 Property 4 屬性測試：嵌入確定性
    - **Property 4: 對同一文字執行嵌入兩次應產生完全相同的向量**
    - 使用 mock 避免實際載入模型，`st.text(min_size=1, max_size=512)`
    - **Validates: Requirements 4.3**

  - [x] 3.3 實作 pgvector 資料庫初始化
    - 建立 `document_chunks` 資料表（含 `source_file`、`chunk_index`、`text`、`embedding` 欄位）
    - 建立 `processed_files` 資料表（含 `file_path`、`file_hash` 欄位）
    - 建立 IVFFlat 向量相似度索引
    - Vector Store 連線失敗時記錄 ERROR 並終止執行
    - _Requirements: 5.1, 5.3, 5.4_

  - [x] 3.4 實作 `compute_file_hash(path: str) -> str` 與 `get_processed_files(conn) -> dict`
    - 計算檔案 SHA-256 hash
    - 從 `processed_files` 資料表取得已處理檔案的 hash 記錄
    - _Requirements: 6.2_

  - [x] 3.5 實作 `upsert_chunks(conn, chunks: list[dict]) -> None`
    - 先刪除同 `source_file` 的舊資料，再批次插入新 chunks
    - 利用 `UNIQUE (source_file, chunk_index)` 約束防止重複插入
    - _Requirements: 5.1, 6.5_

- [x] 4. 實作 data_update.py — 主流程與增量更新
  - [x] 4.1 實作 `run_update(data_dir: str, rebuild: bool = False) -> None`
    - 增量模式：比對 File_Hash，跳過未變更檔案
    - `--rebuild` 模式：清除 Vector Store 所有資料後全量重建
    - 掃描 `data/raw/`，依序執行 read → clean → save processed → chunk → embed → upsert
    - 將清理後文字儲存為 `data/processed/<filename>.txt`（UTF-8 編碼）
    - _Requirements: 2.2, 6.1, 6.2, 6.3, 6.4_

  - [ ]* 4.2 撰寫 Property 5 屬性測試：Vector Store 寫入冪等性
    - **Property 5: 對相同 `data/` 目錄執行兩次後，`document_chunks` 資料與執行一次結果相同**
    - 使用 mock 資料庫連線
    - **Validates: Requirements 6.5**

  - [ ]* 4.3 撰寫 Property 6 屬性測試：增量更新正確性
    - **Property 6: 若檔案 SHA-256 hash 未變更，增量執行後該檔案對應 chunks 保持不變**
    - **Validates: Requirements 6.1, 6.2, 6.3**

  - [x] 4.4 實作 CLI 介面（argparse）
    - 支援 `--rebuild` 旗標與 `--data-dir <路徑>` 參數
    - _Requirements: 6.4_

- [x] 5. Checkpoint — 確認 data_update.py 完整可執行
  - 確保所有測試通過，ask the user if questions arise.

- [x] 6. 實作 rag_query.py — 核心查詢函式
  - [x] 6.1 實作 `embed_query(query: str, model_name: str) -> list[float]`
    - 重用 sentence-transformers 模型將查詢文字轉為向量
    - _Requirements: 7.5_

  - [x] 6.2 實作 `similarity_search(conn, query_vector, top_k: int = 5) -> list[dict]`
    - 使用 pgvector 餘弦相似度檢索，回傳 `text`、`source_file`、`chunk_index`、`score`
    - 結果數量不超過 `top_k` 且不超過實際 chunk 總數
    - 相似度分數低於閾值 0.3 或結果為空時，回傳空列表
    - _Requirements: 7.2, 8.5, 14.4, 15.5_

  - [ ]* 6.3 撰寫 Property 7 屬性測試：檢索數量上限
    - **Property 7: 任意 `top_k`（1 ≤ top_k ≤ 100），回傳結果數量 ≤ top_k**
    - 使用 mock 資料庫連線，`st.integers(min_value=1, max_value=100)`
    - **Validates: Requirements 7.2**

  - [x] 6.4 實作 `assemble_prompt(query: str, chunks: list[dict], history: list[dict]) -> list[dict]`
    - 組裝 LiteLLM messages 格式：system prompt（保健食品領域指令，含要求說明 Study_Population 的指令）、對話歷史（最近 3 輪）、context chunks、user query
    - _Requirements: 8.3, 14.3, 15.3_

  - [ ]* 6.5 撰寫 Property 9 屬性測試：對話歷史保留
    - **Property 9: 對話輪數 n ≥ 3 時，messages 應包含最近 3 輪問答記錄**
    - 使用 `st.integers(min_value=3, max_value=10)`
    - **Validates: Requirements 8.3**

  - [x] 6.5 實作 `format_answer(response: str, chunks: list[dict]) -> str`
    - 格式化回答，附加 citation 列表（來源檔案名稱 + 段落編號）
    - _Requirements: 7.4, 14.2, 15.2_

  - [ ]* 6.6 撰寫 Property 8 屬性測試：回答包含 Citation
    - **Property 8: 若 Vector Store 中存在相關 chunk，輸出應包含至少一筆 citation**
    - **Validates: Requirements 7.4, 14.2, 15.2**

- [x] 7. 實作 rag_query.py — 查詢模式與 LiteLLM 整合
  - [x] 7.1 實作 `run_query(query: str, top_k: int = 5, model: str = "huggingface/HuggingFaceH4/zephyr-7b-beta") -> str`
    - 依序執行：Query Embedding → Similarity Search → Prompt 組裝 → LiteLLM 呼叫
    - 無相關結果時回傳固定無結果訊息，不呼叫 LLM
    - LiteLLM 呼叫失敗時輸出錯誤訊息並提示使用者重試
    - 從 `.env` 讀取 `HF_TOKEN`，透過 `huggingface/<model-name>` 格式呼叫
    - _Requirements: 7.1, 7.3, 7.5, 9.1, 9.3, 9.4, 9.5_

  - [x] 7.2 實作 `run_interactive(top_k: int = 5, model: str = "huggingface/HuggingFaceH4/zephyr-7b-beta") -> None`
    - 持續接受使用者輸入並回應，維護最近 3 輪對話歷史
    - 輸入 `exit` 或 `quit` 時結束程式
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 7.3 實作 CLI 介面（argparse）
    - 支援 `--query "<問題>"`、`--top-k <數字>`（預設 5）、`--model <模型名稱>`（預設 `huggingface/HuggingFaceH4/zephyr-7b-beta`）
    - 無 `--query` 參數時進入互動式模式
    - _Requirements: 7.1, 7.2, 7.3, 8.1_

- [x] 8. Checkpoint — 確認 rag_query.py 完整可執行
  - 確保所有測試通過，ask the user if questions arise.

- [x] 9. 實作 skill_builder.py
  - [x] 9.1 定義 `DEFAULT_QUESTIONS` 與實作 `load_questions(path: str | None) -> list[str]`
    - 預設五個保健食品領域全域問題
    - 支援 `--questions <路徑>` 參數載入自訂問題清單檔案
    - _Requirements: 16.1, 16.2_

  - [x] 9.2 實作 `gather_knowledge(questions: list[str], model: str, top_k: int = 5) -> list[dict]`
    - 對每個問題呼叫 `run_query()`，收集問答對
    - _Requirements: 10.1, 16.3_

  - [x] 9.3 實作 `synthesize_skill_doc(qa_pairs: list[dict], model: str) -> str`
    - 透過 LiteLLM 將問答對整合為符合格式規範的 skill.md 內容
    - 包含所有必要章節：Metadata、Overview（≤200字）、Core Concepts（5-15個）、Key Trends（3-10個）、Key Entities、Methodology & Best Practices、Knowledge Gaps & Limitations、Example Q&A（3-5組）、Source References
    - Core Concepts 應包含至少 5 個保健食品領域核心概念
    - _Requirements: 10.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 16.3, 16.4_

  - [ ]* 9.4 撰寫 Property 10 屬性測試：Skill Document 格式完整性
    - **Property 10: 生成的 skill.md 應包含所有必要章節**
    - 使用 mock LLM，`st.lists(st.fixed_dictionaries(...))`
    - **Validates: Requirements 10.5, 11.1, 11.5, 11.6**

  - [ ]* 9.5 撰寫 Property 11 屬性測試：Skill Document 數量約束
    - **Property 11: Overview ≤200字、Core Concepts 5-15個、Key Trends 3-10個、Example Q&A 3-5組**
    - **Validates: Requirements 11.2, 11.3, 11.4, 11.7**

  - [x] 9.6 實作 `validate_skill_doc(content: str) -> bool` 與 `run_build()`
    - 驗證 skill.md 包含所有必要章節
    - 主流程：收集知識 → 整合 → 驗證 → 輸出至指定路徑
    - _Requirements: 10.2, 10.5_

  - [x] 9.7 實作 CLI 介面（argparse）
    - 支援 `--output <路徑>`（預設 `skill.md`）、`--model <模型名稱>`（預設 `huggingface/HuggingFaceH4/zephyr-7b-beta`）、`--questions <路徑>`
    - _Requirements: 10.2, 10.3, 16.2_

- [ ] 10. 建立測試套件
  - [ ]* 10.1 撰寫單元測試：環境變數讀取、預設模型名稱、`--rebuild` 旗標、退出指令、預設問題清單、LiteLLM 錯誤處理、無結果處理
    - _Requirements: 4.2, 9.4, 6.4, 8.4, 16.1, 9.5, 8.5_

  - [ ]* 10.2 撰寫整合測試：完整 RAG 流程（mock LLM）、Skill Builder 整合（mock LLM）、Study Population 指令驗證
    - _Requirements: 7.5, 10.1, 14.3_

  - [ ]* 10.3 撰寫 Smoke Tests：驗證 `.env.example`、`docker-compose.yml`、`requirements.txt`、`README.md` 存在且包含必要內容
    - _Requirements: 12.1, 12.2, 12.3, 13.1_

- [x] 11. 建立 README.md
  - 撰寫專案簡介（知識主題、資料來源、架構說明）
  - 以 Mermaid 語法繪製系統架構圖，呈現完整 RAG 流程
  - 包含完整環境建置與執行步驟：Docker 啟動、套件安裝、`.env` 設定、資料索引、問答查詢、技能文件生成
  - _Requirements: 13.1, 13.2, 13.3, 12.4_

- [x] 12. Final Checkpoint — 確認所有測試通過
  - 確保所有測試通過，ask the user if questions arise.

## Notes

- 標記 `*` 的子任務為選填，可跳過以加速 MVP 開發
- 每個任務均對應具體需求條款，確保可追溯性
- Checkpoint 任務確保增量驗證，避免問題累積
- 屬性測試（Property-Based Tests）使用 `hypothesis` 函式庫，驗證系統的普遍正確性
- 單元測試驗證具體範例與邊界條件
