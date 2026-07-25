"""
數據處理模組
負責數據驗證、清理、轉換和去重
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import re

from .config import get_config
from .utils import Logger, parse_date, parse_amount, clean_string, normalize_string


logger = Logger.get_logger(__name__)


class DataValidator:
    """數據驗證器"""
    
    def __init__(self):
        """初始化驗證器"""
        self.config = get_config()
        self.logger = logger
        self.errors = []
        self.warnings = []
    
    def validate_report_date(self, date_str: str) -> Tuple[bool, Optional[datetime]]:
        """
        驗證報告日期
        
        Args:
            date_str: 日期字符串
            
        Returns:
            元組 (驗證結果, datetime 對象)
        """
        if not date_str or not isinstance(date_str, str):
            return False, None
        
        date_obj = parse_date(date_str)
        if date_obj is None:
            self.errors.append(f"無效的日期格式: {date_str}")
            return False, None
        
        return True, date_obj
    
    def validate_amount(self, amount_str: str) -> Tuple[bool, Optional[Decimal]]:
        """
        驗證金額
        
        Args:
            amount_str: 金額字符串
            
        Returns:
            元組 (驗證結果, Decimal 對象)
        """
        if amount_str is None:
            return False, None
        
        amount = parse_amount(str(amount_str))
        if amount is None:
            self.errors.append(f"無效的金額格式: {amount_str}")
            return False, None
        
        # 檢查金額是否為負數
        if amount < 0:
            self.warnings.append(f"金額為負數: {amount}")
        
        return True, amount
    
    def validate_item_name(self, name: str) -> Tuple[bool, str]:
        """
        驗證項目名稱
        
        Args:
            name: 項目名稱
            
        Returns:
            元組 (驗證結果, 清理後的名稱)
        """
        if not name or not isinstance(name, str):
            return False, ""
        
        cleaned_name = clean_string(name).strip()
        if not cleaned_name:
            return False, ""
        
        # 檢查長度
        if len(cleaned_name) > 255:
            self.warnings.append(f"項目名稱過長: {cleaned_name[:50]}...")
            cleaned_name = cleaned_name[:255]
        
        return True, cleaned_name
    
    def validate_report_item(self, item: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        驗證單個報告項目
        
        Args:
            item: 項目字典
            
        Returns:
            元組 (驗證結果, 修正後的項目)
        """
        cleaned_item = {}
        
        # 必填字段檢查
        required_fields = ['item_name', 'amount']
        for field in required_fields:
            if field not in item or item[field] is None:
                self.errors.append(f"缺少必填字段: {field}")
                return False, cleaned_item
        
        # 驗證項目名稱
        valid, name = self.validate_item_name(item['item_name'])
        if not valid:
            self.errors.append(f"無效的項目名稱: {item['item_name']}")
            return False, cleaned_item
        cleaned_item['item_name'] = name
        
        # 驗證金額
        valid, amount = self.validate_amount(item['amount'])
        if not valid:
            return False, cleaned_item
        cleaned_item['amount'] = amount
        
        # 可選字段
        if 'item_date' in item and item['item_date']:
            valid, date_obj = self.validate_report_date(str(item['item_date']))
            cleaned_item['item_date'] = date_obj
        
        if 'category' in item and item['category']:
            cleaned_item['category'] = clean_string(item['category']).strip()
        
        if 'description' in item and item['description']:
            cleaned_item['description'] = clean_string(item['description']).strip()
        
        return True, cleaned_item
    
    def clear(self):
        """清除錯誤和警告"""
        self.errors = []
        self.warnings = []


