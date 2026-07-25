"""
統計分析模組
負責數據統計、分析、可視化和報告生成
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from .config import get_config
from .utils import Logger, format_amount, calculate_percentage, calculate_statistics


logger = Logger.get_logger(__name__)


class StatisticsAnalyzer:
    """統計分析器"""
    
    def __init__(self):
        """初始化統計分析器"""
        self.config = get_config()
        self.logger = logger
    
    def analyze_transaction_types(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按交易類型分析項目數據
        
        Args:
            items: 項目列表
            
        Returns:
            交易類型分析結果
        """
        if not items:
            return {
                '收入': {'count': 0, 'total': Decimal(0), 'items': []},
                '支出': {'count': 0, 'total': Decimal(0), 'items': []},
                '轉帳': {'count': 0, 'total': Decimal(0), 'items': []},
                '其他': {'count': 0, 'total': Decimal(0), 'items': []},
            }
        
        transaction_types = {
            '收入': {'count': 0, 'total': Decimal(0), 'items': []},
            '支出': {'count': 0, 'total': Decimal(0), 'items': []},
            '轉帳': {'count': 0, 'total': Decimal(0), 'items': []},
            '其他': {'count': 0, 'total': Decimal(0), 'items': []},
        }
        
        # 關鍵詞匹配
        income_keywords = ['工資', '薪水', '獎金', '利息', '分紅', '稅退', '退款', '進帳', '轉入', 
                          'SALARY', 'BONUS', 'INTEREST', 'TRANSFER IN']
        transfer_keywords = ['轉帳', '轉移', '存款', '取款', 'TRANSFER', 'PAYMENT', '還款', '支付', 'WITHDRAWAL']
        
        for item in items:
            amount = Decimal(str(item.get('amount', 0)))
            category = item.get('category', '')
            item_name = item.get('item_name', '').upper()
            
            # 首先檢查 transaction_type 字段
            if 'transaction_type' in item:
                trans_type = item['transaction_type']
            else:
                # 根據項目名稱和類別判斷
                trans_type = '其他'
                
                # 檢查收入關鍵詞
                for keyword in income_keywords:
                    if keyword.upper() in item_name:
                        trans_type = '收入'
                        break
                
                # 檢查轉帳關鍵詞
                if trans_type == '其他':
                    for keyword in transfer_keywords:
                        if keyword.upper() in item_name:
                            trans_type = '轉帳'
                            break
                
                # 根據金額符號判斷
                if trans_type == '其他':
                    if amount > 0:
                        trans_type = '收入'
                    else:
                        trans_type = '支出'
            
            # 確保 trans_type 有效
            if trans_type not in transaction_types:
                trans_type = '其他'
            
            transaction_types[trans_type]['count'] += 1
            transaction_types[trans_type]['total'] += amount
            transaction_types[trans_type]['items'].append({
                'name': item.get('item_name', ''),
                'amount': amount,
                'date': item.get('item_date', ''),
                'category': item.get('category', '')
            })
        
        return transaction_types
    
    def analyze_items(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析項目數據
        
        Args:
            items: 項目列表
            
        Returns:
            分析結果字典
        """
        if not items:
            return {
                'total_count': 0,
                'total_amount': Decimal(0),
                'statistics': {},
                'categories': {},
            }
        
        # 基本統計
        amounts = [Decimal(str(item.get('amount', 0))) for item in items]
        stats = calculate_statistics(amounts)
        
        # 類別統計
        category_stats = defaultdict(lambda: {'count': 0, 'total': Decimal(0)})
        for item in items:
            category = item.get('category', 'Unknown')
            category_stats[category]['count'] += 1
            category_stats[category]['total'] += Decimal(str(item.get('amount', 0)))
        
        # 計算百分比
        total_amount = sum(amounts) if amounts else Decimal(0)
        for category in category_stats:
            category_stats[category]['percentage'] = calculate_percentage(
                float(category_stats[category]['total']),
                float(total_amount)
            )
        
        return {
            'total_count': len(items),
            'total_amount': total_amount,
            'statistics': stats,
            'categories': dict(category_stats),
        }
    
    def analyze_monthly(self, db_manager, bank_name: str, year_month: str) -> Dict[str, Any]:
        """
        進行月度分析
        
        Args:
            db_manager: 數據庫管理器實例
            bank_name: 銀行名稱
            year_month: 年月 (YYYY-MM)
            
        Returns:
            月度分析結果
        """
        # 直接從項目數據計算統計
        reports = db_manager.list_monthly_reports(bank_name=bank_name, 
                                                 start_date=f"{year_month}-01",
                                                 end_date=f"{year_month}-31")
        
        if not reports:
            return {
                'bank_name': bank_name,
                'year_month': year_month,
                'total_income': 0,
                'total_expense': 0,
                'balance': 0,
                'item_count': 0,
            }
        
        # 獲取項目數據並計算統計
        report_id = reports[0]['id']
        items = db_manager.get_report_items(report_id)
        
        total_income = Decimal(0)
        total_expense = Decimal(0)
        
        for item in items:
            amount = Decimal(str(item.get('amount', 0)))
            if amount > 0:
                total_income += amount
            else:
                total_expense += abs(amount)
        
        return {
            'bank_name': bank_name,
            'year_month': year_month,
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'balance': float(total_income - total_expense),
            'item_count': len(items),
        }
    
    def analyze_trend(self, db_manager, bank_name: str, 
                     months: int = 12) -> List[Dict[str, Any]]:
        """
        趨勢分析
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            months: 分析月數
            
        Returns:
            趨勢數據列表
        """
        from datetime import datetime, timedelta
        
        trend_data = []
        current = datetime.now()
        
        for i in range(months):
            date = current - timedelta(days=30 * i)
            year_month = date.strftime('%Y-%m')
            
            analysis = self.analyze_monthly(db_manager, bank_name, year_month)
            trend_data.append(analysis)
        
    def analyze_quarterly(self, db_manager, bank_name: str, year: int, quarter: int) -> Dict[str, Any]:
        """
        季度分析
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            year: 年份
            quarter: 季度 (1-4)
            
        Returns:
            季度分析結果
        """
        # 計算季度月份
        start_month = (quarter - 1) * 3 + 1
        months = [f"{year:04d}-{month:02d}" for month in range(start_month, start_month + 3)]
        
        quarterly_data = []
        total_income = Decimal(0)
        total_expense = Decimal(0)
        total_items = 0
        
        for month in months:
            monthly_data = self.analyze_monthly(db_manager, bank_name, month)
            quarterly_data.append(monthly_data)
            
            total_income += Decimal(str(monthly_data.get('total_income', 0)))
            total_expense += Decimal(str(monthly_data.get('total_expense', 0)))
            total_items += monthly_data.get('item_count', 0)
        
        return {
            'bank_name': bank_name,
            'year': year,
            'quarter': quarter,
            'period': f"{year}Q{quarter}",
            'months': months,
            'monthly_data': quarterly_data,
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'item_count': total_items,
            'avg_monthly_expense': total_expense / 3 if total_expense > 0 else Decimal(0),
        }
    
    def analyze_yearly(self, db_manager, bank_name: str, year: int) -> Dict[str, Any]:
        """
        年度分析
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            year: 年份
            
        Returns:
            年度分析結果
        """
        yearly_data = []
        total_income = Decimal(0)
        total_expense = Decimal(0)
        total_items = 0
        
        # 按季度分析
        quarterly_data = []
        for quarter in range(1, 5):
            quarter_data = self.analyze_quarterly(db_manager, bank_name, year, quarter)
            quarterly_data.append(quarter_data)
            
            total_income += Decimal(str(quarter_data.get('total_income', 0)))
            total_expense += Decimal(str(quarter_data.get('total_expense', 0)))
            total_items += quarter_data.get('item_count', 0)
        
        # 按月分析
        monthly_data = []
        for month in range(1, 13):
            month_str = f"{year:04d}-{month:02d}"
            monthly_analysis = self.analyze_monthly(db_manager, bank_name, month_str)
            monthly_data.append(monthly_analysis)
        
        return {
            'bank_name': bank_name,
            'year': year,
            'quarterly_data': quarterly_data,
            'monthly_data': monthly_data,
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'item_count': total_items,
            'avg_monthly_expense': total_expense / 12 if total_expense > 0 else Decimal(0),
            'avg_quarterly_expense': total_expense / 4 if total_expense > 0 else Decimal(0),
        }
    
    def calculate_growth_rates(self, db_manager, bank_name: str, 
                              periods: List[str]) -> Dict[str, Any]:
        """
        計算增長率
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            periods: 期間列表 (YYYY-MM 格式)
            
        Returns:
            增長率分析結果
        """
        if len(periods) < 2:
            return {'error': '至少需要2個期間'}
        
        growth_data = []
        for i in range(1, len(periods)):
            current_period = periods[i]
            previous_period = periods[i-1]
            
            current_data = self.analyze_monthly(db_manager, bank_name, current_period)
            previous_data = self.analyze_monthly(db_manager, bank_name, previous_period)
            
            current_expense = Decimal(str(current_data.get('total_expense', 0)))
            previous_expense = Decimal(str(previous_data.get('total_expense', 0)))
            
            if previous_expense > 0:
                growth_rate = ((current_expense - previous_expense) / previous_expense) * 100
            else:
                growth_rate = Decimal(0)
            
            growth_data.append({
                'period': current_period,
                'previous_period': previous_period,
                'current_expense': float(current_expense),
                'previous_expense': float(previous_expense),
                'growth_rate': float(growth_rate),
                'difference': float(current_expense - previous_expense),
            })
        
        return {
            'bank_name': bank_name,
            'periods': periods,
            'growth_data': growth_data,
            'avg_growth_rate': sum(d['growth_rate'] for d in growth_data) / len(growth_data),
        }
    
    def compare_months(self, db_manager, bank_name: str, 
                      year_month1: str, year_month2: str) -> Dict[str, Any]:
        """
        月度對比分析
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            year_month1: 第一個月份
            year_month2: 第二個月份
            
        Returns:
            對比結果
        """
        stats1 = self.analyze_monthly(db_manager, bank_name, year_month1)
        stats2 = self.analyze_monthly(db_manager, bank_name, year_month2)
        
        # 計算增长率
        expense1 = Decimal(str(stats1.get('total_expense', 0)))
        expense2 = Decimal(str(stats2.get('total_expense', 0)))
        
        if expense1 > 0:
            growth_rate = ((expense2 - expense1) / expense1 * 100)
        else:
            growth_rate = 0
        
        return {
            'period_1': year_month1,
            'period_2': year_month2,
            'stats_1': stats1,
            'stats_2': stats2,
            'expense_growth_rate': float(growth_rate),
            'difference': float(expense2 - expense1),
        }
    
    def generate_report_text(self, bank_name: str, analysis_result: Dict[str, Any]) -> str:
        """
        生成統計報告文本
        
        Args:
            bank_name: 銀行名稱
            analysis_result: 分析結果
            
        Returns:
            報告文本
        """
        report_lines = []
        currency = self.config.MARKDOWN_CURRENCY
        
        report_lines.append(f"# {bank_name} - 統計分析報告")
        report_lines.append("")
        report_lines.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("---")
        report_lines.append("")
        
        # 基本統計
        if 'statistics' in analysis_result:
            stats = analysis_result['statistics']
            report_lines.append("## 基本統計")
            report_lines.append("")
            report_lines.append(f"- **項目數量**: {stats.get('count', 0)}")
            report_lines.append(f"- **總金額**: {format_amount(Decimal(str(stats.get('total', 0))), currency=currency)}")
            report_lines.append(f"- **平均金額**: {format_amount(Decimal(str(stats.get('avg', 0))), currency=currency)}")
            report_lines.append(f"- **最大金額**: {format_amount(Decimal(str(stats.get('max', 0))), currency=currency)}")
            report_lines.append(f"- **最小金額**: {format_amount(Decimal(str(stats.get('min', 0))), currency=currency)}")
            report_lines.append("")
        
        # 類別統計
        if 'categories' in analysis_result and analysis_result['categories']:
            report_lines.append("## 類別統計")
            report_lines.append("")
            report_lines.append("| 類別 | 金額 | 占比 |")
            report_lines.append("|------|------|------|")
            
            for category, data in sorted(analysis_result['categories'].items(), 
                                        key=lambda x: x[1]['total'], reverse=True):
                report_lines.append(
                    f"| {category} | {format_amount(data['total'], currency=currency)} | "
                    f"{data.get('percentage', 0):.1f}% |"
                )
            
            report_lines.append("")
        
    def generate_monthly_report(self, db_manager, bank_name: str, year_month: str) -> str:
        """
        生成月度統計報告
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            year_month: 年月 (YYYY-MM)
            
        Returns:
            Markdown 格式的報告
        """
        # 獲取項目明細
        reports = db_manager.list_monthly_reports(bank_name=bank_name, 
                                                 start_date=f"{year_month}-01",
                                                 end_date=f"{year_month}-31")
        
        if reports:
            report_id = reports[0]['id']
            items = db_manager.get_report_items(report_id)
            item_analysis = self.analyze_items(items)
            
            # 分析交易類型
            transaction_analysis = self.analyze_transaction_types(items)
            
            # 從項目數據計算總結統計
            total_income = Decimal(0)
            total_expense = Decimal(0)
            item_count = len(items)
            
            for item in items:
                amount = Decimal(str(item.get('amount', 0)))
                trans_type = item.get('transaction_type', '')
                
                # 按交易類型分類
                if trans_type == '收入' or (not trans_type and amount > 0):
                    total_income += amount
                else:
                    total_expense += abs(amount)
            
            balance = total_income - total_expense
        else:
            item_analysis = {'total_count': 0, 'total_amount': Decimal(0), 'categories': {}}
            transaction_analysis = {
                '收入': {'count': 0, 'total': Decimal(0), 'items': []},
                '支出': {'count': 0, 'total': Decimal(0), 'items': []},
                '轉帳': {'count': 0, 'total': Decimal(0), 'items': []},
                '其他': {'count': 0, 'total': Decimal(0), 'items': []},
            }
            total_income = Decimal(0)
            total_expense = Decimal(0)
            balance = Decimal(0)
            item_count = 0
        
        # 生成報告
        report_lines = []
        currency = self.config.MARKDOWN_CURRENCY
        
        report_lines.append(f"# {bank_name} - {year_month} 月度統計報告")
        report_lines.append("")
        report_lines.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 月度總結
        report_lines.append("## 📊 月度總結")
        report_lines.append("")
        report_lines.append("| 指標 | 數值 |")
        report_lines.append("|------|------|")
        report_lines.append(f"| 總收入 | {format_amount(total_income, currency=currency)} |")
        report_lines.append(f"| 總支出 | {format_amount(total_expense, currency=currency)} |")
        report_lines.append(f"| 結余 | {format_amount(balance, currency=currency)} |")
        report_lines.append(f"| 項目數量 | {item_count} |")
        report_lines.append("")
        
        # 交易類型統計
        report_lines.append("## 💳 交易類型統計")
        report_lines.append("")
        report_lines.append("| 類型 | 金額 | 項目數 | 占比 |")
        report_lines.append("|------|------|--------|------|")
        
        total_amount = total_income + total_expense
        for trans_type in ['收入', '支出', '轉帳', '其他']:
            trans_data = transaction_analysis.get(trans_type, {})
            trans_total = trans_data.get('total', Decimal(0))
            trans_count = trans_data.get('count', 0)
            
            if trans_count > 0:
                percentage = (float(trans_total) / float(total_amount) * 100) if total_amount > 0 else 0
                report_lines.append(
                    f"| {trans_type} | {format_amount(trans_total, currency=currency)} | "
                    f"{trans_count} | {percentage:.1f}% |"
                )
        report_lines.append("")
        
        # 詳細交易清單（按交易類型分別顯示）
        for trans_type in ['收入', '支出', '轉帳', '其他']:
            trans_data = transaction_analysis.get(trans_type, {})
            trans_items = trans_data.get('items', [])
            
            if trans_items:
                report_lines.append(f"### {trans_type}明細")
                report_lines.append("")
                report_lines.append("| 日期 | 項目 | 金額 | 類別 |")
                report_lines.append("|------|------|------|------|")
                
                for item in sorted(trans_items, key=lambda x: x['date'] or '', reverse=True):
                    report_lines.append(
                        f"| {item['date'] or '-'} | {item['name'][:30]} | "
                        f"{format_amount(item['amount'], currency=currency)} | {item['category']} |"
                    )
                report_lines.append("")
        
        # 類別統計
        if item_analysis['categories']:
            report_lines.append("## 📈 支出類別統計")
            report_lines.append("")
            report_lines.append("| 類別 | 金額 | 占比 | 項目數 |")
            report_lines.append("|------|------|------|--------|")
            
            for category, data in sorted(item_analysis['categories'].items(), 
                                        key=lambda x: x[1]['total'], reverse=True):
                report_lines.append(
                    f"| {category} | {format_amount(data['total'], currency=currency)} | "
                    f"{data.get('percentage', 0):.1f}% | {data['count']} |"
                )
            report_lines.append("")
        
        # 統計指標
        if 'statistics' in item_analysis:
            stats = item_analysis['statistics']
            report_lines.append("## 📋 統計指標")
            report_lines.append("")
            report_lines.append(f"- **平均支出**: {format_amount(Decimal(str(stats.get('avg', 0))), currency=currency)}")
            report_lines.append(f"- **最大支出**: {format_amount(Decimal(str(stats.get('max', 0))), currency=currency)}")
            report_lines.append(f"- **最小支出**: {format_amount(Decimal(str(stats.get('min', 0))), currency=currency)}")
            report_lines.append("")
        
        return '\n'.join(report_lines)
    
    def generate_quarterly_report(self, db_manager, bank_name: str, year: int, quarter: int) -> str:
        """
        生成季度統計報告
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            year: 年份
            quarter: 季度
            
        Returns:
            Markdown 格式的報告
        """
        # 計算季度月份
        start_month = (quarter - 1) * 3 + 1
        months = [f"{year:04d}-{month:02d}" for month in range(start_month, start_month + 3)]
        
        # 收集所有月份的數據
        all_items = []
        monthly_summaries = []
        
        for month in months:
            reports = db_manager.list_monthly_reports(bank_name=bank_name, 
                                                     start_date=f"{month}-01",
                                                     end_date=f"{month}-31")
            
            if reports:
                report_id = reports[0]['id']
                items = db_manager.get_report_items(report_id)
                all_items.extend(items)
                
                # 計算月度統計
                monthly_income = Decimal(0)
                monthly_expense = Decimal(0)
                
                for item in items:
                    amount = Decimal(str(item.get('amount', 0)))
                    if amount > 0:
                        monthly_income += amount
                    else:
                        monthly_expense += abs(amount)
                
                monthly_summaries.append({
                    'year_month': month,
                    'total_income': monthly_income,
                    'total_expense': monthly_expense,
                    'balance': monthly_income - monthly_expense,
                    'item_count': len(items)
                })
            else:
                monthly_summaries.append({
                    'year_month': month,
                    'total_income': Decimal(0),
                    'total_expense': Decimal(0),
                    'balance': Decimal(0),
                    'item_count': 0
                })
        
        # 計算季度總計
        total_income = sum(summary['total_income'] for summary in monthly_summaries)
        total_expense = sum(summary['total_expense'] for summary in monthly_summaries)
        total_items = sum(summary['item_count'] for summary in monthly_summaries)
        
        # 生成報告
        report_lines = []
        currency = self.config.MARKDOWN_CURRENCY
        
        report_lines.append(f"# {bank_name} - {year}年第{quarter}季度統計報告")
        report_lines.append("")
        report_lines.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**報告期間**: {months[0]} 至 {months[-1]}")
        report_lines.append("")
        
        # 季度總結
        report_lines.append("## 📊 季度總結")
        report_lines.append("")
        report_lines.append("| 指標 | 數值 |")
        report_lines.append("|------|------|")
        report_lines.append(f"| 總收入 | {format_amount(total_income, currency=currency)} |")
        report_lines.append(f"| 總支出 | {format_amount(total_expense, currency=currency)} |")
        report_lines.append(f"| 結余 | {format_amount(total_income - total_expense, currency=currency)} |")
        report_lines.append(f"| 月均支出 | {format_amount(total_expense / 3 if total_expense > 0 else Decimal(0), currency=currency)} |")
        report_lines.append(f"| 總項目數 | {total_items} |")
        report_lines.append("")
        
        # 月度明細
        report_lines.append("## 📅 月度明細")
        report_lines.append("")
        report_lines.append("| 月份 | 收入 | 支出 | 結余 | 項目數 |")
        report_lines.append("|------|------|------|------|--------|")
        
        for summary in monthly_summaries:
            report_lines.append(
                f"| {summary['year_month']} | "
                f"{format_amount(summary['total_income'], currency=currency)} | "
                f"{format_amount(summary['total_expense'], currency=currency)} | "
                f"{format_amount(summary['balance'], currency=currency)} | "
                f"{summary['item_count']} |"
            )
        report_lines.append("")
        
        return '\n'.join(report_lines)
    
    def generate_yearly_report(self, db_manager, bank_name: str, year: int) -> str:
        """
        生成年度統計報告
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            year: 年份
            
        Returns:
            Markdown 格式的報告
        """
        # 收集全年數據
        quarterly_summaries = []
        total_income = Decimal(0)
        total_expense = Decimal(0)
        total_items = 0
        
        for quarter in range(1, 5):
            start_month = (quarter - 1) * 3 + 1
            months = [f"{year:04d}-{month:02d}" for month in range(start_month, start_month + 3)]
            
            # 收集季度數據
            quarterly_items = []
            quarterly_income = Decimal(0)
            quarterly_expense = Decimal(0)
            quarterly_item_count = 0
            
            for month in months:
                reports = db_manager.list_monthly_reports(bank_name=bank_name, 
                                                         start_date=f"{month}-01",
                                                         end_date=f"{month}-31")
                
                if reports:
                    report_id = reports[0]['id']
                    items = db_manager.get_report_items(report_id)
                    quarterly_items.extend(items)
                    quarterly_item_count += len(items)
                    
                    # 計算月度統計
                    for item in items:
                        amount = Decimal(str(item.get('amount', 0)))
                        if amount > 0:
                            quarterly_income += amount
                        else:
                            quarterly_expense += abs(amount)
            
            quarterly_summaries.append({
                'period': f"{year}Q{quarter}",
                'total_income': quarterly_income,
                'total_expense': quarterly_expense,
                'balance': quarterly_income - quarterly_expense,
                'item_count': quarterly_item_count
            })
            
            total_income += quarterly_income
            total_expense += quarterly_expense
            total_items += quarterly_item_count
        
        # 生成報告
        report_lines = []
        currency = self.config.MARKDOWN_CURRENCY
        
        report_lines.append(f"# {bank_name} - {year}年度統計報告")
        report_lines.append("")
        report_lines.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 年度總結
        report_lines.append("## 📊 年度總結")
        report_lines.append("")
        report_lines.append("| 指標 | 數值 |")
        report_lines.append("|------|------|")
        report_lines.append(f"| 總收入 | {format_amount(total_income, currency=currency)} |")
        report_lines.append(f"| 總支出 | {format_amount(total_expense, currency=currency)} |")
        report_lines.append(f"| 年度結余 | {format_amount(total_income - total_expense, currency=currency)} |")
        report_lines.append(f"| 月均支出 | {format_amount(total_expense / 12 if total_expense > 0 else Decimal(0), currency=currency)} |")
        report_lines.append(f"| 季均支出 | {format_amount(total_expense / 4 if total_expense > 0 else Decimal(0), currency=currency)} |")
        report_lines.append(f"| 總項目數 | {total_items} |")
        report_lines.append("")
        
        # 季度總結
        report_lines.append("## 📈 季度總結")
        report_lines.append("")
        report_lines.append("| 季度 | 收入 | 支出 | 結余 | 項目數 |")
        report_lines.append("|------|------|------|------|--------|")
        
        for summary in quarterly_summaries:
            report_lines.append(
                f"| {summary['period']} | "
                f"{format_amount(summary['total_income'], currency=currency)} | "
                f"{format_amount(summary['total_expense'], currency=currency)} | "
                f"{format_amount(summary['balance'], currency=currency)} | "
                f"{summary['item_count']} |"
            )
        report_lines.append("")
        
        return '\n'.join(report_lines)
    
    def generate_comparison_report(self, db_manager, bank_name: str, 
                                 period1: str, period2: str, comparison_type: str = 'monthly') -> str:
        """
        生成比較統計報告
        
        Args:
            db_manager: 數據庫管理器
            bank_name: 銀行名稱
            period1: 第一個期間
            period2: 第二個期間
            comparison_type: 比較類型 (monthly, quarterly, yearly)
            
        Returns:
            Markdown 格式的比較報告
        """
        if comparison_type == 'monthly':
            data1 = self.analyze_monthly(db_manager, bank_name, period1)
            data2 = self.analyze_monthly(db_manager, bank_name, period2)
            title = f"{bank_name} - {period1} vs {period2} 月度比較報告"
        elif comparison_type == 'quarterly':
            # 解析季度格式 (2024Q1)
            year1, q1 = period1.split('Q')
            year2, q2 = period2.split('Q')
            data1 = self.analyze_quarterly(db_manager, bank_name, int(year1), int(q1))
            data2 = self.analyze_quarterly(db_manager, bank_name, int(year2), int(q2))
            title = f"{bank_name} - {period1} vs {period2} 季度比較報告"
        else:
            return "不支持的比較類型"
        
        report_lines = []
        currency = self.config.MARKDOWN_CURRENCY
        
        report_lines.append(f"# {title}")
        report_lines.append("")
        report_lines.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 比較總結
        report_lines.append("## 📊 比較總結")
        report_lines.append("")
        report_lines.append("| 指標 | 期間1 | 期間2 | 差異 | 變化率 |")
        report_lines.append("|------|-------|-------|------|--------|")
        
        income1 = Decimal(str(data1.get('total_income', 0)))
        income2 = Decimal(str(data2.get('total_income', 0)))
        expense1 = Decimal(str(data1.get('total_expense', 0)))
        expense2 = Decimal(str(data2.get('total_expense', 0)))
        
        # 收入比較
        income_diff = income2 - income1
        income_rate = ((income2 - income1) / income1 * 100) if income1 > 0 else Decimal(0)
        
        # 支出比較
        expense_diff = expense2 - expense1
        expense_rate = ((expense2 - expense1) / expense1 * 100) if expense1 > 0 else Decimal(0)
        
        report_lines.append(
            f"| 收入 | {format_amount(income1, currency=currency)} | "
            f"{format_amount(income2, currency=currency)} | "
            f"{format_amount(income_diff, currency=currency)} | "
            f"{float(income_rate):+.1f}% |"
        )
        report_lines.append(
            f"| 支出 | {format_amount(expense1, currency=currency)} | "
            f"{format_amount(expense2, currency=currency)} | "
            f"{format_amount(expense_diff, currency=currency)} | "
            f"{float(expense_rate):+.1f}% |"
        )
        report_lines.append(
            f"| 結余 | {format_amount(income1 - expense1, currency=currency)} | "
            f"{format_amount(income2 - expense2, currency=currency)} | "
            f"{format_amount((income2 - expense2) - (income1 - expense1), currency=currency)} | - |"
        )
        report_lines.append("")
        
        # 趨勢分析
        report_lines.append("## 📈 趨勢分析")
        report_lines.append("")
        if expense_rate > 0:
            report_lines.append(f"⚠️ **支出增加**: 較上期增加 {float(expense_rate):.1f}%")
        elif expense_rate < 0:
            report_lines.append(f"✅ **支出減少**: 較上期減少 {abs(float(expense_rate)):.1f}%")
        else:
            report_lines.append("➡️ **支出持平**: 與上期持平")
        
        if income_rate > 0:
            report_lines.append(f"✅ **收入增加**: 較上期增加 {float(income_rate):.1f}%")
        elif income_rate < 0:
            report_lines.append(f"⚠️ **收入減少**: 較上期減少 {abs(float(income_rate)):.1f}%")
        else:
            report_lines.append("➡️ **收入持平**: 與上期持平")
        report_lines.append("")
        
        return '\n'.join(report_lines)
        """
        導出統計數據
        
        Args:
            analysis_result: 分析結果
            output_format: 輸出格式 (csv, json)
            
        Returns:
            導出内容
        """
        if output_format == 'csv':
            return self._export_csv(analysis_result)
        elif output_format == 'json':
            return self._export_json(analysis_result)
        else:
            self.logger.error(f"不支持的格式: {output_format}")
            return None
    
    @staticmethod
    def _export_csv(analysis_result: Dict[str, Any]) -> str:
        """導出為 CSV 格式"""
        lines = []
        
        # 類別統計 CSV
        lines.append("Category,Amount,Count,Percentage")
        if 'categories' in analysis_result:
            for category, data in analysis_result['categories'].items():
                lines.append(
                    f'"{category}",{data["total"]},{data["count"]},{data.get("percentage", 0)}'
                )
        
        return '\n'.join(lines)
    
    def export_statistics(self, analysis_result: Dict[str, Any],
                         output_format: str = 'csv') -> Optional[str]:
        """
        導出統計數據
        
        Args:
            analysis_result: 分析結果
            output_format: 輸出格式 (csv, json)
            
        Returns:
            導出内容
        """
        if output_format == 'csv':
            return self._export_csv(analysis_result)
        elif output_format == 'json':
            return self._export_json(analysis_result)
        else:
            self.logger.error(f"不支持的格式: {output_format}")
            return None
    
    @staticmethod
    def _export_csv(analysis_result: Dict[str, Any]) -> str:
        """導出為 CSV 格式"""
        lines = []
        
        # 類別統計 CSV
        lines.append("Category,Amount,Count,Percentage")
        if 'categories' in analysis_result:
            for category, data in analysis_result['categories'].items():
                lines.append(f"{category},{data['total']},{data['count']},{data.get('percentage', 0):.2f}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _export_json(analysis_result: Dict[str, Any]) -> str:
        """導出為 JSON 格式"""
        import json
        return json.dumps(analysis_result, default=str, ensure_ascii=False, indent=2)
        """
        生成圖表
        
        Args:
            analysis_result: 分析結果
            chart_type: 圖表類型 (pie, bar, line)
            output_path: 輸出路徑 (可選)
            
        Returns:
            圖表文件路徑或 None
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # 非交互式後端
            
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            
            if chart_type == 'pie' and 'categories' in analysis_result:
                return self._generate_pie_chart(analysis_result, output_path)
            elif chart_type == 'bar' and 'categories' in analysis_result:
                return self._generate_bar_chart(analysis_result, output_path)
            elif chart_type == 'line' and 'trend_data' in analysis_result:
                return self._generate_line_chart(analysis_result, output_path)
            else:
                self.logger.warning(f"不支持的圖表類型或數據格式: {chart_type}")
                return None
                
        except ImportError as e:
            self.logger.error(f"圖表生成需要 matplotlib: {e}")
            return None
        except Exception as e:
            self.logger.error(f"圖表生成失敗: {e}")
            return None
    
    def _generate_pie_chart(self, analysis_result: Dict[str, Any], output_path: Optional[str] = None) -> Optional[str]:
        """生成圓餅圖"""
        import matplotlib.pyplot as plt
        
        categories = analysis_result.get('categories', {})
        if not categories:
            return None
        
        # 準備數據
        labels = []
        sizes = []
        for category, data in sorted(categories.items(), key=lambda x: x[1]['total'], reverse=True):
            labels.append(category)
            sizes.append(float(data['total']))
        
        # 生成圖表
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        
        ax.axis('equal')
        ax.set_title('支出類別占比', fontsize=16, pad=20)
        
        # 設置字體
        plt.setp(autotexts, size=10, weight="bold")
        plt.setp(texts, size=12)
        
        # 保存圖表
        if output_path is None:
            output_path = self.config.REPORT_DIR / f"pie_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        else:
            output_path = Path(output_path)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _generate_bar_chart(self, analysis_result: Dict[str, Any], output_path: Optional[str] = None) -> Optional[str]:
        """生成柱狀圖"""
        import matplotlib.pyplot as plt
        
        categories = analysis_result.get('categories', {})
        if not categories:
            return None
        
        # 準備數據
        labels = []
        values = []
        for category, data in sorted(categories.items(), key=lambda x: x[1]['total'], reverse=True):
            labels.append(category)
            values.append(float(data['total']))
        
        # 生成圖表
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(labels, values, color='skyblue', edgecolor='navy', linewidth=1)
        
        ax.set_title('各類別支出金額', fontsize=16, pad=20)
        ax.set_xlabel('類別', fontsize=12)
        ax.set_ylabel('金額', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        
        # 添加數值標籤
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 保存圖表
        if output_path is None:
            output_path = self.config.REPORT_DIR / f"bar_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        else:
            output_path = Path(output_path)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _generate_line_chart(self, analysis_result: Dict[str, Any], output_path: Optional[str] = None) -> Optional[str]:
        """生成折線圖 (趨勢圖)"""
        import matplotlib.pyplot as plt
        
        trend_data = analysis_result.get('trend_data', [])
        if not trend_data:
            return None
        
        # 準備數據
        months = []
        expenses = []
        for data in trend_data:
            months.append(data.get('year_month', ''))
            expenses.append(float(data.get('total_expense', 0)))
        
        # 生成圖表
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(months, expenses, marker='o', linewidth=2, markersize=6, color='red')
        
        ax.set_title('月度支出趨勢', fontsize=16, pad=20)
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('支出金額', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # 添加數值標籤
        for i, (month, expense) in enumerate(zip(months, expenses)):
            ax.annotate(f'{expense:,.0f}', (month, expense), 
                       xytext=(0, 10), textcoords='offset points',
                       ha='center', fontsize=9)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 保存圖表
        if output_path is None:
            output_path = self.config.REPORT_DIR / f"line_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        else:
            output_path = Path(output_path)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)


# 全局統計分析器實例
_analyzer = None


def get_statistics_analyzer() -> StatisticsAnalyzer:
    """獲取全局統計分析器實例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = StatisticsAnalyzer()
    return _analyzer
