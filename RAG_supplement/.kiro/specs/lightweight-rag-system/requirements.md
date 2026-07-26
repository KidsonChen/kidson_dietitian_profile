# Requirements Document

## Introduction

本系統為一套輕量化 RAG（Retrieval-Augmented Generation）系統，專注於**保健食品（Dietary Supplements / Nutraceuticals）**學術文獻知識庫，涵蓋完整的知識處理流程：資料收集 → 文字清理 → 分塊（Chunking）→ 向量嵌入（Embedding）→ 向量儲存（Vector Store）→ 相似度檢索（Retrieval）→ LLM 生成（Generation）。系統最終將知識濃縮為符合 Agent Skill 格式的 `skill.md` 技能文件，供 AI Agent 使用。

知識來源為使用者自行放置於 `data/raw/` 資料夾的學術論文 PDF 檔案，核心查詢用途包含：保健食品成分功效查詢（如 Omega-3、薑黃素、維生素 C 等）以及劑量建議查詢（如維生素 D 每日建議攝取量）。所有回答均需引用具體論文來源，確保資訊具備學術依據。

LLM 呼叫採用 HuggingFace Inference API 免費額度，透過 LiteLLM 統一介面存取，無需自架 LLM 服務即可運作。

系統由三個主要元件組成：
- `data_update.py`：資料收集、清理與向量索引
- `rag_query.py`：RAG 問答 CLI 介面
- `skill_builder.py`：技能文件自動生成

## Glossary

- **RAG_System**：本輕量化 Retrieval-Augmented Generation 系統的整體
- **Data_Updater**：`data_update.py` 腳本，負責資料收集、清理、分塊、嵌入與向量寫入
- **RAG_Query**：`rag_query.py` 腳本，負責接收使用者問題並透過 RAG 流程產生回答
- **Skill_Builder**：`skill_builder.py` 腳本，負責掃描知識庫並生成 `skill.md`
- **Vector_Store**：pgvector（PostgreSQL 擴充套件）向量資料庫，儲存 chunk 文字、向量與 metadata
- **Embedding_Model**：sentence-transformers 本地模型，將文字轉換為向量表示
- **LLM**：透過 LiteLLM 統一介面呼叫的大型語言模型（預設 gemini-2.5-flash）
- **Chunk**：文字分塊單位，包含文字內容、向量、來源 metadata
- **Skill_Document**：符合 Agent Skill 格式的 `skill.md` 輸出文件
- **Processed_File**：經清理後儲存於 `data/processed/` 的純文字檔
- **Raw_File**：儲存於 `data/raw/` 的原始來源資料檔案（本系統為學術論文 PDF）
- **File_Hash**：用於增量更新判斷的檔案內容雜湊值
- **LiteLLM**：統一 LLM 呼叫介面函式庫，本系統透過 LiteLLM 呼叫 HuggingFace Inference API
- **HF_Token**：HuggingFace 帳號的 API Token，用於存取 HuggingFace Inference API 免費額度
- **Supplement**：保健食品，指以補充特定營養素或生物活性物質為目的的食品或製劑
- **Active_Ingredient**：保健食品中具有生物活性的有效成分，如 Omega-3、薑黃素（Curcumin）、維生素 D 等
- **Dosage_Recommendation**：特定保健食品成分的建議攝取劑量範圍，通常以每日攝取量（mg 或 IU）表示
- **Efficacy**：保健食品成分經研究證實的生理功效或健康效益
- **Study_Population**：學術論文中研究所針對的受試族群，如成人、老年人、特定疾病患者等
- **Citation**：回答中引用的具體論文來源，包含論文標題、作者或來源檔案名稱與段落編號
- **Contraindication**：保健食品成分的禁忌症或與其他物質的交互作用警示

---

## Requirements

### Requirement 1：資料格式支援

**User Story:** As a 知識工程師, I want 系統能讀取多種格式的原始資料, so that 我可以使用不同來源的文件建立知識庫。

#### Acceptance Criteria

