"""
配置管理模組
支援環境變量、配置檔案和默認值的三層配置
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class Config:
    """應用程序配置類"""
    
    # 項目根目錄
    BASE_DIR = Path(__file__).parent.parent
    
    # 配置初始化
    def __init__(self, env_file: Optional[str] = None):
        """
        初始化配置
        
        Args:
            env_file: 環境變量文件路徑
        """
        # 加載環境變量
        if env_file is None:
            env_file = self.BASE_DIR / '.env'
        
        if os.path.exists(env_file):
            load_dotenv(env_file)
        
        # 加載配置文件
        self.config_file = self.BASE_DIR / 'config.json'
        self.config_dict = self._load_json_config() if self.config_file.exists() else {}
    
    def _load_json_config(self) -> Dict[str, Any]:
        """加載 JSON 配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"無法加載配置文件: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置值 (優先級: 環境變量 > JSON配置 > 默認值)
        
        Args:
            key: 配置鍵名 (支持點號分隔符，如 'database.type')
            default: 默認值
            
        Returns:
            配置值
        """
        # 1. 從環境變量獲取
        env_value = os.getenv(key.upper().replace('.', '_'))
        if env_value is not None:
            return self._parse_value(env_value)
        
        # 2. 從 JSON 配置獲取
        keys = key.split('.')
        current = self.config_dict
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k)
            else:
                current = None
                break
        
        if current is not None:
            return current
        
        # 3. 返回默認值
        return default
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """
        解析字符串值為正確的類型
        
        Args:
            value: 字符串值
            
        Returns:
            解析後的值
        """
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        elif value.isdigit():
            return int(value)
        elif value.replace('.', '', 1).isdigit():
            return float(value)
        return value
    
    # ================================
    # 應用配置
    # ================================
    
    @property
    def APP_NAME(self) -> str:
        return self.get('project.name', '月結單處理系統')
    
    @property
    def APP_VERSION(self) -> str:
        return self.get('project.version', '1.0.0')
    
    @property
    def APP_DEBUG(self) -> bool:
        return self.get('APP_DEBUG', False)
    
    @property
    def APP_LOG_LEVEL(self) -> str:
        return self.get('APP_LOG_LEVEL', 'INFO')
    
    @property
    def TIMEZONE(self) -> str:
        return self.get('APP_TIMEZONE', 'Asia/Taipei')
    
    # ================================
    # 路徑配置
    # ================================
    
    @property
    def RAW_DATA_DIR(self) -> Path:
        return self.BASE_DIR / self.get('paths.raw_data', 'raw_data')
    
    @property
    def ACCOUNT_DATA_DIR(self) -> Path:
        return self.RAW_DATA_DIR / 'account'
    
    @property
    def CREDIT_CARD_DATA_DIR(self) -> Path:
        return self.RAW_DATA_DIR / 'credit card'
    
    @property
    def MARKDOWN_DIR(self) -> Path:
        return self.BASE_DIR / self.get('paths.markdown_output', 'md')
    
    @property
    def REPORT_DIR(self) -> Path:
        return self.BASE_DIR / self.get('paths.report_output', 'report')
    
    @property
    def DATABASE_DIR(self) -> Path:
        return self.BASE_DIR / self.get('paths.database_path', 'database')
    
    @property
    def SOURCE_DIR(self) -> Path:
        return self.BASE_DIR / self.get('paths.source_code', 'src')
    
    @property
    def LOG_DIR(self) -> Path:
        return self.BASE_DIR / 'logs'
    
    # ================================
    # 數據庫配置
    # ================================
    
    @property
    def DATABASE_TYPE(self) -> str:
        return self.get('database.type', 'sqlite')
    
    @property
    def DATABASE_NAME(self) -> str:
        return self.get('database.name', 'report_rag.db')
    
    @property
    def DATABASE_PATH(self) -> str:
        """完整的數據庫路徑"""
        if self.DATABASE_TYPE == 'sqlite':
            return str(self.DATABASE_DIR / self.DATABASE_NAME)
        return self.get('database.name', 'report_rag')
    
    @property
    def DATABASE_HOST(self) -> str:
        return self.get('database.host', 'localhost')
    
    @property
    def DATABASE_PORT(self) -> int:
        port = self.get('database.port', 5432)
        return int(port) if isinstance(port, str) else port
    
    @property
    def DATABASE_USER(self) -> str:
        return self.get('database.username', '')
    
    @property
    def DATABASE_PASSWORD(self) -> str:
        return self.get('database.password', '')
    
    # ================================
    # PDF 處理配置
    # ================================
    
    @property
    def PDF_TIMEOUT(self) -> int:
        timeout = self.get('pdf_processing.timeout_seconds', 300)
        return int(timeout) if isinstance(timeout, str) else timeout
    
    @property
    def PDF_MAX_FILE_SIZE(self) -> int:
        """最大 PDF 文件大小 (MB)"""
        size = self.get('pdf_processing.max_file_size_mb', 50)
        return int(size) if isinstance(size, str) else size
    
    @property
    def PDF_EXTRACT_TABLES(self) -> bool:
        return self.get('pdf_processing.extract_tables', True)
    
    @property
    def PDF_OCR_ENABLED(self) -> bool:
        return self.get('pdf_processing.ocr_enabled', False)
    
    # ================================
    # Markdown 生成配置
    # ================================
    
    @property
    def MARKDOWN_INCLUDE_METADATA(self) -> bool:
        return self.get('markdown_generation.include_metadata', True)
    
    @property
    def MARKDOWN_INCLUDE_TOC(self) -> bool:
        return self.get('markdown_generation.include_toc', True)
    
    @property
    def MARKDOWN_DATE_FORMAT(self) -> str:
        return self.get('markdown_generation.date_format', '%Y-%m-%d')
    
    @property
    def MARKDOWN_CURRENCY(self) -> str:
        return self.get('markdown_generation.currency_symbol', 'NT$')
    
    # ================================
    # 統計配置
    # ================================
    
    @property
    def STATISTICS_ENABLE_CHARTS(self) -> bool:
        return self.get('statistics.enable_charts', True)
    
    @property
    def STATISTICS_CHART_FORMAT(self) -> str:
        return self.get('statistics.chart_format', 'png')
    
    # ================================
    # 銀行配置
    # ================================
    
    @property
    def BANKS(self) -> list:
        """支持的銀行代碼列表"""
        banks = self.get('BANKS', 'bank_a,bank_b,bank_c')
        if isinstance(banks, str):
            return [b.strip() for b in banks.split(',')]
        return banks
    
    # ================================
    # 日誌配置
    # ================================
    
    @property
    def LOG_FILE(self) -> Path:
        log_file = self.get('LOG_FILE', 'logs/app.log')
        return Path(log_file) if self.BASE_DIR.name != Path(log_file).parent.name else self.LOG_DIR / Path(log_file).name
    
    @property
    def LOG_MAX_BYTES(self) -> int:
        """日誌文件最大大小 (字節)"""
        size = self.get('LOG_MAX_SIZE', 10485760)  # 10MB
        return int(size) if isinstance(size, str) else size
    
    @property
    def LOG_BACKUP_COUNT(self) -> int:
        """日誌備份文件數量"""
        count = self.get('LOG_BACKUP_COUNT', 5)
        return int(count) if isinstance(count, str) else count
    
    # ================================
    # 配置驗證和初始化
    # ================================
    
    def ensure_directories_exist(self) -> None:
        """確保所有必要的目錄存在"""
        dirs = [
            self.RAW_DATA_DIR,
            self.MARKDOWN_DIR,
            self.REPORT_DIR,
            self.DATABASE_DIR,
            self.LOG_DIR,
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> bool:
        """驗證配置有效性"""
        errors = []
        
        # 驗證必需的配置
        if not self.APP_NAME:
            errors.append("APP_NAME 未設定")
        
        if self.DATABASE_TYPE not in ('sqlite', 'postgresql', 'mysql'):
            errors.append(f"無效的 DATABASE_TYPE: {self.DATABASE_TYPE}")
        
        if errors:
            logging.error("配置驗證失敗:" + '\n'.join(errors))
            return False
        
        return True
    
    def __repr__(self) -> str:
        """配置信息字符串表示"""
        return (
            f"Config(\n"
            f"  app_name={self.APP_NAME},\n"
            f"  app_version={self.APP_VERSION},\n"
            f"  database_type={self.DATABASE_TYPE},\n"
            f"  database_path={self.DATABASE_PATH},\n"
            f"  banks={self.BANKS}\n"
            f")"
        )


# 全局配置實例
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """獲取全局配置實例 (單例模式)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def set_config(config: Config) -> None:
    """設置全局配置實例"""
    global _config_instance
    _config_instance = config
