"""
主程序測試
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import argparse
from datetime import datetime

from src.main import (
    setup_app,
    process_single_file,
    batch_process_files,
    init_db_command,
    main,
    clean_amount_string,
    extract_credit_card_items_from_text,
    parse_credit_card_date,
    extract_items_from_account_statement,
)


class TestSetupApp:
    """應用初始化測試"""

    @patch('src.main.get_config')
    def test_setup_app_success(self, mock_get_config):
        """測試應用初始化成功"""
        mock_config = MagicMock()
        mock_config.ensure_directories_exist.return_value = None
        mock_config.validate.return_value = True
        mock_config.APP_NAME = 'Test App'
        mock_config.APP_VERSION = '1.0.0'
        mock_get_config.return_value = mock_config

        with patch('src.main.Logger') as mock_logger:
            result = setup_app()
            assert result is True
            mock_logger.setup.assert_called_once()

    @patch('src.main.get_config')
    def test_setup_app_config_validation_failure(self, mock_get_config):
        """測試配置驗證失敗"""
        mock_config = MagicMock()
        mock_config.validate.return_value = False
        mock_get_config.return_value = mock_config

        result = setup_app()
        assert result is False


class TestProcessSingleFile:
    """單文件處理測試"""

    @patch('src.main.get_config')
    @patch('src.main.get_pdf_processor')
    @patch('src.main.get_db_manager')
    @patch('src.main.check_database')
    @patch('src.main.init_database')
    def test_process_single_file_success(self, mock_init_db, mock_check_db,
                                       mock_get_db_manager, mock_get_pdf_processor,
                                       mock_get_config, tmp_path):
        """測試單文件處理成功"""
        # 設置模擬對象
        mock_config = MagicMock()
        mock_config.BANKS = ['test_bank']
        mock_config.DATABASE_PATH = str(tmp_path / 'test.db')
        mock_config.MARKDOWN_DIR = tmp_path / 'md'
        mock_get_config.return_value = mock_config

        mock_pdf_proc = MagicMock()
        mock_pdf_proc.process_pdf.return_value = {
            'success': True, 
            'page_count': 2,
            'all_text': 'sample text content',
            'all_tables': {}
        }
        mock_get_pdf_processor.return_value = mock_pdf_proc

        mock_check_db.return_value = True

        mock_db_manager = MagicMock()
        mock_db_manager.insert_monthly_report.return_value = 1
        mock_get_db_manager.return_value = mock_db_manager

        # 創建臨時文件
        test_file = tmp_path / 'test.pdf'
        test_file.write_text('dummy pdf content')

        result = process_single_file(str(test_file))
        assert result is True

    @patch('src.main.get_config')
    def test_process_single_file_not_exists(self, mock_get_config):
        """測試文件不存在的情況"""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        result = process_single_file('/nonexistent/file.pdf')
        assert result is False


class TestCreditCardExtraction:
    @pytest.mark.parametrize(
        'raw,expected',
        [
            ('3,739.93CR', '-3739.93'),
            ('HKD6,293.50', '6293.50'),
            ('(1,234.56)', '-1234.56'),
        ]
    )
    def test_clean_amount_string_handles_credit_card_amounts(self, raw, expected):
        assert clean_amount_string(raw) == expected

    def test_extract_credit_card_items_from_text(self):
        sample_text = (
            'Post date Trans date Description of transaction Amount (HKD)\n'
            '09FEB 06FEB 759 STORE 15987 HONG KONG HK 100.00\n'
            'APPLE PAY-MOBILE:2489\n'
            '09FEB 08FEB FUSION 112TWE2 TAI PO HK 75.00\n'
        )
        report_date = datetime(2026, 3, 9)
        items = extract_credit_card_items_from_text(sample_text, report_date)

        assert len(items) == 2
        assert items[0]['item_name'].startswith('759 STORE 15987 HONG KONG HK')
        assert 'APPLE PAY' in items[0]['item_name']
        assert items[0]['amount'] == '100.00'
        assert items[0]['item_date'] == '2026-02-06'
        assert items[1]['item_name'].startswith('FUSION 112TWE2 TAI PO HK')
        assert items[1]['amount'] == '75.00'

    def test_extract_items_from_account_statement_skips_balance(self):
        sample_text = (
            'HSBC One Account Transaction History\n'
            'HKD Savings\n'
            'Date Transaction Details Deposit Withdrawal Balance\n'
            '6 Feb B/F BALANCE 17,351.13\n'
            '9 Feb 4201-8400-1990-4414\n'
            'N20811034189(08FEB26) 3,739.93\n'
            'GXC024LL4A\n'
            'GLB TRF USD509.59 07FEB 4,000.00 9,611.20\n'
            '5 Mar BAGUIO W M & R LTD\n'
            'SALARY 16,222.10 16,942.50\n'
        )
        report_date = datetime(2026, 3, 6)
        items = extract_items_from_account_statement({}, sample_text, report_date)

        assert len(items) == 2
        assert items[0]['item_date'] == '2026-02-09'
        assert items[0]['amount'] == '4,000.00'
        assert items[0]['category'] == '轉帳'
        assert items[1]['item_date'] == '2026-03-05'
        assert items[1]['amount'] == '16,222.10'
        assert items[1]['category'] == '收入'


class TestBatchProcessFiles:
    """批量處理測試"""

    @patch('src.main.get_config')
    @patch('src.main.process_single_file')
    def test_batch_process_files_success(self, mock_process_single_file, mock_get_config):
        """測試批量處理成功"""
        mock_config = MagicMock()
        mock_config.RAW_DATA_DIR = Path('/tmp/raw')
        mock_config.ACCOUNT_DATA_DIR = Path('/tmp/raw/account')
        mock_config.CREDIT_CARD_DATA_DIR = Path('/tmp/raw/credit card')
        mock_get_config.return_value = mock_config

        # 模擬沒有子目錄的情況
        mock_process_single_file.return_value = True

        with patch('src.main.Path') as mock_path:
            # 模擬目錄存在
            mock_path.return_value.exists.return_value = True
            # 模擬沒有子目錄
            mock_path.return_value.glob.return_value = [
                Path('/tmp/raw/file1.pdf'),
                Path('/tmp/raw/file2.pdf')
            ]

            result = batch_process_files('/tmp/raw')
            assert result is True
            # 應該調用兩次process_single_file
            assert mock_process_single_file.call_count == 2

    @patch('src.main.get_config')
    def test_batch_process_files_directory_not_exists(self, mock_get_config):
        """測試目錄不存在的情況"""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        result = batch_process_files('/nonexistent/directory')
        assert result is False


class TestInitDbCommand:
    """數據庫初始化測試"""

    @patch('src.main.get_config')
    @patch('src.main.init_database')
    @patch('src.main.reset_database')
    def test_init_db_command_success(self, mock_reset_db, mock_init_db, mock_get_config):
        """測試數據庫初始化成功"""
        mock_config = MagicMock()
        mock_config.DATABASE_PATH = '/tmp/test.db'
        mock_get_config.return_value = mock_config

        mock_init_db.return_value = True

        result = init_db_command()
        assert result is True
        mock_init_db.assert_called_once_with('/tmp/test.db')

    @patch('src.main.get_config')
    @patch('src.main.init_database')
    @patch('src.main.reset_database')
    def test_init_db_command_with_reset(self, mock_reset_db, mock_init_db, mock_get_config):
        """測試數據庫重置"""
        mock_config = MagicMock()
        mock_config.DATABASE_PATH = '/tmp/test.db'
        mock_get_config.return_value = mock_config

        mock_reset_db.return_value = True
        mock_init_db.return_value = True

        result = init_db_command(reset=True)
        assert result is True
        mock_reset_db.assert_called_once()


class TestMainFunction:
    """主函數測試"""

    @patch('src.main.setup_app')
    @patch('src.main.init_db_command')
    @patch('src.main.batch_process_files')
    def test_main_init_db(self, mock_batch_process, mock_init_db, mock_setup_app):
        """測試主函數初始化數據庫"""
        mock_setup_app.return_value = True
        mock_init_db.return_value = True

        with patch('sys.argv', ['main.py', '--init-db']):
            result = main()
            assert result == 0
            mock_init_db.assert_called_once_with(reset=False)

    @patch('src.main.setup_app')
    @patch('src.main.process_single_file')
    def test_main_process_file(self, mock_process_file, mock_setup_app):
        """測試主函數處理單個文件"""
        mock_setup_app.return_value = True
        mock_process_file.return_value = True

        with patch('sys.argv', ['main.py', '--file', 'test.pdf']):
            result = main()
            assert result == 0
            mock_process_file.assert_called_once_with('test.pdf', None)

    @patch('src.main.setup_app')
    @patch('src.main.batch_process_files')
    @patch('src.main.init_db_command')
    def test_main_default_behavior(self, mock_init_db, mock_batch_process, mock_setup_app):
        """測試主函數默認行為"""
        mock_setup_app.return_value = True
        mock_init_db.return_value = True
        mock_batch_process.return_value = True

        with patch('sys.argv', ['main.py']):
            result = main()
            assert result == 0
            mock_init_db.assert_called_once_with()  # 默認參數 reset=False
            mock_batch_process.assert_called_once_with(bank_name=None)

    @patch('src.main.setup_app')
    def test_main_setup_failure(self, mock_setup_app):
        """測試應用初始化失敗"""
        mock_setup_app.return_value = False

        result = main()
        assert result == 1