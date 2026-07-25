#!/usr/bin/env python3
"""
檢查數據庫統計信息
"""

import sys
from src.db_manager import get_db_manager

def main():
    manager = get_db_manager()
    stats = manager.get_database_stats()
    
    print("\n" + "="*50)
    print("數據庫統計信息")
    print("="*50)
    
    for table, count in stats.items():
        print(f"  {table}: {count} 條記錄")
    
    print("="*50)
    
    # 按銀行查詢報告數量
    print("\n按銀行統計:")
    all_reports = manager.list_monthly_reports()
    
    bank_stats = {}
    for report in all_reports:
        bank = report['bank_name']
        if bank not in bank_stats:
            bank_stats[bank] = 0
        bank_stats[bank] += 1
    
    for bank, count in bank_stats.items():
        print(f"  {bank}: {count} 個報告")
    
    print("\n✅ 數據庫檢查完成")

if __name__ == '__main__':
    main()
