import sqlite3
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from src.db_manager import DatabaseManager
from database.init_db import init_database


def test_init_database_creates_tables(tmp_path):
    db_path = tmp_path / 'report_rag.db'
    schema_path = Path(__file__).resolve().parent.parent / 'database' / 'schema.sql'
    assert init_database(str(db_path), str(schema_path)) is True
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    names = {row[0] for row in cursor.fetchall()}
    assert 'monthly_reports' in names
    assert 'report_items' in names
    assert 'statistics' in names
    conn.close()


def test_insert_and_query_monthly_report(tmp_path):
    db_path = tmp_path / 'report_rag.db'
    schema_path = Path(__file__).resolve().parent.parent / 'database' / 'schema.sql'
    assert init_database(str(db_path), str(schema_path)) is True

    manager = DatabaseManager(str(db_path))
    report_id = manager.insert_monthly_report({
        'file_name': 'test_statement.pdf',
        'bank_name': 'bank_a',
        'report_date': datetime(2024, 4, 1),
        'total_amount': Decimal('1000.00'),
        'currency': 'TWD',
        'item_count': 1,
        'md_file_path': 'md/bank_a/202404_statement.md',
    })
    assert report_id is not None
    report = manager.get_monthly_report(report_id)
    assert report is not None
    assert report['file_name'] == 'test_statement.pdf'
    assert report['bank_name'] == 'bank_a'
    assert float(report['total_amount']) == 1000.0
