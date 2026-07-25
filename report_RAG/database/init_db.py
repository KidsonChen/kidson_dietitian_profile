"""
數據庫初始化腳本
用於創建和初始化數據庫表結構
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional


def init_database(db_path: str, schema_path: Optional[str] = None) -> bool:
    """
    初始化數據庫
    
    Args:
        db_path: 數據庫文件路徑
        schema_path: Schema SQL 文件路徑
        
    Returns:
        初始化成功與否
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 確保父目錄存在
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # 連接數據庫
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 啟用外鍵約束
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # 加載 SQL schema
        if schema_path is None:
            schema_path = db_dir / 'schema.sql'
        
        if not Path(schema_path).exists():
            logger.error(f"Schema 文件不存在: {schema_path}")
            conn.close()
            return False
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # 執行 SQL schema
        conn.executescript(sql_script)
        conn.commit()
        
        # 驗證表是否創建成功
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        tables = cursor.fetchall()
        logger.info(f"成功創建 {len(tables)} 個表: {[t[0] for t in tables]}")
        
        # 檢查是否創建了視圖
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='view';"
        )
        views = cursor.fetchall()
        if views:
            logger.info(f"成功創建 {len(views)} 個視圖: {[v[0] for v in views]}")
        
        conn.close()
        logger.info(f"數據庫初始化成功: {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"數據庫初始化失敗: {e}")
        return False


def check_database(db_path: str) -> bool:
    """
    檢查數據庫完整性
    
    Args:
        db_path: 數據庫文件路徑
        
    Returns:
        數據庫是否有效
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not Path(db_path).exists():
            logger.warning(f"數據庫文件不存在: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 啟用外鍵約束
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # 驗證表
        required_tables = [
            'monthly_reports',
            'report_items',
            'statistics',
            'category_statistics',
            'processing_logs',
            'audit_logs'
        ]
        
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        existing_tables = {t[0] for t in cursor.fetchall()}
        
        missing_tables = set(required_tables) - existing_tables
        if missing_tables:
            logger.error(f"缺少必要的表: {missing_tables}")
            conn.close()
            return False
        
        # 驗證表結構 (檢查主要列)
        checks = {
            'monthly_reports': ['id', 'file_name', 'bank_name', 'report_date'],
            'report_items': ['id', 'report_id', 'item_name', 'amount'],
            'statistics': ['id', 'bank_name', 'year_month'],
        }
        
        for table, columns in checks.items():
            cursor.execute(f"PRAGMA table_info({table});")
            existing_columns = {col[1] for col in cursor.fetchall()}
            missing_columns = set(columns) - existing_columns
            if missing_columns:
                logger.error(f"表 {table} 缺少列: {missing_columns}")
                conn.close()
                return False
        
        conn.close()
        logger.info("數據庫檢查通過")
        return True
        
    except Exception as e:
        logger.error(f"數據庫檢查失敗: {e}")
        return False


def reset_database(db_path: str, confirm: bool = False) -> bool:
    """
    重置數據庫 (刪除所有數據)
    
    Args:
        db_path: 數據庫文件路徑
        confirm: 是否需要確認
        
    Returns:
        重置成功與否
    """
    logger = logging.getLogger(__name__)
    
    if not Path(db_path).exists():
        logger.warning(f"數據庫文件不存在: {db_path}")
        return False
    
    if confirm:
        response = input(f"確認刪除 {db_path} 中的所有數據? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("操作已取消")
            return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 禁用外鍵約束以便刪除
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # 刪除所有表的數據
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        tables = cursor.fetchall()
        
        for table in tables:
            cursor.execute(f"DELETE FROM {table[0]};")
            logger.info(f"清空表: {table[0]}")
        
        conn.commit()
        conn.close()
        
        logger.info("數據庫已重置")
        return True
        
    except Exception as e:
        logger.error(f"數據庫重置失敗: {e}")
        return False


def backup_database(db_path: str, backup_path: Optional[str] = None) -> bool:
    """
    備份數據庫
    
    Args:
        db_path: 原始數據庫路徑
        backup_path: 備份路徑 (默認為 .bak)
        
    Returns:
        備份成功與否
    """
    logger = logging.getLogger(__name__)
    
    import shutil
    from datetime import datetime
    
    if not Path(db_path).exists():
        logger.error(f"數據庫文件不存在: {db_path}")
        return False
    
    if backup_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"數據庫已備份到: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"數據庫備份失敗: {e}")
        return False


if __name__ == '__main__':
    """命令行使用示例"""
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python init_db.py <db_path> [schema_path]")
        print("\n示例:")
        print("  python init_db.py ./database/report_rag.db ./database/schema.sql")
        sys.exit(1)
    
    db_path = sys.argv[1]
    schema_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = init_database(db_path, schema_path)
    sys.exit(0 if success else 1)
