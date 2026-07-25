# 月結單處理系統

自動化解決方案，用於讀取PDF格式月結單，生成結構化Markdown報告，存儲到資料庫，並提供統計分析功能。

## ✨ 功能特性

- 📄 **PDF讀取**: 自動識別和提取月結單中的數據
- 📝 **Markdown生成**: 生成格式規範的Markdown報告
- 💾 **數據存儲**: 將數據持久化存儲到資料庫
- 📊 **統計分析**: 提供多維度的數據分析和可視化
- 🔄 **月份整合**: 按月份整合所有月結單和消費記錄
- 🔄 **自動化工作流**: 一鍵處理整個流程

## 🚀 快速開始

### 系統要求
- Python 3.8+
- pip 或 conda

### 安裝步驟

1. **克隆或下載項目**
```bash
cd report_RAG
```

2. **創建虛擬環境（推薦）**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **安裝依賴**
```bash
pip install -r requirements.txt
```

4. **初始化數據庫**
```bash
python -m src.main --init-db
```

## 📋 使用方法

### 1. 準備PDF檔案
將月結單PDF放入 `raw_data/` 文件夾

### 2. 處理PDF文件

#### 處理單個PDF文件
```bash
python -m src.main --file raw_data/您的月結單.pdf
```

#### 批量處理整個目錄
```bash
python -m src.main --batch
```

#### 指定銀行名稱
```bash
python -m src.main --file raw_data/statement.pdf --bank "中國信託"
```

### 3. 生成月份總結報告

#### 生成全部銀行的月份總結
```bash
python -m src.main --report 2024-04
```

#### 生成特定銀行的月份總結
```bash
python -m src.main --report 2024-04:中國信託
```

### 4. 數據庫管理

#### 初始化數據庫
```bash
python -m src.main --init-db
```

#### 重置數據庫（刪除所有數據）
```bash
python -m src.main --reset-db
```

### 5. 查看結果

- **Markdown報告**: `md/` 文件夾
  - 單個文件報告: `md/文件名.md`
  - 月份總結報告: `md/monthly_YYYY-MM/`
- **數據庫**: `database/report_rag.db`
- **日誌**: `logs/` 文件夾

## 🛠️ 開發與測試工具

### 測試腳本

#### 創建測試PDF文件
```bash
python create_test_pdf.py
```
創建測試用的PDF月結單文件，用於開發和測試。

#### 檢查PDF文件內容
```bash
python inspect_pdf.py
```
檢查PDF文件的頁數、文本內容和表格結構。

#### 測試PDF處理功能
```bash
python test_pdf_processing.py
```
測試PDF處理器的完整功能，包括文本提取和表格解析。

#### 測試表格提取
```bash
python test_table_extraction.py
```
專門測試PDF中的表格數據提取功能。

#### 模擬PDF處理測試
```bash
python simulate_pdf_test.py
```
模擬PDF處理邏輯，用於快速測試數據清理和處理流程。

### 數據庫工具

#### 初始化數據庫
```bash
python database/init_db.py
```
手動初始化數據庫表結構。

### 測試運行

#### 運行所有測試
```bash
pytest
```

#### 運行特定測試文件
```bash
pytest tests/test_main.py
pytest tests/test_pdf_processor.py
pytest tests/test_data_processor.py
```

#### 運行帶覆蓋率的測試
```bash
pytest --cov=src --cov-report=html
```

## 📁 項目結構

```
report_RAG/
├── src/                    # 源代碼
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── main.py            # 主程序入口
│   ├── pdf_processor.py   # PDF處理器
│   ├── data_processor.py  # 數據處理器
│   ├── db_manager.py      # 數據庫管理器
│   ├── markdown_generator.py # Markdown生成器
│   ├── statistics.py      # 統計分析
│   └── utils.py           # 工具函數
├── tests/                 # 測試文件
│   ├── test_config.py
│   ├── test_main.py
│   ├── test_pdf_processor.py
│   ├── test_data_processor.py
│   ├── test_db_manager.py
│   ├── test_markdown_generator.py
│   ├── test_statistics.py
│   └── test_utils.py
├── database/              # 數據庫相關
│   ├── init_db.py        # 數據庫初始化
│   └── schema.sql        # 數據庫結構
├── raw_data/             # 原始PDF文件
│   ├── account/          # 帳戶月結單
│   └── credit card/      # 信用卡月結單
├── md/                   # 生成的Markdown報告
├── report/               # 統計報告
├── logs/                 # 日誌文件
├── create_test_pdf.py    # 創建測試PDF
├── inspect_pdf.py        # 檢查PDF內容
├── test_pdf_processing.py # 測試PDF處理
├── test_table_extraction.py # 測試表格提取
├── simulate_pdf_test.py  # 模擬測試
├── requirements.txt      # Python依賴
├── pytest.ini           # pytest配置
└── README.md            # 項目文檔
```

