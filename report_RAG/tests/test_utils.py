from decimal import Decimal

from src.utils import parse_date, parse_amount, format_amount, clean_string, deduplicate_list


def test_parse_date_formats():
    assert parse_date('2024-04-19').year == 2024
    assert parse_date('2024/04/19').month == 4
    assert parse_date('2024-04').day == 1


def test_parse_amount_and_format():
    amount = parse_amount('NT$ 1,234.56')
    assert isinstance(amount, Decimal)
    assert amount == Decimal('1234.56')
    assert format_amount(amount, currency='NT$') == 'NT$1,234.56'


def test_clean_and_deduplicate():
    assert clean_string('  Hello  World  ') == 'Hello World'
    cleaned = deduplicate_list(['a', 'b', 'a', 'c'])
    assert cleaned == ['a', 'b', 'c']
