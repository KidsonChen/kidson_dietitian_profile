from decimal import Decimal

from src.data_processor import DataProcessor


def test_process_items_validates_and_deduplicates():
    processor = DataProcessor()
    items = [
        {'item_name': '早餐', 'amount': '120.00', 'category': '餐飲', 'item_date': '2024-04-01'},
        {'item_name': '早餐', 'amount': '120.00', 'category': '餐飲', 'item_date': '2024-04-01'},
        {'item_name': '捷運', 'amount': '50', 'category': '交通', 'item_date': '2024-04-02'},
    ]

    processed_items, errors = processor.process_items(items)

    assert len(processed_items) == 2
    assert not errors
    totals = processor.calculate_totals(processed_items)
    assert totals['total_amount'] == Decimal('170.00')
    assert totals['item_count'] == 2
    assert totals['average_amount'] == Decimal('85.00')