1. THE Data_Updater SHALL 支援讀取 `.md`、`.txt`、`.pdf` 三種格式的 Raw_File。
2. WHEN Data_Updater 讀取 `.pdf` 格式的 Raw_File，THE Data_Updater SHALL 將其文字內容提取並轉換為純文字。
3. WHEN Data_Updater 讀取 `.md` 或 `.txt` 格式的 Raw_File，THE Data_Updater SHALL 直接讀取其文字內容。
4. IF Data_Updater 遇到不支援格式的檔案，THEN THE Data_Updater SHALL 跳過該檔案並記錄警告訊息。

---

### Requirement 2：文字清理與 Processed File 生成

**User Story:** As a 知識工程師, I want 原始資料經過清理後儲存為標準化文字檔, so that 後續分塊與嵌入流程能獲得乾淨的輸入。

#### Acceptance Criteria

1. WHEN Data_Updater 處理 Raw_File，THE Data_Updater SHALL 移除 HTML 標籤、頁首頁尾標記與重複空白後，將結果儲存為 Processed_File。
2. THE Data_Updater SHALL 依照命名慣例將 `data/raw/<filename>.<ext>` 對應儲存為 `data/processed/<filename>.txt`。
3. WHEN Data_Updater 生成 Processed_File，THE Data_Updater SHALL 確保輸出檔案為 UTF-8 編碼的純文字格式。
4. FOR ALL Raw_File，Data_Updater 對同一 Raw_File 執行清理後再次執行清理，THE Data_Updater SHALL 產生與第一次相同內容的 Processed_File（冪等性）。

---

### Requirement 3：文字分塊（Chunking）

**User Story:** As a 知識工程師, I want 清理後的文字依固定長度加 overlap 策略切分為 Chunk, so that 向量嵌入能在合理粒度下進行。

#### Acceptance Criteria

1. THE Data_Updater SHALL 使用固定長度加 overlap 策略將 Processed_File 切分為多個 Chunk。
2. THE Data_Updater SHALL 允許透過設定參數指定 chunk 大小（字元數或 token 數）與 overlap 大小。
3. WHEN Data_Updater 生成 Chunk，THE Data_Updater SHALL 為每個 Chunk 附加來源檔案名稱與段落編號作為 metadata。
4. FOR ALL Processed_File，切分後所有 Chunk 的文字內容合集 SHALL 涵蓋原始 Processed_File 的完整文字（不遺漏任何內容）。

---

### Requirement 4：向量嵌入（Embedding）

**User Story:** As a 知識工程師, I want 每個 Chunk 透過本地 Embedding Model 轉換為向量, so that 系統不依賴外部嵌入 API 即可運作。

#### Acceptance Criteria

1. THE Data_Updater SHALL 使用 sentence-transformers 本地 Embedding_Model 將每個 Chunk 的文字轉換為向量。
2. THE Data_Updater SHALL 從 `.env` 環境變數 `EMBEDDING_MODEL` 讀取所使用的模型名稱。
3. WHEN Data_Updater 對同一 Chunk 文字執行嵌入兩次，THE Embedding_Model SHALL 產生相同的向量（確定性）。
4. IF Embedding_Model 載入失敗，THEN THE Data_Updater SHALL 輸出錯誤訊息並終止執行。

---

### Requirement 5：向量寫入 Vector Store

**User Story:** As a 知識工程師, I want Chunk 的文字、向量與 metadata 寫入 pgvector, so that 後續可進行相似度檢索。

#### Acceptance Criteria

1. THE Data_Updater SHALL 將每個 Chunk 的文字內容、向量與來源 metadata（檔案名稱、段落編號）寫入 Vector_Store。
2. THE Data_Updater SHALL 從 `.env` 環境變數 `PGVECTOR_CONNECTION_STRING` 讀取資料庫連線字串。
3. IF Vector_Store 連線失敗，THEN THE Data_Updater SHALL 輸出錯誤訊息並終止執行。
4. THE Data_Updater SHALL 在寫入前建立所需的資料表與 pgvector 擴充套件（若尚未存在）。

---

