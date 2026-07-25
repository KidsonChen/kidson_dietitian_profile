"""
Markdown 生成模組
負責將月結單數據轉換為 Markdown 格式報告
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal

from .config import get_config
from .utils import Logger, format_date, format_amount, parse_date


logger = Logger.get_logger(__name__)


class MarkdownGenerator:
    """Markdown 生成器"""
    
    def __init__(self):
        """初始化 Markdown 生成器"""
        self.config = get_config()
        self.logger = logger
    
    def _normalize_report_date(self, report_date: Any) -> datetime:
        if isinstance(report_date, datetime):
            return report_date
        if isinstance(report_date, str):
            parsed = parse_date(report_date)
            if parsed is not None:
                return parsed
        return datetime.now()

    def generate_metadata_header(self, report_data: Dict[str, Any]) -> str:
        """
        生成 Markdown 元數據頭部
        
        Args:
            report_data: 報告數據
            
        Returns:
            YAML 格式的元數據
        """
        report_date = self._normalize_report_date(report_data.get('report_date', datetime.now()))
        month_str = report_date.strftime('%Y-%m')
        metadata = f"""---
title: {report_data.get('title', '月結單')}
date: {format_date(datetime.now())}
bank: {report_data.get('bank_name', '')}
month: {month_str}
currency: {report_data.get('currency', 'TWD')}
---

"""
        return metadata
    
    def generate_content(self, report_data: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
        """
        生成 Markdown 內容
        
        Args:
            report_data: 報告數據
            items: 項目列表
            
        Returns:
            Markdown 內容字符串
        """
        content = []
        currency = report_data.get('currency', 'TWD')
        
        # 標題
        content.append(f"# {report_data.get('title', '月結單')}")
        content.append("")
        
        # 基本信息
        content.append("## 基本信息")
        content.append("")
        normalized_report_date = self._normalize_report_date(report_data.get('report_date', datetime.now()))
        content.append(f"- **銀行**: {report_data.get('bank_name', 'N/A')}")
        content.append(f"- **月份**: {format_date(normalized_report_date, '%Y年%m月')}")
        content.append(f"- **幣種**: {currency}")
        content.append(f"- **生成時間**: {format_date(datetime.now())}")
        content.append("")
        
        # 統計摘要
        content.append("## 統計摘要")
        content.append("")
        
        total_amount = report_data.get('total_amount', Decimal(0))
        item_count = len(items)
        
        content.append(f"| 指標 | 數值 |")
        content.append(f"|------|------|")
        content.append(f"| **合計金額** | {format_amount(total_amount, currency=currency)} |")
        content.append(f"| **項目數量** | {item_count} |")
        
        if item_count > 0:
            avg_amount = total_amount / item_count
            content.append(f"| **平均金額** | {format_amount(avg_amount, currency=currency)} |")
        
        content.append("")
        
        # 項目明細
        if items:
            content.append("## 項目明細")
            content.append("")
            content.append("| 日期 | 項目名稱 | 類別 | 金額 |")
            content.append("|------|----------|------|------|")
            
            for item in items:
                item_date = item.get('item_date')
                if item_date:
                    if isinstance(item_date, str):
                        date_str = item_date  # 如果是字符串，直接使用
                    else:
                        date_str = format_date(item_date, '%Y-%m-%d')
                else:
                    date_str = 'N/A'
                name = item.get('item_name', '')
                category = item.get('category', 'N/A')
                amount = format_amount(Decimal(str(item.get('amount', 0))), currency=currency)
                
                content.append(f"| {date_str} | {name} | {category} | {amount} |")
            
            content.append("")
        
        # 類別統計
        if items:
            category_totals = {}
            for item in items:
                category = item.get('category', 'N/A')
                amount = Decimal(str(item.get('amount', 0)))
                if category not in category_totals:
                    category_totals[category] = Decimal(0)
                category_totals[category] += amount
            
            if category_totals:
                content.append("## 類別統計")
                content.append("")
                content.append("| 類別 | 金額 | 占比 |")
                content.append("|------|------|------|")
                
                for category, amount in sorted(category_totals.items(), 
                                              key=lambda x: x[1], reverse=True):
                    percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                    content.append(
                        f"| {category} | {format_amount(amount, currency=currency)} | {percentage:.1f}% |"
                    )
                
                content.append("")
        
        # 備註
        content.append("## 備註")
        content.append("")
        content.append("- 本報告由系統自動生成")
        content.append(f"- 數據來源: {report_data.get('file_name', 'N/A')}")
        content.append(f"- 生成時間: {format_date(datetime.now(), '%Y-%m-%d %H:%M:%S')}")
        
        return '\n'.join(content)
    
    def generate_markdown(self, report_data: Dict[str, Any], items: List[Dict[str, Any]],
                         output_path: Optional[Path] = None) -> Optional[str]:
        """
        生成 Markdown 文件
        
        Args:
            report_data: 報告數據
            items: 項目列表
            output_path: 輸出文件路徑 (可選)
            
        Returns:
            Markdown 內容字符串
        """
        try:
            # 生成內容
            metadata = self.generate_metadata_header(report_data)
            content = self.generate_content(report_data, items)
            markdown_content = metadata + content
            
            # 保存到文件 (如果指定了路徑)
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                self.logger.info(f"成功生成 Markdown: {output_path}")
            
            return markdown_content
        
        except Exception as e:
            self.logger.error(f"生成 Markdown 失敗: {e}")
            return None
    
    def generate_monthly_summary(self, monthly_data: Dict[str, Any],
                                output_path: Optional[Path] = None) -> Optional[str]:
        """
        生成月份總結 Markdown 報告
        
        Args:
            monthly_data: 月份總結數據
            output_path: 輸出文件路徑 (可選)
            
        Returns:
            Markdown 內容字符串
        """
        try:
            year_month = monthly_data.get('year_month', '')
            bank_name = monthly_data.get('bank_name', '全部銀行')
            currency = monthly_data.get('currency', 'TWD')
            
            # 解析年月
            try:
                year, month = year_month.split('-')
                month_name = f"{year}年{month}月"
            except:
                month_name = year_month
            
            # 生成元數據頭部
            metadata = f"""---
