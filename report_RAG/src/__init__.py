"""
月結單處理系統
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Report RAG Team"
__description__ = "自動化月結單處理系統 - PDF讀取、Markdown生成、數據庫存儲、統計分析"

from .config import Config
from .utils import Logger

__all__ = ['Config', 'Logger', '__version__', '__author__', '__description__']
