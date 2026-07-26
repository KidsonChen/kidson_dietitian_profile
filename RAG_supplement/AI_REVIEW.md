# HW3 AI 評分回饋

> 本份回饋由 **Anthropic Claude Opus 4.7** 與 **OpenAI GPT-5.5** 兩個獨立模型，分別針對 Phase 1 與 Phase 2 程式碼與文件進行評分；最終加權分數為兩模型平均後，進行全班性的 Normalize，以及老師加分。

---

## 本次公布的兩個分數

本次 HW3 作業，每位同學會公布**兩個分數**，計算方式為下列三個候選值中**最高的兩個**：

| 候選 | 來源 | 計算 | 值 |
|---|---|---|---:|
| A | Max(Phase 1 兩模型評分) | max(Opus 85.0, GPT 89.5) | 89.50 |
| B | Max(Phase 2 兩模型評分) | max(Opus 46.6, GPT 42.3) | 46.56 |
| C | 最終加權分數 | 詳見下方加權計算 | 70.56 |

### 你的兩個分數

### **89.50**　／　**70.56**

_（A：Max(Phase 1 兩模型評分) = 89.50；C：最終加權分數 = 70.56）_

## 最終加權分數（候選 C）的計算

| 來源 | Phase 1 (40%) | Phase 2 (60%) | 加權平均 |
|---|---:|---:|---:|
| Anthropic Claude Opus 4.7 | 85.0 | 46.6 | 61.94 |
| OpenAI GPT-5.5 | 89.5 | 42.3 | 61.19 |
| **兩模型平均** | **87.2** | **44.4** | **61.56** |
| 老師加分 (professor_bonus) | | | +9 |
| **最終分數** | | | **70.56** |

## 計算公式

```
Phase 1 平均  = (Opus_P1 + GPT_P1) / 2
Phase 2 平均  = (Opus_P2 + GPT_P2) / 2
加權平均      = 0.4 × Phase 1 平均 + 0.6 × Phase 2 平均
Normalize 後  = 依全班分布做校準
最終分數      = min(100, Normalize 後 + 老師加分)
```

## 專案基本資料

- **github_id**：`KidsonChen`
- **領域**（Haiku 抽取）：`dietary_supplements_nutraceuticals`
- **領域分類**（taxonomy）：`biomedical_health_domain`
- **Phase 1 CI**：✓ 通過
- **Phase 2 CI**：✗ 未通過

## Phase 1 分項評語（40% 權重）

| 面向 | Opus 分數 | Opus 評語 | GPT 分數 | GPT 評語 |
|---|---:|---|---:|---|
| 資料收集 | 78 | data/raw 含 18 份 PDF 加 1 份 md，數量達到合格門檻並超過 baseline，README 詳列涵蓋成分（鈣鎂鋅、Omega-3、薑黃素等）。格式以 PDF 為主僅 1 份 md，多樣性偏弱；亦未提供來源授權聲明（license 缺失），扣分主因為合規說明不足。 | 82 | data/raw 有 19 份，含 18 PDF 與 1 MD，達 Phase 1 合格且格式多元；README 清楚描述保健食品成分範圍，但缺逐篇來源、版本與授權合規說明。 |
| RAG 系統完整度 | 85 | data_update.py (484 行) 完整實作 PDF 解析（pdfplumber+PyPDF2 fallback）、清洗、512/64 chunking、sentence-transformers embedding 與 pgvector 寫入；rag_query.py (378 行) 提供 embed_query 快取、cosine similarity top-k=5 加 0.3 門檻、LiteLLM 整合與 citation 格式（[來源: 檔名, 段落 N]）。系統 prompt 針對保健食品領域設計，多輪互動完整，整體流程串接清晰。 | 90 | data_update.py 具 PDF/MD/TXT 讀取、清理、512/64 chunking、sentence-transformers embedding 與 pgvector 寫入；rag_query.py 有 top-k 檢索、來源引用與 LiteLLM 整合。 |
| 冪等性 | 92 | 明確支援 --rebuild 旗標強制全量重建，並以 SHA-256 file hash 加 processed_files 表追蹤，僅重新處理 hash 變更檔案，跳過未變更檔，README 第 5 節明確說明冪等性設計。增量機制完整，達到 high anchor 水準。 | 96 | README 與程式支援 data_update.py --rebuild；並以 SHA-256 hash 搭配 processed_files 表追蹤新增或修改檔案，可避免重複嵌入並支援增量更新。 |

