-- 月結單處理系統 - 數據庫 Schema
-- SQLite 數據庫表結構定義

-- ================================
-- 1. 月結單主表
-- ================================
CREATE TABLE IF NOT EXISTS monthly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name VARCHAR(255) NOT NULL UNIQUE COMMENT '原始PDF檔案名',
    bank_name VARCHAR(100) NOT NULL COMMENT '銀行名稱',
    report_date DATE NOT NULL COMMENT '月結單月份 (YYYY-MM-01)',
    total_amount DECIMAL(15, 2) NOT NULL COMMENT '總金額',
    currency VARCHAR(10) DEFAULT 'TWD' COMMENT '幣種',
    item_count INTEGER DEFAULT 0 COMMENT '項目數量',
    validation_status VARCHAR(20) DEFAULT 'pending' COMMENT '驗證狀態: pending/valid/invalid',
    validation_message TEXT COMMENT '驗證說明',
    md_file_path VARCHAR(255) COMMENT 'Markdown 檔案路徑',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '創建時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新時間',
    is_deleted INTEGER DEFAULT 0 COMMENT '軟刪除標記'
);

-- 索引: 加速查詢
CREATE INDEX IF NOT EXISTS idx_reports_bank_date ON monthly_reports(bank_name, report_date);
CREATE INDEX IF NOT EXISTS idx_reports_status ON monthly_reports(validation_status);
CREATE INDEX IF NOT EXISTS idx_reports_created ON monthly_reports(created_at);

-- ================================
-- 2. 項目明細表
-- ================================
CREATE TABLE IF NOT EXISTS report_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL COMMENT '月結單 ID (外鍵)',
    item_name VARCHAR(255) NOT NULL COMMENT '項目名稱',
    item_date DATE COMMENT '項目日期',
    amount DECIMAL(15, 2) NOT NULL COMMENT '項目金額',
    category VARCHAR(100) COMMENT '項目類別 (例: 食品、交通、娛樂)',
    description TEXT COMMENT '項目描述',
    is_valid INTEGER DEFAULT 1 COMMENT '數據有效性標記',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '創建時間',
    FOREIGN KEY (report_id) REFERENCES monthly_reports(id) ON DELETE CASCADE
);

-- 索引: 加速查詢
CREATE INDEX IF NOT EXISTS idx_items_report_id ON report_items(report_id);
CREATE INDEX IF NOT EXISTS idx_items_category ON report_items(category);
CREATE INDEX IF NOT EXISTS idx_items_date ON report_items(item_date);

-- ================================
-- 3. 統計表
-- ================================
CREATE TABLE IF NOT EXISTS statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name VARCHAR(100) NOT NULL COMMENT '銀行名稱',
    year_month VARCHAR(7) NOT NULL COMMENT '年月 (YYYY-MM)',
    total_income DECIMAL(15, 2) DEFAULT 0 COMMENT '總收入',
    total_expense DECIMAL(15, 2) DEFAULT 0 COMMENT '總支出',
    balance DECIMAL(15, 2) DEFAULT 0 COMMENT '結余 (收入 - 支出)',
    item_count INTEGER DEFAULT 0 COMMENT '項目數量',
    category_count INTEGER DEFAULT 0 COMMENT '類別數量',
    avg_amount DECIMAL(15, 2) DEFAULT 0 COMMENT '平均金額',
    max_amount DECIMAL(15, 2) DEFAULT 0 COMMENT '最大金額',
    min_amount DECIMAL(15, 2) DEFAULT 0 COMMENT '最小金額',
    statistics_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '統計生成日期',
    UNIQUE(bank_name, year_month)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_stats_bank_month ON statistics(bank_name, year_month);
CREATE INDEX IF NOT EXISTS idx_stats_date ON statistics(statistics_date);

-- ================================
-- 4. 類別統計表
-- ================================
CREATE TABLE IF NOT EXISTS category_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name VARCHAR(100) NOT NULL COMMENT '銀行名稱',
    year_month VARCHAR(7) NOT NULL COMMENT '年月 (YYYY-MM)',
    category VARCHAR(100) NOT NULL COMMENT '項目類別',
    total_amount DECIMAL(15, 2) DEFAULT 0 COMMENT '類別總金額',
    item_count INTEGER DEFAULT 0 COMMENT '類別項目數',
    percentage DECIMAL(5, 2) DEFAULT 0 COMMENT '佔比百分比',
    statistics_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '統計生成日期',
    UNIQUE(bank_name, year_month, category)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_cat_stats_bank_month ON category_statistics(bank_name, year_month);
CREATE INDEX IF NOT EXISTS idx_cat_stats_category ON category_statistics(category);

-- ================================
-- 5. 處理日誌表 (用於追蹤每個PDF的處理狀態)
-- ================================
CREATE TABLE IF NOT EXISTS processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name VARCHAR(255) NOT NULL COMMENT 'PDF 檔案名',
    bank_name VARCHAR(100) COMMENT '銀行名稱',
    status VARCHAR(20) NOT NULL COMMENT '處理狀態: pending/processing/completed/failed',
    error_message TEXT COMMENT '錯誤信息',
    processing_time_ms INTEGER COMMENT '處理耗時 (毫秒)',
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '處理時間',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '創建時間'
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_logs_status ON processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_logs_bank ON processing_logs(bank_name);
CREATE INDEX IF NOT EXISTS idx_logs_processed ON processing_logs(processed_at);

-- ================================
-- 6. 用戶日誌表 (可選: 用於系統操作審計)
-- ================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation VARCHAR(50) NOT NULL COMMENT '操作類型: INSERT/UPDATE/DELETE/EXPORT',
    table_name VARCHAR(100) COMMENT '操作表名',
    record_id INTEGER COMMENT '操作記錄 ID',
    operation_detail TEXT COMMENT '操作詳情',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '操作時間'
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_audit_operation ON audit_logs(operation);
CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_logs(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

-- ================================
-- 初始化視圖 (可選)
-- ================================

-- 詳細報告視圖: 結合月結單和項目明細
CREATE VIEW IF NOT EXISTS v_detailed_reports AS
SELECT 
    mr.id,
    mr.file_name,
    mr.bank_name,
    mr.report_date,
    ri.item_name,
    ri.item_date,
    ri.amount,
    ri.category,
    mr.total_amount,
    mr.created_at
FROM monthly_reports mr
LEFT JOIN report_items ri ON mr.id = ri.report_id
WHERE mr.is_deleted = 0;

-- 月統計視圖
CREATE VIEW IF NOT EXISTS v_monthly_summary AS
SELECT 
    bank_name,
    year_month,
    total_income,
    total_expense,
    balance,
    item_count,
    category_count,
    statistics_date
FROM statistics
ORDER BY bank_name, year_month DESC;

-- ================================
-- 備註
-- ================================
-- SQLite 3 語法
-- 所有時間戳默認為 UTC
-- 軟刪除使用 is_deleted 標記
-- 外鍵約束需要啟用: PRAGMA foreign_keys = ON;
