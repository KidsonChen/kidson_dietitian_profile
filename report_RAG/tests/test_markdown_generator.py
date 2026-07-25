from pathlib import Path
from decimal import Decimal

from src.markdown_generator import MarkdownGenerator


def test_generate_markdown_creates_file_and_content(tmp_path):
    generator = MarkdownGenerator()
    report_data = {
        'title': '測試月結單',
        'bank_name': '測試銀行',
        'report_date': '2024-04-01',
        'currency': 'NT$',
        'file_name': 'test_statement.pdf',
    }
    items = [
        {
            'item_name': '早餐',
            'item_date': '2024-04-01',
            'amount': Decimal('120.50'),
            'category': '餐飲',
        },
        {
            'item_name': '計程車',
            'item_date': '2024-04-02',
            'amount': Decimal('250.00'),
            'category': '交通',
        },
    ]
    output_path = tmp_path / 'output.md'

    markdown = generator.generate_markdown(report_data, items, output_path=output_path)

    assert markdown is not None
    assert output_path.exists()
    assert '# 測試月結單' in markdown
    assert '| 類別 | 金額 | 占比 |' in markdown
    assert '測試銀行' in markdown
    assert 'NT$120.50' in markdown
    assert '餐飲' in markdown