### Requirement 6：冪等性執行與增量更新

**User Story:** As a 知識工程師, I want 每次執行 data_update.py 後 Vector Store 精確反映 data/ 目錄的最新狀態, so that 不會因重複執行而累積重複資料。

#### Acceptance Criteria

1. THE Data_Updater SHALL 預設以增量模式執行，僅處理自上次執行後新增或修改的 Raw_File。
2. THE Data_Updater SHALL 使用 File_Hash 或檔案修改時間判斷 Raw_File 是否需要重新處理。
3. WHEN Data_Updater 以增量模式執行且 Raw_File 未變更，THE Data_Updater SHALL 跳過該檔案的清理、分塊、嵌入與寫入流程。
4. WHEN Data_Updater 以 `--rebuild` 旗標執行，THE Data_Updater SHALL 清除 Vector_Store 中所有現有資料後執行全量重建。
5. FOR ALL 執行情境，對相同的 `data/` 目錄內容執行 Data_Updater 兩次後，Vector_Store 中的資料 SHALL 與執行一次的結果相同（冪等性）。

---

### Requirement 7：RAG 問答 — 單次查詢模式

**User Story:** As a 使用者, I want 透過命令列單次查詢問題並獲得 LLM 回答, so that 我可以快速取得知識庫中的資訊。

#### Acceptance Criteria

