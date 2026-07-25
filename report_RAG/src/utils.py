"""
工具函數模組
提供日誌、路徑、日期、金額等常用工具函數
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Any
from decimal import Decimal
import re
from .config import get_config


class Logger:
    """日誌管理類"""
    
    _loggers = {}
    
    @classmethod
    def setup(cls, name: str = 'report_rag') -> logging.Logger:
        """
        設置日誌系統
        
        Args:
            name: 日誌名稱
            
        Returns:
            Logger 實例
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        config = get_config()
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, config.APP_LOG_LEVEL.upper()))
        
        # 確保日誌目錄存在
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # 文件處理器 (帶輪轉)
        handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        
        # 控制台處理器
        console_handler = logging.StreamHandler()
        
        # 格式化
        formatter = logging.Formatter(
            config.get('logging.format', 
                      '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.addHandler(console_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def get_logger(cls, name: str = 'report_rag') -> logging.Logger:
        """獲取日誌實例"""
        if name not in cls._loggers:
            return cls.setup(name)
        return cls._loggers[name]


# ================================
# 路徑處理工具函數
# ================================

def ensure_path_exists(path: Path) -> Path:
    """
    確保路徑存在
    
    Args:
        path: 文件或目錄路徑
        
    Returns:
        路徑對象
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: Path) -> Tuple[float, str]:
    """
    獲取文件大小
    
    Args:
        file_path: 文件路徑
        
    Returns:
        元組 (大小, 單位)
    """
    size_bytes = file_path.stat().st_size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return round(size_bytes, 2), unit
        size_bytes /= 1024
    return round(size_bytes, 2), 'TB'


# ================================
# 日期時間工具函數
# ================================

def parse_date(date_str: str, formats: Optional[list] = None) -> Optional[datetime]:
    """
    解析日期字符串
    
    Args:
        date_str: 日期字符串
        formats: 嘗試的格式列表
        
    Returns:
        datetime 對象，如果解析失敗返回 None
    """
    if formats is None:
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d %b %Y',
            '%d %B %Y',
            '%Y-%m',
            '%Y/%m',
        ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def format_date(date_obj: datetime, fmt: str = '%Y-%m-%d') -> str:
    """
    格式化日期
    
    Args:
        date_obj: datetime 對象
        fmt: 格式字符串
        
    Returns:
        格式化的日期字符串
    """
    return date_obj.strftime(fmt)


def get_year_month(date_obj: datetime) -> str:
    """
    獲取年月字符串 (YYYY-MM)
    
    Args:
        date_obj: datetime 對象
        
    Returns:
        YYYY-MM 格式的字符串
    """
    return date_obj.strftime('%Y-%m')


# ================================
# 金額處理工具函數
# ================================

def parse_amount(amount_str: str) -> Optional[Decimal]:
    """
    解析金額字符串
    
    Args:
        amount_str: 金額字符串 (可能包含貨幣符號、逗號等)
        
    Returns:
        Decimal 對象，如果解析失敗返回 None
    """
    if not isinstance(amount_str, str):
        amount_str = str(amount_str)
    
    # 移除常見的貨幣符號和空格
    sanitized = amount_str.strip()
    sanitized = re.sub(r'[^\d.\-\+,]', '', sanitized)
    sanitized = sanitized.replace(',', '')
    
    try:
        return Decimal(sanitized)
    except:
        return None


def format_amount(amount: Decimal, decimal_places: int = 2, 
                 currency: str = 'NT$') -> str:
    """
    格式化金額
    
    Args:
        amount: Decimal 金額
        decimal_places: 小數位數
        currency: 貨幣符號
        
    Returns:
        格式化的金額字符串
    """
    if amount is None:
        return f"{currency} 0.00"
    
    formatted = f"{amount:,.{decimal_places}f}"
    return f"{currency}{formatted}"


def validate_amount(amount: Decimal, min_val: Decimal = None, 
                    max_val: Decimal = None) -> bool:
    """
    驗證金額有效性
    
    Args:
        amount: 金額
        min_val: 最小值
        max_val: 最大值
        
    Returns:
        驗證結果
    """
    if amount is None:
        return False
    
    if min_val is not None and amount < min_val:
        return False
    
    if max_val is not None and amount > max_val:
        return False
    
    return True


# ================================
# 字符串處理工具函數
# ================================

def clean_string(text: str) -> str:
    """
    清理字符串 (去除多餘空格、特殊字符等)
    
    Args:
        text: 原始字符串
        
    Returns:
        清理後的字符串
    """
    if not isinstance(text, str):
        return str(text)
    
    # 移除多餘空格
    text = ' '.join(text.split())
    # 移除首尾空格
    text = text.strip()
    return text


def normalize_string(text: str) -> str:
    """
    規範化字符串 (轉小寫、去除特殊字符等)
    
    Args:
        text: 原始字符串
        
    Returns:
        規範化的字符串
    """
    text = clean_string(text)
    text = text.lower()
    # 移除不必要的標點符號
    text = re.sub(r'[^\w\s\-]', '', text)
    return text


def extract_numbers(text: str) -> list:
    """
    從字符串中提取所有數字
    
    Args:
        text: 文本字符串
        
    Returns:
        數字列表
    """
    return re.findall(r'\d+(?:\.\d+)?', text)


# ================================
# 驗證工具函數
# ================================

def is_valid_date(date_str: str) -> bool:
    """
    驗證日期字符串是否有效
    
    Args:
        date_str: 日期字符串
        
    Returns:
        驗證結果
    """
    return parse_date(date_str) is not None


def is_valid_amount(amount_str: str) -> bool:
    """
    驗證金額字符串是否有效
    
    Args:
        amount_str: 金額字符串
        
    Returns:
        驗證結果
    """
    result = parse_amount(amount_str)
    return result is not None and result >= 0


# ================================
# 數據處理工具函數
# ================================

def chunk_list(lst: list, chunk_size: int) -> list:
    """
    將列表分割成指定大小的塊
    
    Args:
        lst: 原始列表
        chunk_size: 塊大小
        
    Returns:
        分割後的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def deduplicate_list(lst: list, key=None) -> list:
    """
    移除列表中的重複元素 (保持順序)
    
    Args:
        lst: 原始列表
        key: 用於比較的鍵函數
        
    Returns:
        去重後的列表
    """
    seen = set()
    result = []
    for item in lst:
        value = key(item) if key else item
        if value not in seen:
            seen.add(value)
            result.append(item)
    return result


# ================================
# 統計工具函數
# ================================

def calculate_percentage(part: float, total: float, decimal_places: int = 2) -> float:
    """
    計算百分比
    
    Args:
        part: 部分值
        total: 総值
        decimal_places: 小數位數
        
    Returns:
        百分比 (0-100)
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, decimal_places)


def calculate_statistics(values: list) -> dict:
    """
    計算統計數據
    
    Args:
        values: 數值列表
        
    Returns:
        包含統計信息的字典
    """
    if not values:
        return {
            'count': 0,
            'sum': 0,
            'avg': 0,
            'min': 0,
            'max': 0,
            'total': 0
        }
    
    numeric_values = [v for v in values if v is not None and isinstance(v, (int, float, Decimal))]
    
    if not numeric_values:
        return {
            'count': len(values),
            'sum': 0,
            'avg': 0,
            'min': 0,
            'max': 0,
            'total': 0
        }
    
    sum_val = sum(numeric_values)
    
    return {
        'count': len(numeric_values),
        'sum': float(sum_val),
        'avg': float(sum_val / len(numeric_values)),
        'min': float(min(numeric_values)),
        'max': float(max(numeric_values)),
        'total': float(sum_val)
    }


# ================================
# 初始化全局日誌
# ================================

# 在模組載入時設置日誌
_logger = Logger.setup()
