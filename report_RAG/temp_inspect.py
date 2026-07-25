"""
臨時腳本 - 檢查特定PDF文件
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import pdfplumber

def inspect_specific_pdf():
    """檢查特定的PDF文件"""
    file_path = Path("raw_data/account/eStatementFile_20260406102256.pdf")
    print(f"檢查PDF文件: {file_path}")

    try:
        with pdfplumber.open(file_path) as pdf:
            print(f"頁數: {len(pdf.pages)}")

            # 檢查每一頁
            for i, page in enumerate(pdf.pages):
                print(f"\n=== 第 {i+1} 頁 ===")

                # 提取文本
                text = page.extract_text()
                print(f"文本長度: {len(text)} 字符")
                print("文本預覽 (前300字符):")
                print(text[:300] if text else "無文本內容")
                print("-" * 50)

                # 檢查表格
                tables = page.extract_tables()
                if tables:
                    print(f"發現 {len(tables)} 個表格")
                    for j, table in enumerate(tables):
                        print(f"  表格 {j+1}: {len(table)} 行 x {len(table[0]) if table else 0} 列")
                        # 顯示前3行
                        for k, row in enumerate(table[:3]):
                            print(f"    行 {k+1}: {row}")
                else:
                    print("沒有發現表格")

                print("=" * 80)

    except Exception as e:
        print(f"處理PDF時出錯: {e}")

if __name__ == "__main__":
    inspect_specific_pdf()