1. WHEN 使用者執行 `python rag_query.py --query "<問題>"，THE RAG_Query SHALL 執行完整 RAG 流程並輸出回答。
2. THE RAG_Query SHALL 支援 `--top-k <數字>` 參數指定檢索的 Chunk 數量，預設值為 5。
3. THE RAG_Query SHALL 支援 `--model <模型名稱>` 參數指定 LLM，預設值為 `gemini-2.5-flash`。
4. WHEN RAG_Query 產生回答，THE RAG_Query SHALL 同時顯示引用的來源檔案名稱與段落編號。
5. WHEN RAG_Query 執行查詢，THE RAG_Query SHALL 依序執行：Query Embedding → Similarity Search → Prompt 組裝 → LiteLLM 呼叫。

---

### Requirement 8：RAG 問答 — 互動式多輪對話模式

**User Story:** As a 使用者, I want 透過互動式 CLI 進行多輪對話, so that 我可以在同一會話中持續追問並獲得上下文連貫的回答。

#### Acceptance Criteria

1. WHEN 使用者執行 `python rag_query.py`（不帶 `--query` 參數），THE RAG_Query SHALL 進入互動式對話模式。
2. WHILE RAG_Query 處於互動式模式，THE RAG_Query SHALL 持續接受使用者輸入並回應，直到使用者輸入退出指令。
3. THE RAG_Query SHALL 在對話歷史中保留至少最近 3 輪的問答記錄，並將其納入 LLM 的 messages 中。
4. WHEN 使用者在互動式模式中輸入退出指令（如 `exit` 或 `quit`），THE RAG_Query SHALL 結束程式。
5. IF Vector_Store 中無相關 Chunk，THEN THE RAG_Query SHALL 告知使用者無法找到相關資訊，而非產生無根據的回答。

---

### Requirement 9：LiteLLM 整合

**User Story:** As a 開發者, I want 所有 LLM 呼叫統一透過 LiteLLM 介面呼叫 HuggingFace Inference API, so that 可以輕易切換不同的 HuggingFace 模型。

#### Acceptance Criteria

1. THE RAG_Query SHALL 使用 LiteLLM 的 `completion()` 函式呼叫 LLM，傳入 `model`、`messages` 參數。
2. THE Skill_Builder SHALL 使用 LiteLLM 的 `completion()` 函式呼叫 LLM，傳入 `model`、`messages` 參數。
3. THE RAG_System SHALL 從 `.env` 環境變數 `HF_TOKEN` 讀取 HuggingFace API Token，並透過 LiteLLM 的 `huggingface/<model-name>` 格式呼叫模型。
4. THE RAG_System SHALL 預設使用 `huggingface/HuggingFaceH4/zephyr-7b-beta` 作為 LLM，並允許透過 `--model` 參數覆蓋。
5. IF LiteLLM 呼叫回傳錯誤，THEN THE RAG_Query SHALL 輸出錯誤訊息並提示使用者重試。

---

### Requirement 10：Skill Builder — 主題掃描與知識整合

**User Story:** As a AI Agent 開發者, I want 系統自動掃描知識庫並整合為 skill.md, so that Agent 可以直接使用濃縮後的知識。

#### Acceptance Criteria

1. WHEN 使用者執行 `python skill_builder.py`，THE Skill_Builder SHALL 向 RAG_System 提出多個預設全域問題以掃描知識庫主題。
2. THE Skill_Builder SHALL 支援 `--output <路徑>` 參數指定輸出檔案路徑，預設為 `skill.md`。
3. THE Skill_Builder SHALL 支援 `--model <模型名稱>` 參數指定 LLM，預設值為 `gemini-2.5-flash`。
4. THE Skill_Builder SHALL 透過 LLM 將多個問答結果整合為連貫的知識摘要。
5. WHEN Skill_Builder 完成生成，THE Skill_Builder SHALL 輸出符合 Skill_Document 格式規範的 `skill.md` 檔案。

---

### Requirement 11：Skill Document 格式規範

**User Story:** As a AI Agent 開發者, I want skill.md 包含標準化的章節結構, so that Agent 能以一致的方式解析與使用技能文件。

#### Acceptance Criteria

1. THE Skill_Builder SHALL 在 Skill_Document 中生成 Metadata 章節，包含：知識領域、資料來源數量、最後更新時間、適用 Agent 類型。
2. THE Skill_Builder SHALL 在 Skill_Document 中生成 Overview 章節，內容為 200 字以內的知識摘要。
3. THE Skill_Builder SHALL 在 Skill_Document 中生成 Core Concepts 章節，包含 5 至 15 個核心概念。
4. THE Skill_Builder SHALL 在 Skill_Document 中生成 Key Trends 章節，包含 3 至 10 個趨勢。
5. THE Skill_Builder SHALL 在 Skill_Document 中生成 Key Entities 章節，列出作者、機構、工具、框架等實體。
6. THE Skill_Builder SHALL 在 Skill_Document 中生成 Methodology & Best Practices、Knowledge Gaps & Limitations、Example Q&A（3 至 5 組）、Source References 章節。
7. FOR ALL 生成的 Skill_Document，Skill_Document 中的 Example Q&A 章節 SHALL 包含至少 3 組且不超過 5 組問答對。

---

### Requirement 12：環境設定與 Docker 支援

**User Story:** As a 開發者, I want 系統提供標準化的環境設定範本與 Docker Compose 設定, so that 可以快速重現完整的執行環境。

#### Acceptance Criteria

1. THE RAG_System SHALL 提供 `.env.example` 檔案，包含 `HF_TOKEN`、`EMBEDDING_PROVIDER`、`EMBEDDING_MODEL`、`PGVECTOR_CONNECTION_STRING` 四個環境變數範本。
2. THE RAG_System SHALL 提供 `docker-compose.yml` 檔案，用於啟動 pgvector 服務。
3. THE RAG_System SHALL 提供 `requirements.txt` 檔案，列出所有 Python 套件相依性。
4. WHEN 開發者依照 README.md 步驟執行，THE RAG_System SHALL 能在全新環境中完整重現所有功能。

---

### Requirement 13：README 文件

**User Story:** As a 開發者, I want 完整的 README.md 說明文件, so that 任何人都能理解系統架構並重現執行環境。

#### Acceptance Criteria

1. THE RAG_System SHALL 提供 `README.md`，包含專案簡介（知識主題、資料來源、架構說明）。
2. THE README.md SHALL 包含以 Mermaid 語法繪製的系統架構圖，呈現完整 RAG 流程。
3. THE README.md SHALL 包含完整的環境建置與執行步驟，涵蓋 Docker 啟動、套件安裝、資料索引、問答查詢與技能文件生成。

---

### Requirement 14：保健食品成分功效查詢

**User Story:** As a 使用者, I want 查詢特定保健食品成分的功效, so that 我可以根據學術文獻了解各成分對健康的具體效益。

#### Acceptance Criteria

1. WHEN 使用者提出包含特定 Active_Ingredient 名稱的功效查詢（如「魚油的 Omega-3 有什麼功效？」），THE RAG_Query SHALL 從 Vector_Store 中檢索與該成分功效相關的 Chunk 並生成回答。
2. WHEN RAG_Query 回答功效查詢，THE RAG_Query SHALL 在回答中包含至少一筆 Citation，標注來源論文的檔案名稱與段落編號。
3. WHEN RAG_Query 回答功效查詢，THE RAG_Query SHALL 明確說明功效所對應的 Study_Population（如成人、特定疾病患者），若文獻未指定則標注「未指定研究族群」。
4. IF Vector_Store 中無與查詢 Active_Ingredient 相關的 Chunk，THEN THE RAG_Query SHALL 告知使用者目前知識庫中無該成分的相關文獻，而非產生無根據的回答。
5. THE RAG_Query SHALL 支援以中文或英文名稱查詢 Active_Ingredient（如「薑黃素」與「Curcumin」應能檢索到相同的相關文獻）。

---

### Requirement 15：劑量建議查詢

**User Story:** As a 使用者, I want 查詢特定保健食品的建議劑量範圍, so that 我可以根據學術文獻了解安全且有效的攝取量。

#### Acceptance Criteria

1. WHEN 使用者提出包含特定 Supplement 或 Active_Ingredient 的劑量查詢（如「維生素 D 每日建議攝取量是多少？」），THE RAG_Query SHALL 從 Vector_Store 中檢索與該成分劑量相關的 Chunk 並生成回答。
2. WHEN RAG_Query 回答劑量查詢，THE RAG_Query SHALL 在回答中標注 Dosage_Recommendation 的來源 Citation（檔案名稱與段落編號）。
3. WHEN RAG_Query 回答劑量查詢，THE RAG_Query SHALL 標注該劑量建議所對應的 Study_Population（如成人、老年人、特定疾病患者）。
4. WHEN 文獻中存在針對不同 Study_Population 的多個 Dosage_Recommendation，THE RAG_Query SHALL 分別列出各族群的建議劑量並標注對應 Citation。
5. IF Vector_Store 中無與查詢成分相關的劑量資訊，THEN THE RAG_Query SHALL 告知使用者目前知識庫中無該成分的劑量建議資料，而非產生無根據的回答。

---

### Requirement 16：保健食品領域的 Skill Builder 全域問題

**User Story:** As a AI Agent 開發者, I want skill_builder.py 預設使用針對保健食品領域設計的全域問題, so that 生成的 skill.md 能精準涵蓋保健食品知識庫的核心內容。

#### Acceptance Criteria

1. THE Skill_Builder SHALL 預設使用以下五個針對保健食品領域的全域問題掃描知識庫：
   - 「這個知識庫涵蓋哪些保健食品成分？」
   - 「各成分的主要功效與適用族群為何？」
   - 「文獻中最常見的劑量建議範圍為何？」
   - 「有哪些成分具有交互作用或禁忌症的研究？」
   - 「目前研究最充分的保健食品成分有哪些？」
2. THE Skill_Builder SHALL 支援 `--questions <路徑>` 參數，允許使用者提供自訂問題清單檔案以覆蓋預設全域問題。
3. WHEN Skill_Builder 使用保健食品全域問題掃描知識庫，THE Skill_Builder SHALL 將各問題的 RAG 回答結果整合為涵蓋 Supplement、Active_Ingredient、Efficacy、Dosage_Recommendation 與 Contraindication 的 Skill_Document。
4. WHEN Skill_Builder 生成 Skill_Document，THE Skill_Document 的 Core Concepts 章節 SHALL 包含至少 5 個保健食品領域的核心概念（如具體的 Active_Ingredient 名稱或功效類別）。
