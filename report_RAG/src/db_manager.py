"""
數據庫管理模組
負責數據庫連接、查詢、插入、更新和刪除操作
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from contextlib import contextmanager

from .config import get_config
from .utils import Logger


logger = Logger.get_logger(__name__)


class DatabaseManager:
    """數據庫管理類"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化數據庫管理器
        
        Args:
            db_path: 數據庫路徑
        """
        self.config = get_config()
        self.db_path = db_path or self.config.DATABASE_PATH
        self.logger = logger
    
    @contextmanager
    def get_connection(self):
        """
        獲取數據庫連接上下文管理器
        
        Yields:
            sqlite3 連接對象
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 返回字典而非元組
            conn.execute("PRAGMA foreign_keys = ON;")  # 啟用外鍵約束
            conn.execute("PRAGMA journal_mode = WAL;")  # 啟用 WAL 模式
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            self.logger.error(f"數據庫錯誤: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # ================================
    # 月結單表操作
    # ================================
    
    def insert_monthly_report(self, data: Dict[str, Any]) -> Optional[int]:
        """
        插入月結單記錄
        
        Args:
            data: 月結單數據字典
                {
                    'file_name': str,
                    'bank_name': str,
                    'report_date': datetime,
                    'total_amount': Decimal,
                    'currency': str,
                    'item_count': int,
                    'md_file_path': str,
                }
            
        Returns:
            插入後的記錄 ID，失敗返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                report_date = data['report_date']
                if isinstance(report_date, datetime):
                    report_date = report_date.strftime('%Y-%m-%d')

                cursor.execute("""
                    INSERT INTO monthly_reports
                    (file_name, bank_name, report_date, total_amount, 
                     currency, item_count, validation_status, md_file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['file_name'],
                    data['bank_name'],
                    report_date,
                    float(data['total_amount']),
                    data.get('currency', 'TWD'),
                    data.get('item_count', 0),
                    data.get('validation_status', 'valid'),
                    data.get('md_file_path'),
                ))
                
                report_id = cursor.lastrowid
                self.logger.info(f"成功插入月結單: ID={report_id}, {data['file_name']}")
                return report_id
        except sqlite3.IntegrityError as e:
            self.logger.error(f"數據完整性錯誤 (可能是文件已存在): {e}")
            return None
        except Exception as e:
            self.logger.error(f"插入月結單失敗: {e}")
            return None
    
    def get_monthly_report(self, report_id: int) -> Optional[Dict]:
        """
        查詢月結單記錄
        
        Args:
            report_id: 月結單 ID
            
        Returns:
            月結單字典，未找到返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM monthly_reports WHERE id = ? AND is_deleted = 0",
                    (report_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"查詢月結單失敗: {e}")
            return None

    def get_monthly_report_by_file_name(self, file_name: str) -> Optional[Dict]:
        """
        根據文件名查詢月結單記錄
        
        Args:
            file_name: PDF 文件名
            
        Returns:
            月結單字典，未找到返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM monthly_reports WHERE file_name = ? AND is_deleted = 0",
                    (file_name,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"根據文件名查詢月結單失敗: {e}")
            return None

    def delete_report_items(self, report_id: int) -> bool:
        """
        刪除指定月結單的所有項目
        
        Args:
            report_id: 月結單 ID
            
        Returns:
            刪除成功與否
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM report_items WHERE report_id = ?", (report_id,))
                self.logger.info(f"成功刪除月結單項目: report_id={report_id}")
                return True
        except Exception as e:
            self.logger.error(f"刪除報告項目失敗: {e}")
            return False

    def update_monthly_report(self, report_id: int, data: Dict[str, Any]) -> bool:
        """
        更新月結單記錄
        
        Args:
            report_id: 月結單 ID
            data: 更新數據
            
        Returns:
            更新成功與否
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 構建動態 SQL
                set_clauses = []
                values = []
                for key, value in data.items():
                    if isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d')
                    if isinstance(value, Decimal):
                        value = float(value)
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
                
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                values.append(report_id)
                
                sql = f"UPDATE monthly_reports SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(sql, values)
                
                self.logger.info(f"成功更新月結單: ID={report_id}")
                return True
        except Exception as e:
            self.logger.error(f"更新月結單失敗: {e}")
            return False
    
    def delete_monthly_report(self, report_id: int, soft_delete: bool = True) -> bool:
        """
        刪除月結單記錄
        
        Args:
            report_id: 月結單 ID
            soft_delete: 軟刪除 (標記) 或硬刪除 (永久删除)
            
        Returns:
            刪除成功與否
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if soft_delete:
                    cursor.execute(
                        "UPDATE monthly_reports SET is_deleted = 1 WHERE id = ?",
                        (report_id,)
                    )
                else:
                    cursor.execute(
                        "DELETE FROM monthly_reports WHERE id = ?",
                        (report_id,)
                    )
                
                self.logger.info(f"成功刪除月結單: ID={report_id}")
                return True
        except Exception as e:
            self.logger.error(f"刪除月結單失敗: {e}")
            return False
    
    # ================================
    # 項目明細表操作
    # ================================
    
    def insert_report_items(self, report_id: int, items: List[Dict[str, Any]]) -> bool:
        """
        批量插入項目明細
        
        Args:
            report_id: 月結單 ID
            items: 項目列表
            
        Returns:
            插入成功與否
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for item in items:
                    item_date = item.get('item_date')
                    if isinstance(item_date, datetime):
                        item_date = item_date.strftime('%Y-%m-%d')

                    amount = item.get('amount')
                    amount_value = float(amount) if amount is not None else 0

                    cursor.execute("""
                        INSERT INTO report_items
                        (report_id, item_name, item_date, amount, category, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        report_id,
                        item['item_name'],
                        item_date,
                        amount_value,
                        item.get('category'),
                        item.get('description'),
                    ))
                
                self.logger.info(f"成功插入 {len(items)} 個項目")
                return True
        except Exception as e:
            self.logger.error(f"插入項目失敗: {e}")
            return False
    
    def get_report_items(self, report_id: int) -> List[Dict]:
        """
        查詢月結單的所有項目
        
        Args:
            report_id: 月結單 ID
            
        Returns:
            項目列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM report_items WHERE report_id = ? AND is_valid = 1",
                    (report_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"查詢項目失敗: {e}")
            return []
    
    # ================================
    # 統計表操作
    # ================================
    
    def insert_statistics(self, data: Dict[str, Any]) -> bool:
        """
        插入或更新統計記錄
        
        Args:
            data: 統計數據字典
            
        Returns:
            插入成功與否
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 先嘗試更新，如果沒有則插入
                cursor.execute("""
                    INSERT OR REPLACE INTO statistics
                    (bank_name, year_month, total_income, total_expense, balance,
                     item_count, category_count, avg_amount, max_amount, min_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['bank_name'],
                    data['year_month'],
                    float(data.get('total_income', 0)),
                    float(data.get('total_expense', 0)),
                    float(data.get('balance', 0)),
                    data.get('item_count', 0),
                    data.get('category_count', 0),
                    float(data.get('avg_amount', 0)),
                    float(data.get('max_amount', 0)),
                    float(data.get('min_amount', 0)),
                ))
                
                self.logger.info(f"成功插入統計: {data['bank_name']} - {data['year_month']}")
                return True
        except Exception as e:
            self.logger.error(f"插入統計失敗: {e}")
            return False
    
    def get_statistics_by_month(self, bank_name: str, year_month: str) -> Optional[Dict]:
        """
        查詢特定月份的統計
        
        Args:
            bank_name: 銀行名稱
            year_month: 年月 (YYYY-MM)
            
        Returns:
            統計字典，未找到返回 None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM statistics
                    WHERE bank_name = ? AND year_month = ?
                """, (bank_name, year_month))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"查詢統計失敗: {e}")
            return None
    
    # ================================
    # 查詢操作
    # ================================
    
    def list_monthly_reports(self, bank_name: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> List[Dict]:
        """
        查詢月結單列表
        
        Args:
            bank_name: 銀行名稱 (可選)
            start_date: 開始日期 (可選)
            end_date: 結束日期 (可選)
            
        Returns:
            月結單列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = "SELECT * FROM monthly_reports WHERE is_deleted = 0"
                params = []
                
                if bank_name:
                    sql += " AND bank_name = ?"
                    params.append(bank_name)
                
                if start_date:
                    sql += " AND report_date >= ?"
                    params.append(start_date)
                
                if end_date:
                    sql += " AND report_date <= ?"
                    params.append(end_date)
                
                sql += " ORDER BY report_date DESC"
                
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"查詢月結單列表失敗: {e}")
            return []
    
    # ================================
    # 統計查詢
    # ================================
    
    def get_category_totals(self, report_id: int) -> Dict[str, Decimal]:
        """
        按類別統計項目金額
        
        Args:
            report_id: 月結單 ID
            
        Returns:
            {類別: 費用總額}
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT category, SUM(amount) as total
                    FROM report_items
                    WHERE report_id = ? AND is_valid = 1 AND category IS NOT NULL
                    GROUP BY category
                    ORDER BY total DESC
                """, (report_id,))
                
                return {row['category']: Decimal(str(row['total'])) 
                        for row in cursor.fetchall()}
        except Exception as e:
            self.logger.error(f"查詢類別統計失敗: {e}")
            return {}
    
    def get_monthly_summary(self, year_month: str, bank_name: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取指定月份的總結數據
        
        Args:
            year_month: 年月 (YYYY-MM)
            bank_name: 銀行名稱 (可選)
            
        Returns:
            月份總結數據字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 查詢該月的月結單
                sql = """
                    SELECT mr.*, 
                           GROUP_CONCAT(ri.item_name || '|' || ri.amount || '|' || ri.category || '|' || ri.item_date) as items_data
                    FROM monthly_reports mr
                    LEFT JOIN report_items ri ON mr.id = ri.report_id AND ri.is_valid = 1
                    WHERE mr.is_deleted = 0 
                    AND strftime('%Y-%m', mr.report_date) = ?
                """
                params = [year_month]
                
                if bank_name:
                    sql += " AND mr.bank_name = ?"
                    params.append(bank_name)
                
                sql += " GROUP BY mr.id ORDER BY mr.report_date"
                
                cursor.execute(sql, params)
                reports = cursor.fetchall()
                
                # 整合數據
                total_amount = Decimal(0)
                all_items = []
                report_summaries = []
                
                for report in reports:
                    report_dict = dict(report)
                    report_summaries.append({
                        'file_name': report_dict['file_name'],
                        'bank_name': report_dict['bank_name'],
                        'report_date': report_dict['report_date'],
                        'total_amount': Decimal(str(report_dict['total_amount'])),
                        'currency': report_dict['currency'],
                        'item_count': report_dict['item_count']
                    })
                    
                    total_amount += Decimal(str(report_dict['total_amount']))
                    
                    # 解析項目數據
                    items_data = report_dict.get('items_data')
                    if items_data:
                        for item_str in items_data.split(','):
                            if item_str and '|' in item_str:
                                parts = item_str.split('|', 3)
                                if len(parts) >= 4:
                                    item_name, amount, category, item_date = parts
                                    all_items.append({
                                        'item_name': item_name,
                                        'amount': Decimal(amount),
                                        'category': category,
                                        'item_date': item_date,
                                        'bank_name': report_dict['bank_name']
                                    })
                
                # 按類別統計
                category_totals = {}
                for item in all_items:
                    category = item.get('category', '其他')
                    if category not in category_totals:
                        category_totals[category] = Decimal(0)
                    category_totals[category] += item['amount']
                
                return {
                    'year_month': year_month,
                    'bank_name': bank_name,
                    'total_amount': total_amount,
                    'report_count': len(report_summaries),
                    'item_count': len(all_items),
                    'reports': report_summaries,
                    'items': all_items,
                    'category_totals': category_totals,
                    'currency': 'TWD'  # 假設統一為台幣
                }
                
        except Exception as e:
            self.logger.error(f"獲取月份總結失敗: {e}")
            return {}
    
    # ================================
    # 數據庫維護
    # ================================
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        獲取數據庫統計信息
        
        Returns:
            統計信息字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # 表統計
                cursor.execute("""
                    SELECT name FROM sqlite_master WHERE type='table'
                """)
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table[0]}")
                    count = cursor.fetchone()['count']
                    stats[table[0]] = count
                
                return stats
        except Exception as e:
            self.logger.error(f"獲取數據庫統計失敗: {e}")
            return {}
    
    def vacuum_database(self) -> bool:
        """
        數據庫整理和優化
        
        Returns:
            優化成功與否
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("VACUUM;")
                self.logger.info("數據庫已整理和優化")
                return True
        except Exception as e:
            self.logger.error(f"數據庫整理失敗: {e}")
            return False


# 全局數據庫管理器實例
_db_manager = None


def get_db_manager(db_path: Optional[str] = None) -> DatabaseManager:
    """獲取全局數據庫管理器實例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
