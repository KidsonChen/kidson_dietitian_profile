from decimal import Decimal

from src.statistics import StatisticsAnalyzer


def test_analyze_items_returns_totals_and_percentages():
    analyzer = StatisticsAnalyzer()
    items = [
        {'item_name': '午餐', 'amount': Decimal('150.00'), 'category': '餐飲'},
        {'item_name': '晚餐', 'amount': Decimal('200.00'), 'category': '餐飲'},
        {'item_name': '捷運', 'amount': Decimal('50.00'), 'category': '交通'},
    ]

    result = analyzer.analyze_items(items)

    assert result['total_count'] == 3
    assert result['total_amount'] == Decimal('400.00')
    assert result['statistics']['count'] == 3
    assert '餐飲' in result['categories']
    assert result['categories']['餐飲']['count'] == 2
    assert result['categories']['餐飲']['percentage'] == 87.5
    assert result['categories']['交通']['percentage'] == 12.5


def test_export_statistics_formats_csv_and_json():
    analyzer = StatisticsAnalyzer()
    analysis_result = {
        'categories': {
            '餐飲': {'total': Decimal('350.00'), 'count': 2, 'percentage': 87.5},
            '交通': {'total': Decimal('50.00'), 'count': 1, 'percentage': 12.5},
        }
    }

    csv_output = analyzer.export_statistics(analysis_result, output_format='csv')
    assert 'Category,Amount,Count,Percentage' in csv_output
    assert '餐飲' in csv_output

    json_output = analyzer.export_statistics(analysis_result, output_format='json')
    assert '"餐飲"' in json_output


def test_generate_monthly_report_formats_markdown():
    analyzer = StatisticsAnalyzer()
    
    # Mock database manager
    class MockDBManager:
        def list_monthly_reports(self, bank_name, start_date, end_date):
            return [{'id': 1}]
        
        def get_report_items(self, report_id):
            return [
                {'item_name': '午餐', 'amount': Decimal('150.00'), 'category': '餐飲'},
                {'item_name': '晚餐', 'amount': Decimal('200.00'), 'category': '餐飲'},
            ]
    
    db_manager = MockDBManager()
    
    # Mock monthly data
    analyzer.analyze_monthly = lambda db, bank, period: {
        'total_income': Decimal('1000.00'),
        'total_expense': Decimal('350.00'),
        'balance': Decimal('650.00'),
        'item_count': 2
    }
    
    report = analyzer.generate_monthly_report(db_manager, 'TestBank', '2024-01')
    
    assert '# TestBank - 2024-01 月度統計報告' in report
    assert '總收入' in report
    assert '總支出' in report
    assert '餐飲' in report


def test_generate_quarterly_report_formats_markdown():
    analyzer = StatisticsAnalyzer()
    
    # Mock database manager
    class MockDBManager:
        def list_monthly_reports(self, bank_name, start_date, end_date):
            # Mock data for 2024 Q1 (Jan, Feb, Mar)
            if start_date.startswith('2024-01'):
                return [{'id': 1}]
            elif start_date.startswith('2024-02'):
                return [{'id': 2}]
            elif start_date.startswith('2024-03'):
                return [{'id': 3}]
            return []
        
        def get_report_items(self, report_id):
            # Mock items for each month
            return [
                {'item_name': f'Item {report_id}-1', 'amount': Decimal('1000.00'), 'category': '收入'},
                {'item_name': f'Item {report_id}-2', 'amount': Decimal('-350.00'), 'category': '支出'},
            ]
    
    db_manager = MockDBManager()
    
    report = analyzer.generate_quarterly_report(db_manager, 'TestBank', 2024, 1)
    
    assert '# TestBank - 2024年第1季度統計報告' in report
    assert '季度總結' in report
    assert '月度明細' in report
    assert '總收入' in report
    assert '總支出' in report


def test_generate_yearly_report_formats_markdown():
    analyzer = StatisticsAnalyzer()
    
    # Mock database manager
    class MockDBManager:
        def list_monthly_reports(self, bank_name, start_date, end_date):
            # Mock data for all months in 2024
            month = start_date[:7]  # Extract YYYY-MM
            if month.startswith('2024'):
                month_num = int(month.split('-')[1])
                return [{'id': month_num}]
            return []
        
        def get_report_items(self, report_id):
            # Mock items for each month (3 items per month)
            return [
                {'item_name': f'Income {report_id}', 'amount': Decimal('1000.00'), 'category': '收入'},
                {'item_name': f'Expense {report_id}-1', 'amount': Decimal('-300.00'), 'category': '支出'},
                {'item_name': f'Expense {report_id}-2', 'amount': Decimal('-50.00'), 'category': '支出'},
            ]
    
    db_manager = MockDBManager()
    
    report = analyzer.generate_yearly_report(db_manager, 'TestBank', 2024)
    
    assert '# TestBank - 2024年度統計報告' in report
    assert '年度總結' in report
    assert '季度總結' in report
    assert '總收入' in report
    assert '總支出' in report


def test_generate_comparison_report_formats_markdown():
    analyzer = StatisticsAnalyzer()
    
    # Mock monthly data
    def mock_analyze_monthly(db, bank, period):
        if period == '2024-01':
            return {'total_income': Decimal('1000.00'), 'total_expense': Decimal('350.00')}
        elif period == '2024-02':
            return {'total_income': Decimal('1100.00'), 'total_expense': Decimal('400.00')}
        return {}
    
    analyzer.analyze_monthly = mock_analyze_monthly
    
    report = analyzer.generate_comparison_report(None, 'TestBank', '2024-01', '2024-02', 'monthly')
    
    assert '# TestBank - 2024-01 vs 2024-02 月度比較報告' in report
    assert '比較總結' in report
    assert '趨勢分析' in report
    assert '收入增加' in report
    assert '支出增加' in report