## 🔧 配置

系統配置通過 `config.json` 文件管理。主要配置項包括：

- 數據庫路徑
- 日誌級別
- 輸出目錄
- PDF處理參數

## 📊 數據格式

### 帳戶月結單格式
- 日期格式: YYYY-MM-DD
- 金額格式: 正數表示收入，負數表示支出
- 類別: 自動識別或手動指定

### 信用卡月結單格式
- 交易日期和入帳日期
- 消費金額（正數）
- 交易項目描述

## 🤝 貢獻

1. Fork 此項目
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📝 許可證

此項目採用 MIT 許可證 - 查看 [LICENSE](LICENSE) 文件了解詳情。

## 🆘 故障排除

### 常見問題

1. **PDF處理失敗**
   - 檢查PDF文件是否損壞
   - 確認PDF格式是否受支持

2. **數據庫連接錯誤**
   - 確保數據庫文件路徑正確
   - 檢查文件權限

3. **依賴安裝失敗**
   - 使用虛擬環境
   - 更新pip: `pip install --upgrade pip`

### 日誌查看

所有操作都會記錄到 `logs/` 文件夾中。查看最新日誌：
```bash
tail -f logs/app.log
```

## 📁 項目結構

```
report_RAG/
├── raw_data/              # 原始PDF檔案
├── md/                    # 生成的Markdown報告
│   ├── monthly_YYYY-MM/   # 月份總結報告
│   └── *.md              # 單個文件報告
├── database/              # 數據庫文件
├── logs/                  # 日誌文件
├── tests/                 # 測試文件
├── src/                   # 源代碼
│   ├── main.py           # 主程序入口
│   ├── config.py         # 配置管理
│   ├── utils.py          # 工具函數
│   ├── pdf_processor.py  # PDF處理
│   ├── data_processor.py # 數據處理
│   ├── markdown_generator.py # Markdown生成
│   ├── db_manager.py     # 數據庫管理
│   └── __init__.py
├── requirements.txt      # Python依賴
├── config.json          # 配置文件
├── README.md            # 本文檔
└── .gitignore          # Git忽略規則
```

## ⚙️ 配置說明

編輯 `config.json` 調整系統設置：

```json
{
  "app_name": "月結單處理系統",
  "app_version": "1.0.0",
  "database_path": "database/report_rag.db",
  "raw_data_dir": "raw_data",
  "markdown_dir": "md",
  "banks": ["中國信託", "玉山銀行", "國泰世華"]
}
```

## 🔧 主要模組說明

| 模組 | 功能 |
|------|------|
| `main.py` | 主程序入口，命令行參數處理 |
| `pdf_processor.py` | PDF讀取、表格識別、數據提取 |
| `data_processor.py` | 數據驗證、清理、轉換 |
| `markdown_generator.py` | 生成Markdown格式報告 |
| `db_manager.py` | 數據庫操作（CRUD） |
| `config.py` | 配置管理 |
| `utils.py` | 日誌、格式化等工具函數 |

## 📊 數據庫架構

### monthly_reports - 月結單主表
```sql
- id (INTEGER PRIMARY KEY)
- file_name (TEXT) - PDF文件名
- bank_name (TEXT) - 銀行名稱
- report_date (TEXT) - 報表日期
- total_amount (REAL) - 總金額
- currency (TEXT) - 貨幣單位
- item_count (INTEGER) - 項目數量
- md_file_path (TEXT) - Markdown文件路徑
- created_at (TEXT)
- updated_at (TEXT)
- is_deleted (INTEGER)
```

### report_items - 明細項目表
```sql
- id (INTEGER PRIMARY KEY)
- report_id (INTEGER) - 月結單ID
- item_name (TEXT) - 項目名稱
- item_date (TEXT) - 項目日期
- amount (REAL) - 金額
- category (TEXT) - 類別
- description (TEXT) - 描述
- is_valid (INTEGER)
```

## 🧪 測試

運行測試套件：
```bash
pytest
```

## 📈 月份總結報告內容

月份總結報告包含以下內容：

- **基本統計**: 月結單數量、消費項目數量、總金額
- **月結單列表**: 該月所有處理過的月結單摘要
- **消費項目明細**: 按日期排序的所有消費項目
- **類別統計**: 按消費類別的統計和占比
- **備註**: 數據來源和生成時間

## 💡 使用場景

