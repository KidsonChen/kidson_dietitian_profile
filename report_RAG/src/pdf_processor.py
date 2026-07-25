"""
PDF 處理模組
負責讀取、解析和提取 PDF 月結單信息
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pdfplumber

from .config import get_config
from .utils import Logger, get_file_size, parse_date, clean_string


logger = Logger.get_logger(__name__)


class PDFProcessor:
    """PDF 處理類"""
    
    def __init__(self):
        """初始化 PDF 處理器"""
        self.config = get_config()
        self.logger = logger
    
    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        驗證 PDF 文件
        
        Args:
            file_path: PDF 文件路徑
            
        Returns:
            元組 (驗證結果, 錯誤信息)
        """
        # 檢查文件是否存在
        if not file_path.exists():
            msg = f"文件不存在: {file_path}"
            self.logger.error(msg)
            return False, msg
        
        # 檢查文件擴展名
        if file_path.suffix.lower() != '.pdf':
            msg = f"不支持的文件格式: {file_path.suffix}"
            self.logger.error(msg)
            return False, msg
        
        # 檢查文件大小
        size, unit = get_file_size(file_path)
        if unit == 'MB' and size > self.config.PDF_MAX_FILE_SIZE:
            msg = f"文件大小超過限制 ({size}{unit} > {self.config.PDF_MAX_FILE_SIZE}MB)"
            self.logger.error(msg)
            return False, msg
        
        return True, ""
    
    def open_pdf(self, file_path: Path) -> Optional[pdfplumber.PDF]:
        """
        打開 PDF 文件
        
        Args:
            file_path: PDF 文件路徑
            
        Returns:
            pdfplumber.PDF 對象，如果打開失敗返回 None
        """
        try:
            pdf = pdfplumber.open(file_path)
            self.logger.info(f"成功打開 PDF: {file_path.name} ({len(pdf.pages)} 頁)")
            return pdf
        except Exception as e:
            self.logger.error(f"打開 PDF 失敗: {e}")
            return None
    
    def get_page_count(self, pdf: pdfplumber.PDF) -> int:
        """
        獲取 PDF 頁數
        
        Args:
            pdf: pdfplumber.PDF 對象
            
        Returns:
            頁數
        """
        return len(pdf.pages)
    
    def extract_text(self, pdf: pdfplumber.PDF, page_num: int = 0) -> str:
        """
        提取 PDF 某一頁的文本
        
        Args:
            pdf: pdfplumber.PDF 對象
            page_num: 页码 (0-based)
            
        Returns:
            提取的文本
        """
        try:
            if page_num >= len(pdf.pages):
                self.logger.warning(f"頁碼超出範圍: {page_num}")
                return ""
            
            page = pdf.pages[page_num]
            text = page.extract_text()
            return text if text else ""
        except Exception as e:
            self.logger.error(f"提取文本失敗 (第 {page_num + 1} 頁): {e}")
            return ""
    
    def extract_tables(self, pdf: pdfplumber.PDF, page_num: int = 0) -> List[List]:
        """
        提取 PDF 某一頁的表格
        
        Args:
            pdf: pdfplumber.PDF 對象
            page_num: 页码 (0-based)
            
        Returns:
            表格數據列表
        """
        try:
            if page_num >= len(pdf.pages):
                self.logger.warning(f"頁碼超出範圍: {page_num}")
                return []
            
            page = pdf.pages[page_num]
            
            # 使用更靈活的表格提取參數
            tables = page.extract_tables(table_settings={
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines",
                "snap_tolerance": 3,
                "snap_x_tolerance": 1,
                "snap_y_tolerance": 1,
                "join_tolerance": 3,
                "join_x_tolerance": 1,
                "join_y_tolerance": 1,
                "edge_min_length": 3,
                "edge_min_length_prefilter": 1,
                "min_words_vertical": 3,
                "min_words_horizontal": 1,
                "intersection_tolerance": 3,
                "intersection_x_tolerance": 1,
                "intersection_y_tolerance": 1,
                "text_settings": {
                    "keep_blank_chars": False,
                    "text_x_tolerance": 1,
                    "text_y_tolerance": 1,
                },
            })
            
            # 如果沒有找到表格，嘗試更寬鬆的設置
            if not tables:
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                    "snap_x_tolerance": 2,
                    "snap_y_tolerance": 2,
                    "join_tolerance": 5,
                    "join_x_tolerance": 2,
                    "join_y_tolerance": 2,
                    "text_settings": {
                        "keep_blank_chars": False,
                    },
                })
            
            return tables if tables else []
        except Exception as e:
            self.logger.error(f"提取表格失敗 (第 {page_num + 1} 頁): {e}")
            return []
    
    def extract_all_tables(self, pdf: pdfplumber.PDF) -> Dict[int, List[List]]:
        """
        提取 PDF 全部表格
        
        Args:
            pdf: pdfplumber.PDF 對象
            
        Returns:
            字典 {頁碼: 表格數據}
        """
        all_tables = {}
        for page_num in range(len(pdf.pages)):
            tables = self.extract_tables(pdf, page_num)
            if tables:
                all_tables[page_num] = tables
        
        self.logger.info(f"提取表格數量: {sum(len(t) for t in all_tables.values())} 個")
        return all_tables
    
    def extract_metadata(self, pdf: pdfplumber.PDF) -> Dict[str, Any]:
        """
        提取 PDF 文檔信息
        
        Args:
            pdf: pdfplumber.PDF 對象
            
        Returns:
            元數據字典
        """
        try:
            metadata = pdf.metadata
            return {
                'Title': metadata.get('Title', ''),
                'Author': metadata.get('Author', ''),
                'Subject': metadata.get('Subject', ''),
                'Creator': metadata.get('Creator', ''),
                'Producer': metadata.get('Producer', ''),
                'Pages': len(pdf.pages),
            }
        except Exception as e:
            self.logger.warning(f"提取元數據失敗: {e}")
            return {'Pages': len(pdf.pages)}
    
    def process_pdf(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        完整 PDF 處理流程
        
        Args:
            file_path: PDF 文件路徑
            
        Returns:
            處理結果字典，包含提取的所有信息
        """
        # 驗證文件
        valid, error_msg = self.validate_file(file_path)
        if not valid:
            return {
                'success': False,
                'error': error_msg,
                'file_path': str(file_path)
            }
        
        # 打開 PDF
        pdf = self.open_pdf(file_path)
        if pdf is None:
            return {
                'success': False,
                'error': '無法打開 PDF 文件',
                'file_path': str(file_path)
            }
        
        try:
            # 提取基本信息
            result = {
                'success': True,
                'file_path': str(file_path),
                'file_name': file_path.name,
                'page_count': self.get_page_count(pdf),
                'metadata': self.extract_metadata(pdf),
                'all_text': "",
                'all_tables': {},
            }
            
            # 提取全部文本和表格
            all_text_parts = []
            for page_num in range(result['page_count']):
                text = self.extract_text(pdf, page_num)
                all_text_parts.append(text)
            
            result['all_text'] = '\n'.join(all_text_parts)
            result['all_tables'] = self.extract_all_tables(pdf)
            
            self.logger.info(f"成功處理 PDF: {file_path.name}")
            return result
            
        except Exception as e:
            self.logger.error(f"處理 PDF 期間發生錯誤: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': str(file_path)
            }
        finally:
            pdf.close()
    
    def batch_process(self, directory: Path, pattern: str = '*.pdf') -> List[Dict]:
        """
        批量處理 PDF 文件
        
        Args:
            directory: PDF 文件目錄
            pattern: 文件名模式
            
        Returns:
            處理結果列表
        """
        if not directory.exists():
            self.logger.error(f"目錄不存在: {directory}")
            return []
        
        pdf_files = list(directory.glob(pattern))
        self.logger.info(f"找到 {len(pdf_files)} 個 PDF 文件")
        
        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            self.logger.info(f"處理進度: {i}/{len(pdf_files)}")
            result = self.process_pdf(pdf_file)
            if result:
                results.append(result)
        
        self.logger.info(f"批量處理完成: {len(results)} 個文件成功")
        return results


# 全局 PDF 處理器實例
_pdf_processor = None


def get_pdf_processor() -> PDFProcessor:
    """獲取全局 PDF 處理器實例"""
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
    return _pdf_processor