## Phase 2 分項評語（60% 權重）

| 面向 | Opus 分數 | Opus 評語 | GPT 分數 | GPT 評語 |
|---|---:|---|---:|---|
| 資料收集深度 | 62 | data/raw 共 25 份（23 PDF + 2 MD），剛達標但未明顯超出。涵蓋 Calcium、Omega-3、Curcumin 等多種保健食品成分，主題聚焦清楚。但 README §1 僅描述主題，未提供論文清單表格、arXiv ID 或授權聲明，license_compliance 缺失，與 phase2_high_anchor 要求的「列出指引/論文版本與授權」有落差。 | 58 | data/raw Phase 2 有25份，達≥20門檻；但README §資料來源仍寫18篇且僅概列成分，授權/來源條款缺失，來源型態以PDF論文為主，混搭不足。 |
| skill.md 品質 | 5 | skill.md 為空檔（0 chars），所有必要章節 Overview / Core Concepts / Source References 全部缺失，scanner 標示三項 required sections missing。雖 skill_builder.py 內含完整模板與 prompt 設計，但實際未產出文件，等同未交付 Phase 2 最重要的成果。Phase 2 重點面向幾乎零分。 | 0 | skill.md 內容為空，缺 Overview/Core Concepts/Key Trends/Key Entities/Methodology/Knowledge Gaps/Example Q&A/Source References 全部必要章節。 |
| README 設計決策 | 78 | README §5 對 pgvector、sentence-transformers、LiteLLM、chunking（512+64 overlap）、SHA-256 增量更新均有具體取捨理由，§2 含 mermaid 架構圖，§4 環境變數表清楚。回答了 chunking / embedding / vector db / retrieval / idempotency 等大多數設計題，但缺 prompt 工程與 skill_builder 全域問題設計的取捨論述，且 Phase 2 CI 未通過。 | 76 | README §5 對 pgvector、embedding、LLM、chunking、增量更新有具體理由；但 retrieval score、prompt、防幻覺與 skill_builder 全域問題取捨較少，且資料數量未同步。 |
| skill_builder 品質 | 60 | skill_builder.py §DEFAULT_QUESTIONS 設計 5 題涵蓋成分、功效、劑量、交互作用、研究充分度，多元性合理，並透過 gather_knowledge → synthesize_skill_doc 流程整合多次 RAG 結果而非機械拼貼，prompt 模板章節完整。但 phase2_ci_pass=false 且最終未實際生成 skill.md，無法驗證整合品質，有結構無產物。 | 55 | skill_builder.py 有5個全域問題，涵蓋成分、功效、劑量、禁忌與研究充分度，並用RAG結果再合成；但未產出skill.md、Phase 2 CI失敗，依賴外部API且無離線備案。 |

## 整體評語

### 亮點

- 完整的增量更新機制確保冪等性與效率
- 詳細的設計決策說明（pgvector、sentence-transformers、LiteLLM 選型理由）
- 支援中英文多語言嵌入與查詢
- Docker Compose 一鍵部署，降低環境配置複雜度
- 互動式多輪問答與對話歷史維護

### 改進建議

- skill.md 為空檔，未實際生成領域知識文件
- Phase 2 CI 測試失敗，code quality 未驗證
- 缺乏 Python 版本宣告（requirements.txt 未指定 python_requires）
- 無明確的資料來源授權說明或 license 合規聲明
- skill_builder.py 依賴外部 LLM API，無離線備案

---

_本份評分回饋由自動化評分管線（Anthropic + OpenAI 雙模型獨立評分 → 平均 → rescale → 老師加分）產出，僅作為個人學習參考。若對評分有疑問請於課堂或 office hour 提出。_