1. **個人財務管理**: 整合多張信用卡月結單，分析消費習慣
2. **企業報銷管理**: 批量處理員工消費記錄，生成總結報告
3. **財務分析**: 按月份統計各類別消費占比，制定預算計劃

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 許可證

本項目採用 MIT 許可證。
├── database/              # 數據庫文件
├── logs/                  # 日誌文件
├── tests/                 # 測試文件
│   ├── test_config.py
│   ├── test_utils.py
│   ├── test_db_manager.py
│   ├── test_pdf_processor.py
│   ├── test_data_processor.py
│   ├── test_markdown_generator.py
│   ├── test_statistics.py
│   ├── test_main.py
│   └── pytest.ini
├── src/                   # 源代碼
│   ├── main.py
│   ├── config.py
│   ├── utils.py
│   ├── pdf_processor.py
│   ├── data_processor.py
│   ├── markdown_generator.py
│   ├── db_manager.py
│   ├── statistics.py
│   └── __init__.py
├── requirements.md        # 需求規格書
├── PROJECT_STRUCTURE.md   # 項目結構詳細說明
├── README.md             # 本文檔
├── requirements.txt      # Python依賴
├── config.json           # 配置文件
├── .env.example          # 環境變量模板
├── .gitignore           # Git忽略規則
└── pytest.ini           # 測試配置
```

詳見 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## ⚙️ 配置說明

編輯 `config.json` 調整系統設置：

```json
{
  "database": {
    "type": "sqlite"  // 或 postgresql/mysql
  },
  "pdf_processing": {
    "extract_tables": true,
    "ocr_enabled": false
  }
}
```

## 💡 常見用途

### 用途1: 單次處理
```bash
python -m src.main --file raw_data/202404.pdf
```

### 用途2: 批量處理
```bash
python -m src.main --batch
```

### 用途3: 生成月度報告
```bash
python -m src.main --report monthly
```

### 用途4: 生成年度統計
```bash
python -m src.main --report yearly
```

## 🔧 主要模組說明

| 模組 | 功能 |
|------|------|
| `pdf_processor.py` | PDF讀取、表格識別、數據提取 |
| `data_processor.py` | 數據驗證、清理、轉換 |
| `markdown_generator.py` | 生成Markdown格式報告 |
| `db_manager.py` | 數據庫操作（CRUD） |
| `statistics.py` | 統計分析、圖表生成 |
| `config.py` | 配置管理 |

## 📊 數據庫架構

核心表結構：

**monthly_reports** - 月結單主表
```sql
- id (PRIMARY KEY)
- file_name (VARCHAR)
- report_date (DATE)
- total_amount (DECIMAL)
- currency (VARCHAR)
- created_at (TIMESTAMP)
```

**report_items** - 明細項目表
```sql
- id (PRIMARY KEY)
- report_id (FOREIGN KEY)
- item_name (VARCHAR)
- amount (DECIMAL)
- category (VARCHAR)
```

詳見 `database/schema.sql`

## 📈 統計功能

- ✅ 月份合計統計
- ✅ 類別分析
- ✅ 趨勢分析
- ✅ 月度/年度對比
- ✅ 數據導出 (CSV/JSON/PDF)

## 🔐 安全性

- 數據備份建議: 每週備份 `database/` 和 `report/` 文件夾
- 敏感信息: 使用額外的 `.env` 文件存儲密鑰
- 數據驗證: 所有輸入都經過驗證

## 📝 日誌

程序日誌存儲在 `logs/app.log`，可在 `config.json` 中調整日誌級別。

## 🐛 故障排查

### PDF無法識別
1. 確保PDF格式標準
2. 檢查 `pdf_processing.ocr_enabled` 是否需要啟用
3. 查看日誌文件了解錯誤詳情

### 數據不一致
1. 檢查PDF原始數據
2. 驗證 `data_processor.py` 的清理規則
3. 查看數據庫驗證日誌

### 性能問題
1. 啟用數據庫索引
2. 調整 `max_file_size_mb` 限制
3. 使用批量處理命令

## 📚 詳細文檔

- [需求規格書](requirements.md) - 完整的功能和非功能需求
- [項目結構](PROJECT_STRUCTURE.md) - 詳細的目錄和模組說明
- [API文檔](docs/API.md) - （待補充）
- [開發指南](docs/DEVELOPMENT.md) - （待補充）

## 🤝 貢獻指南

1. Fork 本項目
2. 創建特性分支
3. 提交更改
4. 發起Pull Request

## 📄 許可證

MIT License - 詳見 LICENSE 文件

## 📧 聯絡與支持

如有問題或建議，請提出Issue或聯繫項目維護者。

---

**最後更新**: 2026年4月
**版本**: 1.0.0