title: {month_name} 消費總結
date: {format_date(datetime.now())}
month: {year_month}
bank: {bank_name}
type: monthly-summary
---

"""
            content = []
            
            # 標題
            content.append(f"# {month_name} 消費總結")
            if bank_name != '全部銀行':
                content.append(f"**銀行**: {bank_name}")
            content.append("")
            
            # 基本統計
            content.append("## 基本統計")
            content.append("")
            content.append(f"- **統計月份**: {month_name}")
            content.append(f"- **月結單數量**: {monthly_data.get('report_count', 0)}")
            content.append(f"- **消費項目數量**: {monthly_data.get('item_count', 0)}")
            content.append(f"- **總金額**: {format_amount(monthly_data.get('total_amount', Decimal(0)), currency=currency)}")
            content.append(f"- **生成時間**: {format_date(datetime.now())}")
            content.append("")
            
            # 月結單列表
            reports = monthly_data.get('reports', [])
            if reports:
                content.append("## 月結單列表")
                content.append("")
                content.append("| 檔案名稱 | 銀行 | 報表日期 | 金額 | 項目數 |")
                content.append("|----------|------|----------|------|--------|")
                
                for report in reports:
                    content.append(
                        f"| {report.get('file_name', 'N/A')} | "
                        f"{report.get('bank_name', 'N/A')} | "
                        f"{report.get('report_date', 'N/A')} | "
                        f"{format_amount(report.get('total_amount', Decimal(0)), currency=currency)} | "
                        f"{report.get('item_count', 0)} |"
                    )
                content.append("")
            
            # 消費項目明細
            items = monthly_data.get('items', [])
            if items:
                content.append("## 消費項目明細")
                content.append("")
                content.append("| 日期 | 項目名稱 | 類別 | 金額 | 銀行 |")
                content.append("|------|----------|------|------|------|")
                
                # 按日期排序
                sorted_items = sorted(items, key=lambda x: x.get('item_date', ''), reverse=True)
                
                for item in sorted_items:
                    item_date = item.get('item_date', 'N/A')
                    if item_date and len(item_date) > 10:
                        item_date = item_date[:10]  # 只取日期部分
                    
                    content.append(
                        f"| {item_date} | "
                        f"{item.get('item_name', 'N/A')} | "
                        f"{item.get('category', 'N/A')} | "
                        f"{format_amount(item.get('amount', Decimal(0)), currency=currency)} | "
                        f"{item.get('bank_name', 'N/A')} |"
                    )
                content.append("")
            
            # 類別統計
            category_totals = monthly_data.get('category_totals', {})
            if category_totals:
                content.append("## 類別統計")
                content.append("")
                total_amount = monthly_data.get('total_amount', Decimal(0))
                content.append("| 類別 | 金額 | 占比 |")
                content.append("|------|------|------|")
                
                for category, amount in sorted(category_totals.items(), 
                                              key=lambda x: x[1], reverse=True):
                    percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                    content.append(
                        f"| {category} | {format_amount(amount, currency=currency)} | {percentage:.1f}% |"
                    )
                content.append("")
            
            # 備註
            content.append("## 備註")
            content.append("")
            content.append("- 本報告整合了該月所有月結單的消費數據")
            content.append(f"- 數據來源: {len(reports)} 個月結單文件")
            content.append(f"- 生成時間: {format_date(datetime.now(), '%Y-%m-%d %H:%M:%S')}")
            
            markdown_content = metadata + '\n'.join(content)
            
            # 保存到文件
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                self.logger.info(f"成功生成月份總結 Markdown: {output_path}")
            
            return markdown_content
        
        except Exception as e:
            self.logger.error(f"生成月份總結 Markdown 失敗: {e}")
            return None
    
    def generate_batch_summary(self, reports_data: List[Dict[str, Any]]) -> str:
        """
        生成批量報告的總結
        
        Args:
            reports_data: 報告數據列表
            
        Returns:
            總結 Markdown 內容
        """
        content = []
        content.append("# 批量處理報告")
        content.append("")
        content.append(f"- **處理時間**: {format_date(datetime.now())}")
        content.append(f"- **處理檔案數**: {len(reports_data)}")
        content.append("")
        
        content.append("## 處理詳情")
        content.append("")
        content.append("| 檔案名 | 銀行 | 月份 | 狀態 |")
        content.append("|--------|------|------|------|")
        
        for report in reports_data:
            status = "✓ 成功" if report.get('success', False) else "✗ 失敗"
            content.append(
                f"| {report.get('file_name', 'N/A')} | "
                f"{report.get('bank_name', 'N/A')} | "
                f"{report.get('report_date', 'N/A')} | "
                f"{status} |"
            )
        
        content.append("")
        
        return '\n'.join(content)


# 全局 Markdown 生成器實例
_markdown_generator = None


def get_markdown_generator() -> MarkdownGenerator:
    """獲取全局 Markdown 生成器實例"""
    global _markdown_generator
    if _markdown_generator is None:
        _markdown_generator = MarkdownGenerator()
    return _markdown_generator