class DataProcessor:
    """數據處理類"""
    
    def __init__(self):
        """初始化數據處理器"""
        self.config = get_config()
        self.logger = logger
        self.validator = DataValidator()
    
    def clean_text_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理文本數據
        
        Args:
            data: 原始數據字典
            
        Returns:
            清理後的數據
        """
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, str):
                cleaned[key] = clean_string(value)
            else:
                cleaned[key] = value
        return cleaned
    
    def extract_monetary_data(self, pdf_text: str) -> Dict[str, Decimal]:
        """
        從 PDF 文本中提取金額數據
        
        Args:
            pdf_text: PDF 提取的原始文本
            
        Returns:
            金額字典
        """
        monetary_data = {}
        
        # 尋找常見的金額模式
        patterns = {
            'total': r'(?:總計|合計|總額|total)[:\s]*([0-9,]+\.?[0-9]*)',
            'income': r'(?:收入|income)[:\s]*([0-9,]+\.?[0-9]*)',
            'expense': r'(?:支出|expense)[:\s]*([0-9,]+\.?[0-9]*)',
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, pdf_text, re.IGNORECASE)
            if matches:
                # 取最後一個匹配 (通常是最相關的)
                amount = parse_amount(matches[-1])
                if amount:
                    monetary_data[key] = amount
        
        return monetary_data

    def extract_currency_data(self, pdf_text: str) -> str:
        """
        從 PDF 文本中提取主要貨幣代碼

        Args:
            pdf_text: PDF 提取的原始文本

        Returns:
            貨幣代碼字符串，默認返回 HKD 或 TWD
        """
        currency_patterns = [
            r'\b(HKD|USD|TWD|JPY|EUR|CNY)\b',
            r'\b(TWD|HKD|USD|JPY|EUR|CNY)\s+Equivalent\b',
        ]

        for pattern in currency_patterns:
            matches = re.findall(pattern, pdf_text, re.IGNORECASE)
            if matches:
                currency = matches[0].upper()
                return currency

        # 對於臺幣默認值仍保持 TWD
        return 'TWD'
    
    def extract_date_data(self, pdf_text: str) -> Optional[datetime]:
        """
        從 PDF 文本中提取日期
        
        Args:
            pdf_text: PDF 提取的原始文本
            
        Returns:
            datetime 對象
        """
        # 優先嘗試完整日期格式（例如 6 March 2026 或 6 Mar 2026）
        date_patterns = [
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+\d{4}',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\b\s+\d{4}',
            r'\b\d{4}\D+\d{1,2}\D+月',  # 2024年4月 或 2024-4月
            r'\b\d{4}/\d{1,2}\b',  # 2024/4
            r'\b\d{4}-\d{1,2}\b',  # 2024-4
        ]

        candidates = []
        for pattern in date_patterns:
            for match in re.finditer(pattern, pdf_text, re.IGNORECASE):
                candidates.append((match.start(), match.group(0)))

        candidates.sort(key=lambda x: x[0])
        for _, match_text in candidates:
            parsed = parse_date(match_text)
            if parsed and 1900 <= parsed.year <= 2100:
                self.logger.info(f"提取日期: {parsed.strftime('%Y-%m')}")
                return parsed

        # 如果未找到完整日期，嘗試只提取年-月
        patterns = [
            r'(\d{4})\D+(\d{1,2})\D+月',
            r'\b(20\d{2})/(0?[1-9]|1[0-2])\b',
            r'\b(20\d{2})-(0?[1-9]|1[0-2])\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, pdf_text)
            if matches:
                try:
                    year, month = matches[0]
                    date = datetime(int(year), int(month), 1)
                    self.logger.info(f"提取日期: {date.strftime('%Y-%m')}")
                    return date
                except ValueError:
                    continue

        return None
    
    def deduplicate_items(self, items: List[Dict[str, Any]],
                         keys: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        去重項目
        
        Args:
            items: 項目列表
            keys: 去重依據的字段列表
            
        Returns:
            去重後的項目列表
        """
        if keys is None:
            keys = ['item_name', 'amount']
        
        seen = set()
        deduplicated = []
        duplicates_count = 0
        
        for item in items:
            # 生成去重鍵
            key_values = tuple(str(item.get(k, '')) for k in keys)
            if key_values not in seen:
                seen.add(key_values)
                deduplicated.append(item)
            else:
                duplicates_count += 1
        
        if duplicates_count > 0:
            self.logger.info(f"移除重複項目: {duplicates_count} 個")
        
        return deduplicated
    
    def process_items(self, items: List[Dict[str, Any]],
                     deduplicate: bool = True) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        批量處理項目
        
        Args:
            items: 原始項目列表
            deduplicate: 是否去重
            
        Returns:
            元組 (處理後的項目列表, 錯誤信息)
        """
        processed_items = []
        errors = []
        
        for i, item in enumerate(items):
            self.validator.clear()
            valid, cleaned_item = self.validator.validate_report_item(item)
            
            if valid:
                processed_items.append(cleaned_item)
            else:
                error_msg = f"第 {i + 1} 項錯誤: {'; '.join(self.validator.errors)}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
            
            if self.validator.warnings:
                for warning in self.validator.warnings:
                    self.logger.warning(f"第 {i + 1} 項警告: {warning}")
        
        # 去重
        if deduplicate and processed_items:
            processed_items = self.deduplicate_items(processed_items)
        
        self.logger.info(f"處理 {len(items)} 項，成功 {len(processed_items)} 項")
        
        return processed_items, errors
    
    def calculate_totals(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        計算合計
        
        Args:
            items: 項目列表
            
        Returns:
            合計統計字典
        """
        total_amount = Decimal(0)
        item_count = len(items)
        
        for item in items:
            if 'amount' in item and item['amount']:
                total_amount += item['amount']
        
        return {
            'total_amount': total_amount,
            'item_count': item_count,
            'average_amount': total_amount / item_count if item_count > 0 else Decimal(0),
        }
    
    def validate_consistency(self, report_data: Dict[str, Any],
                            calculated_total: Decimal) -> List[str]:
        """
        驗證數據一致性
        
        Args:
            report_data: 報告數據
            calculated_total: 計算得出的合計
            
        Returns:
            不一致的問題列表
        """
        issues = []
        
        if 'total_amount' in report_data:
            reported_total = parse_amount(str(report_data['total_amount']))
            if reported_total != calculated_total:
                difference = abs(reported_total - calculated_total)
                # 允許小數精度偏差 (例如 0.01 元)
                if difference > Decimal('0.01'):
                    issues.append(
                        f"總金額不一致: 報告顯示 {reported_total}, "
                        f"計算得出 {calculated_total}, 差額 {difference}"
                    )
        
        return issues


# 全局數據處理器實例
_data_processor = None


def get_data_processor() -> DataProcessor:
    """獲取全局數據處理器實例"""
    global _data_processor
    if _data_processor is None:
        _data_processor = DataProcessor()
    return _data_processor
