"""
簡單測試腳本 - 測試PDF表格提取
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from src.pdf_processor import get_pdf_processor

def test_table_extraction():
    """測試表格提取功能"""
    pdf_path = Path("raw_data/test_statement.pdf")

    if not pdf_path.exists():
        print(f"PDF文件不存在: {pdf_path}")
        return

    print(f"測試PDF文件: {pdf_path}")

    # 獲取PDF處理器
    processor = get_pdf_processor()

    # 處理PDF
    result = processor.process_pdf(pdf_path)

    if not result['success']:
        print(f"PDF處理失敗: {result['error']}")
        return

    print(f"成功處理PDF，共 {result['page_count']} 頁")

    # 檢查表格數據
    if result['all_tables']:
        print(f"找到表格數據，共 {len(result['all_tables'])} 頁有表格")

        for page_num, tables in result['all_tables'].items():
            print(f"\n第 {page_num + 1} 頁的表格:")
            for table_idx, table in enumerate(tables):
                print(f"  表格 {table_idx + 1}: {len(table)} 行")

                # 顯示前幾行
                for row_idx, row in enumerate(table[:5]):  # 只顯示前5行
                    print(f"    行 {row_idx}: {row}")
    else:
        print("沒有找到表格數據")

    # 檢查文本數據
    print(f"\n文本內容預覽 (前500字符):")
    print(result['all_text'][:500])

if __name__ == "__main__":
    test_table_extraction()