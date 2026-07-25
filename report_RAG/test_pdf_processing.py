"""
測試PDF處理改進的腳本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from src.pdf_processor import get_pdf_processor

def test_pdf_processing():
    """測試PDF處理功能"""
    print("=== 測試PDF處理功能 ===")

    # 測試文件
    test_files = [
        "raw_data/test_statement.pdf",
        "raw_data/eStatementFile_20260406102144.pdf"  # 第一個真實PDF
    ]

    processor = get_pdf_processor()

    for file_path_str in test_files:
        file_path = Path(file_path_str)
        if not file_path.exists():
            print(f"文件不存在: {file_path}")
            continue

        print(f"\n處理文件: {file_path.name}")
        print("-" * 50)

        # 處理PDF
        result = processor.process_pdf(file_path)

        if not result['success']:
            print(f"處理失敗: {result['error']}")
            continue

        print(f"頁數: {result['page_count']}")
        print(f"文本長度: {len(result['all_text'])} 字符")

        # 檢查表格
        if result['all_tables']:
            total_tables = sum(len(tables) for tables in result['all_tables'].values())
            print(f"發現表格: {total_tables} 個")

            # 顯示第一個表格的前幾行
            for page_num, tables in result['all_tables'].items():
                if tables:
                    print(f"第 {page_num + 1} 頁第一個表格:")
                    table = tables[0]
                    for i, row in enumerate(table[:3]):  # 只顯示前3行
                        print(f"  行 {i+1}: {row}")
                    break
        else:
            print("沒有發現表格")

        # 顯示文本預覽
        print(f"文本預覽 (前300字符):")
        print(result['all_text'][:300])
        print("-" * 50)

if __name__ == "__main__":
    test_pdf_processing()