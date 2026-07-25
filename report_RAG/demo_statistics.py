#!/usr/bin/env python3
"""
統計分析功能演示腳本

展示月結單處理系統的統計分析功能
"""

import sys
import os
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.db_manager import DatabaseManager
from src.statistics import StatisticsAnalyzer


def demo_statistics():
    """演示統計分析功能"""
    print("📊 月結單處理系統 - 統計分析功能演示")
    print("=" * 50)

    # 初始化組件
    config = Config()
    db_manager = DatabaseManager(str(config.DATABASE_PATH))
    analyzer = StatisticsAnalyzer()

    try:
        # 檢查數據庫連接
        print("🔍 檢查數據庫連接...")
        try:
            db_manager.get_connection()
            print("✅ 數據庫連接成功")
        except Exception as e:
            print(f"❌ 數據庫連接失敗: {e}")
            return

        # 獲取銀行列表
        all_reports = db_manager.list_monthly_reports()
        banks = list(set(report['bank_name'] for report in all_reports))
        if not banks:
            print("⚠️  數據庫中沒有銀行數據，請先處理一些PDF文件")
            return

        print(f"📋 找到 {len(banks)} 個銀行: {', '.join(banks)}")

        # 為每個銀行生成統計分析
        for bank_name in banks:
            print(f"\n🏦 分析銀行: {bank_name}")
            print("-" * 30)

            # 獲取月度統計
            monthly_reports = db_manager.list_monthly_reports(bank_name=bank_name)
            if not monthly_reports:
                print("⚠️  沒有月度報告數據")
                continue

            print(f"📅 找到 {len(monthly_reports)} 個月度報告")

            # 分析最近一個月的數據
            latest_report = monthly_reports[0]
            report_date = latest_report['report_date'][:7]  # YYYY-MM

            print(f"📊 分析 {report_date} 的數據...")

            # 生成月度統計
            monthly_stats = analyzer.analyze_monthly(db_manager, bank_name, report_date)
            print(f"   💰 總收入: {monthly_stats.get('total_income', 0)}")
            print(f"   💸 總支出: {monthly_stats.get('total_expense', 0)}")
            print(f"   📈 結余: {monthly_stats.get('balance', 0)}")
            print(f"   📝 項目數: {monthly_stats.get('item_count', 0)}")

            # 生成月度報告
            print("\n📄 生成月度報告...")
            monthly_report = analyzer.generate_monthly_report(db_manager, bank_name, report_date)

            # 保存報告
            report_dir = config.REPORT_DIR
            report_dir.mkdir(exist_ok=True)
            report_file = report_dir / f"{bank_name}_{report_date}_統計報告.md"

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(monthly_report)

            print(f"✅ 月度報告已保存: {report_file}")

            # 如果有多個月的數據，生成比較報告
            if len(monthly_reports) >= 2:
                print("\n📊 生成比較分析...")
                prev_report = monthly_reports[1]
                prev_date = prev_report['report_date'][:7]

                comparison_report = analyzer.generate_comparison_report(
                    db_manager, bank_name, prev_date, report_date, 'monthly'
                )

                comparison_file = report_dir / f"{bank_name}_{prev_date}_vs_{report_date}_比較報告.md"
                with open(comparison_file, 'w', encoding='utf-8') as f:
                    f.write(comparison_report)

                print(f"✅ 比較報告已保存: {comparison_file}")

        print("\n🎉 統計分析演示完成！")
        print(f"📁 報告文件保存在: {config.REPORT_DIR}")

    except Exception as e:
        print(f"❌ 演示過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_statistics()