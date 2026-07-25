# 月結單處理系統 - 項目結構

## 📁 目錄說明

```
report_RAG/
│
├── raw_data/              # 📄 原始PDF月結單存放區
│   ├── 202401_statement.pdf
│   ├── 202402_statement.pdf
│   └── ...
│
├── md/                    # 📝 生成的Markdown檔存放區
│   ├── bank_a/            # 銀行A月結單
│   │   ├── 202401_report.md
│   │   ├── 202402_report.md
│   │   └── ...
│   ├── bank_b/            # 銀行B月結單
│   │   ├── 202401_report.md
│   │   ├── 202402_report.md
│   │   └── ...
│   ├── bank_c/            # 銀行C月結單
│   │   ├── 202401_report.md
│   │   ├── 202402_report.md
│   │   └── ...
│   └── ...
│
├── report/                # 📊 統計報告存放區
│   ├── monthly_summary.md
│   ├── yearly_report.md
│   ├── statistics.csv
│   ├── charts/
│   │   ├── monthly_trend.png
│   │   ├── category_distribution.png
│   │   └── ...
│   └── ...
│
├── database/              # 💾 數據庫存放區
│   ├── report_rag.db      # SQLite 數據庫（或數據庫配置）
│   └── schema.sql         # 數據库Schema定義
│
├── src/                   # 💻 源代碼目錄
│   ├── __init__.py
│   ├── main.py            # 主程序入口
│   ├── pdf_processor.py    # PDF讀取和提取模組
│   ├── data_processor.py   # 數據處理和驗證
│   ├── markdown_generator.py # Markdown生成
│   ├── db_manager.py       # 數據庫操作
│   ├── statistics.py       # 統計分析模組
│   ├── config.py           # 配置文件
│   └── utils.py            # 工具函數
│
├── requirements.md        # 📋 項目需求規格書
├── PROJECT_STRUCTURE.md   # 📁 本文檔 - 項目結構說明
├── README.md              # 📖 項目說明和使用指南
├── requirements.txt       # 🐍 Python依賴包
├── config.json            # ⚙️ 配置文件
└── .gitignore            # 🚫 Git忽略文件列表
```

---

## 📂 各文件夾詳細說明

### `/raw_data`
- **用途**: 存放原始的PDF月結單檔案
- **說明**: 系統會自動監控此文件夾，讀取PDF文件進行處理
- **文件命名建議**: `YYYYMM_statement.pdf` 或 `statement_201_YYYYMMDD.pdf`

### `/md`
- **用途**: 存放自動生成的Markdown格式月結單報告
- **說明**: 每次處理PDF後，系統會在此目錄生成對應的MD檔
- **文件結構**: 按銀行分類存放，每個.md包含月結單的所有關鍵信息
- **子目錄結構**:
  - `bank_a/` - A銀行月結單 (例: 台灣銀行、玉山銀行等)
  - `bank_b/` - B銀行月結單
  - `bank_c/` - C銀行月結單
  - 根據實際銀行名稱自定義子目錄名
- **命名規則**: 
  - 子目錄: 使用銀行英文縮寫或統一代碼 (如 `taibank/`, `ebank/`, `cathay/`)
  - 文件: `YYYYMM_statement.md` 或 `YYYYMMDD_report.md`
  - 例: `taibank/202404_statement.md`, `ebank/202404_statement.md`

### `/report`
- **用途**: 存放統計分析報告與可視化圖表
- **子文件夾**:
  - `charts/` - 圖表文件（PNG、SVG等）
  - `exports/` - 導出文件（CSV、JSON、PDF等）
- **包含內容**:
  - 月度/年度對比報告
  - 支出類別分析
  - 趨勢分析
  - 數據統計表

### `/database`
- **用途**: 數據庫配置與初始化
- **文件**:
  - `report_rag.db` - SQLite數據庫文件（或連接配置）
  - `schema.sql` - 數據庫表結構定義

### `/src`
- **用途**: 所有源代碼和業務邏輯
- **主要模組**:
  - `main.py` - 程序入口，協調各模組
  - `pdf_processor.py` - PDF文件讀取和數據提取
  - `data_processor.py` - 數據驗證、清理、轉換
  - `markdown_generator.py` - 生成Markdown文檔
  - `db_manager.py` - 數據庫設計和操作
  - `statistics.py` - 數據統計和分析
  - `config.py` - 全局配置管理
  - `utils.py` - 通用工具函數

---

## 🔄 數據流向

```
raw_data/*.pdf
    ↓
[pdf_processor.py] 
    ↓ 提取數據
[data_processor.py]
    ↓ 驗證清理
    ├→ md/*.md (生成Markdown)
    ├→ database/*.db (存儲數據)
    │
[statistics.py]
    ↓ 統計分析
report/* (輸出報告和圖表)
```

---

## 📝 使用工作流

### 1️⃣ 準備數據
- 將PDF月結單放入 `/raw_data` 文件夾

### 2️⃣ 運行處理
```bash
python src/main.py
```

### 3️⃣ 查看結果
- Markdown報告: `/md` 文件夾
- 統計報告: `/report` 文件夾
- 數據庫: `/database` 文件夾

### 4️⃣ 分析數據
- 查看統計報告
- 查看圖表
- 導出數據

---

## 🔧 配置文件位置

- **全局配置**: `config.json`
- **Python配置**: `src/config.py`
- **數據庫Schema**: `database/schema.sql`

---

## 📦 依賴管理

所有Python依賴包列在 `requirements.txt`，安裝命令：
```bash
pip install -r requirements.txt
```

---

## 🚀 項目啟動流程

1. ✅ 創建虛擬環境（可選）
2. ✅ 安裝依賴: `pip install -r requirements.txt`
3. ✅ 初始化數據庫: `python src/main.py --init-db`
4. ✅ 放入PDF到 `/raw_data`
5. ✅ 運行主程序: `python src/main.py`
6. ✅ 查看 `/md` 和 `/report` 的輸出

---

## 💡 注意事項

- ❌ 不要直接修改 `/database` 中的數據庫文件
- ✅ 定期備份 `/database` 和 `/report` 文件夾
- ✅ 使用 `.gitignore` 排除大文件和臨時文件
- ✅ 保持 `/raw_data` 的PDF文件有組織（按月份命名）

