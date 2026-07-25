"""
月結單處理系統 - 主程序入口
"""

import argparse
import sys
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from .config import get_config, Config
from .utils import Logger
from .pdf_processor import get_pdf_processor
from .data_processor import get_data_processor
from .db_manager import get_db_manager
from .markdown_generator import get_markdown_generator
from database.init_db import init_database, check_database, reset_database


def extract_bank_name_from_text(pdf_text: str, default_bank_name: str = None) -> str:
    """
    從PDF文本中提取銀行名稱
    
    Args:
        pdf_text: PDF文本內容
        default_bank_name: 默認銀行名稱
        
    Returns:
        銀行名稱
    """
    if not pdf_text:
        return default_bank_name or 'unknown_bank'
    
    # 常見銀行名稱模式
    bank_patterns = [
        (r'(?:中國|農業|建設|工商|招商|興業|民生|交通|浦發|華夏|光大|廣發|平安|郵儲)銀行', '中文銀行'),
        (r'Bank of (China|Agriculture|Construction|Communications|Industrial)', 'English Bank'),
        (r'ABC|ICBC|CCB|BOC|CMB|CIB', '銀行縮寫'),
        (r'信用卡|CREDIT CARD', 'credit_card'),
        (r'活期|定期|儲蓄|存款|賬戶|Account|Statement', 'account'),
    ]
    
    text_upper = pdf_text.upper()
    
    for pattern, bank_type in bank_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            if bank_type == '信用卡':
                return 'credit_card'
            elif bank_type == 'account':
                return 'account'
            elif '銀行' in text_upper or '銀行' in pdf_text:
                # 嘗試提取具體銀行名稱
                match = re.search(r'([\u4e00-\u9fa5]+銀行|[A-Z][a-z]+\s+Bank)', pdf_text)
                if match:
                    return match.group(1).replace('銀行', '').strip()
    
    return default_bank_name or 'unknown_bank'


def classify_transaction_type(item_name: str, amount: str) -> str:
    """
    根據項目名稱和金額分類交易類型
    
    Args:
        item_name: 項目名稱
        amount: 金額
        
    Returns:
        交易類型 (收入、支出、轉帳等)
    """
    item_upper = item_name.upper()
    
    # 收入關鍵詞
    income_keywords = ['工資', '薪水', '獎金', '利息', '分紅', '稅退', '退款', 
                      'SALARY', 'BONUS', 'INTEREST', 'TRANSFER IN', '轉入', '進賬']
    
    # 轉帳關鍵詞
    transfer_keywords = ['轉帳', '轉移', '存款', '取款', 'TRANSFER', 'PAYMENT', 
                        '還款', '支付', 'WITHDRAWAL']
    
    # 支出關鍵詞
    expense_keywords = ['購物', '消費', '餐飲', '交通', '娛樂', '電費', '水費', 
                       '網費', '保險', '信用卡', 'SHOPPING', 'PURCHASE', 'EXPENSE']
    
    for keyword in income_keywords:
        if keyword in item_upper:
            return '收入'
    
    for keyword in transfer_keywords:
        if keyword in item_upper:
            return '轉帳'
    
    for keyword in expense_keywords:
        if keyword in item_upper:
            return '支出'
    
    # 根據金額符號判斷
    try:
        amount_num = float(amount.replace(',', '').replace('NT$', '').replace('CNY', ''))
        if amount_num > 0:
            return '收入'
        else:
            return '支出'
    except:
        pass
    
    return '其他'


def setup_app():
    """應用程序初始化"""
    # 加載配置
    config = get_config()
    config.ensure_directories_exist()
    
    # 驗證配置
    if not config.validate():
        return False
    
    # 初始化日誌
    logger = Logger.setup()
    logger.info(f"應用啟動: {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"配置: {config}")
    
    return True


def process_single_file(file_path: str, bank_name: str = None):
    """
    處理單個 PDF 文件
    
    Args:
        file_path: PDF 文件路徑
        bank_name: 銀行名稱 (可選，如果 None 會從文件路徑推斷)
    """
    logger = Logger.get_logger(__name__)
    config = get_config()
    
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        return False
    
    # 處理 PDF
    logger.info(f"開始處理: {file_path.name}")
    pdf_processor = get_pdf_processor()
    pdf_result = pdf_processor.process_pdf(file_path)
    
    if not pdf_result['success']:
        logger.error(f"PDF 處理失敗: {pdf_result['error']}")
        return False
    
    # 推斷銀行名稱
    if bank_name is None:
        # 優先從PDF文本中提取銀行名稱
        extracted_bank = extract_bank_name_from_text(pdf_result['all_text'])
        if extracted_bank and extracted_bank != 'unknown_bank':
            bank_name = extracted_bank
            logger.info(f"從PDF文本中提取銀行名稱: {bank_name}")
        else:
            # 從文件路徑推斷銀行類型
            file_path_str = str(file_path)
            if 'account' in file_path_str.lower():
                bank_name = 'account'
            elif 'credit card' in file_path_str.lower() or 'credit_card' in file_path_str.lower():
                bank_name = 'credit_card'
            else:
                # 從配置推斷
                bank_name = config.BANKS[0] if config.BANKS else 'unknown_bank'
            logger.info(f"從文件路徑推斷銀行名稱: {bank_name}")
    
    logger.info(f"PDF 解析成功: {pdf_result['page_count']} 頁")
    
    # 數據處理 - 從PDF文本中提取結構化數據
    data_processor = get_data_processor()
    
    # 提取金額和日期、幣別
    monetary_data = data_processor.extract_monetary_data(pdf_result['all_text'])
    report_date = data_processor.extract_date_data(pdf_result['all_text'])
    if report_date is None:
        report_date = datetime.now()
    currency = data_processor.extract_currency_data(pdf_result['all_text'])
    
    # 從PDF中提取項目數據 - 多策略方法
    items = []
    
    # 根據銀行類型選擇提取策略
    if bank_name == 'credit_card':
        # 信用卡格式的提取邏輯
        items = extract_items_from_credit_card(pdf_result['all_tables'], pdf_result['all_text'], report_date)
    elif bank_name == 'account':
        # 帳戶對帳單格式的提取邏輯
        items = extract_items_from_account_statement(pdf_result['all_tables'], pdf_result['all_text'], report_date)
    else:
        # 預設的提取邏輯
        # 策略1: 從表格中提取
        if pdf_result['all_tables']:
            logger.info("嘗試從表格中提取數據...")
            table_items = extract_items_from_tables(pdf_result['all_tables'])
            items.extend(table_items)
        
        # 策略2: 如果沒有表格數據，從文本中提取
        if not items and pdf_result['all_text']:
            logger.info("表格提取失敗，嘗試從文本中提取數據...")
            text_items = extract_items_from_text(pdf_result['all_text'])
            items.extend(text_items)
    
    # 策略3: 如果還是沒有數據，使用示例數據
    if not items:
        logger.warning("無法從PDF中提取項目數據，使用示例數據")
        items = create_sample_items(report_date)
    
    # 數據清理和驗證
    processed_items, errors = data_processor.process_items(items)
    if errors:
        logger.warning(f"數據處理錯誤: {errors}")
    
    # 增強項目分類 - 添加交易類型
    for item in processed_items:
        if 'transaction_type' not in item:
            item['transaction_type'] = classify_transaction_type(
                item.get('item_name', ''),
                str(item.get('amount', ''))
            )
    
    # 計算總額
    totals = data_processor.calculate_totals(processed_items)
    
    # 數據庫初始化檢查
    db_manager = get_db_manager()
    if not check_database(config.DATABASE_PATH):
        logger.warning("數據庫檢查失敗，嘗試初始化...")
        if not init_database(config.DATABASE_PATH):
            logger.error("數據庫初始化失敗")
            return False
    
    # 插入數據庫
    report_data = {
        'file_name': file_path.name,
        'bank_name': bank_name,
        'report_date': report_date,
        'total_amount': totals['total_amount'],
        'currency': currency,
        'item_count': len(processed_items),
        'md_file_path': str(config.MARKDOWN_DIR / f"{file_path.stem}.md"),
    }
    
    existing_report = db_manager.get_monthly_report_by_file_name(file_path.name)
    if existing_report:
        report_id = existing_report['id']
        logger.info(f"文件已存在於數據庫，更新記錄: {file_path.name}")
        if not db_manager.update_monthly_report(report_id, report_data):
            logger.error("更新現有月結單失敗")
            return False
        if not db_manager.delete_report_items(report_id):
            logger.error("刪除舊的項目明細失敗")
            return False
    else:
        report_id = db_manager.insert_monthly_report(report_data)
        if report_id is None:
            logger.error("插入數據庫失敗")
            return False
    
    # 插入項目明細
    if processed_items:
        success = db_manager.insert_report_items(report_id, processed_items)
        if not success:
            logger.error("插入項目明細失敗")
            return False
    
    # 生成 Markdown 報告
    markdown_generator = get_markdown_generator()
    markdown_content = markdown_generator.generate_markdown(
        report_data, 
        processed_items, 
        output_path=config.MARKDOWN_DIR / f"{file_path.stem}.md"
    )
    
    if markdown_content:
        logger.info(f"成功生成 Markdown 報告: {config.MARKDOWN_DIR / file_path.stem}.md")
    else:
        logger.error("生成 Markdown 報告失敗")
        return False
    
    logger.info(f"成功處理文件: {file_path.name} (ID: {report_id})")
    return True


def extract_items_from_tables(all_tables: Dict[int, List]) -> List[Dict]:
    """
    從表格數據中提取項目
    
    Args:
        all_tables: 所有表格數據
        
    Returns:
        項目列表
    """
    items = []
    
    for page_num, tables in all_tables.items():
        for table in tables:
            # 跳過表頭行
            for row in table[1:]:
                if len(row) >= 3:  # 至少有日期、項目、金額
                    try:
                        # 清理和驗證數據
                        item_date = str(row[0]).strip() if row[0] else None
                        item_name = str(row[1]).strip() if row[1] else '未知項目'
                        amount_str = str(row[2]).strip() if row[2] else '0'
                        category = str(row[3]).strip() if len(row) > 3 and row[3] else '其他'
                        
                        # 強力清理項目名稱 - 移除常見的PDF提取噪聲
                        item_name = clean_item_name(item_name)
                        
                        # 清理金額字符串
                        amount_str = clean_amount_string(amount_str)
                        
                        # 清理類別
                        category = clean_category(category)
                        
                        # 推斷類別 (如果沒有指定)
                        if category == '其他':
                            category = infer_category(item_name)
                        
                        item = {
                            'item_name': item_name,
                            'amount': amount_str,
                            'item_date': item_date,
                            'category': category
                        }
                        items.append(item)
                    except (IndexError, TypeError, AttributeError) as e:
                        logger.warning(f"處理表格行時出錯: {e}, 行數據: {row}")
                        continue
    
    return items


def is_account_footer_line(line: str) -> bool:
    footer_signals = [
        'Total Relationship Balance',
        'Important Notice',
        'Your average Total Relationship Balance',
        'Effective 1 May',
        'To provide better banking services',
        'The Hongkong and Shanghai Banking Corporation Limited',
        'IPSSTM',
        'Page ',
    ]
    return any(line.startswith(signal) for signal in footer_signals)


def is_account_balance_description(description: str) -> bool:
    desc_lower = description.lower()
    return (
        'balance' in desc_lower
        or 'total relationship balance' in desc_lower
        or 'net position' in desc_lower
        or 'b/f balance' in desc_lower
    )


def clean_account_description(description: str) -> str:
    description = re.sub(r'GXC\d+[A-Z]+\s*', '', description).strip()
    description = re.sub(r'N\d+\([^)]+\)\s*', '', description).strip()
    description = re.sub(r'HC\d+\s*', '', description).strip()
    description = re.sub(r'\b\d{2}[A-Z]{3}\b', '', description).strip()
    description = re.sub(r'\s+', ' ', description).strip()
    return description or '交易'


def extract_items_from_account_statement(all_tables: Dict[int, List], all_text: str, report_date: datetime) -> List[Dict]:
    """
    從帳戶對帳單PDF中提取項目 (針對匯豐銀行等格式優化)
    """
    items = []

    # 分割文本為行
    lines = all_text.split('\n')

    # 尋找交易記錄的開始標記
    transaction_started = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 檢查是否是交易記錄的開始
        if 'Date Transaction Details Deposit Withdrawal Balance' in line:
            transaction_started = True
            i += 1
            continue

        if not transaction_started:
            i += 1
            continue

        date_match = re.match(r'^(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+(.+))?', line)

        if date_match:
            day, month, partial_desc = date_match.groups()

            transaction_lines = []
            if partial_desc:
                transaction_lines.append(partial_desc)

            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue

                if re.match(r'^\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', next_line):
                    break

                if is_account_footer_line(next_line):
                    break

                transaction_lines.append(next_line)
                j += 1

            transaction_text = ' '.join(transaction_lines).strip()
            if transaction_text:
                amounts = re.findall(r'([+-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', transaction_text)
                valid_amounts = []
                for amt in amounts:
                    clean_amt = amt.replace(',', '').replace('+', '').replace('-', '')
                    try:
                        num_val = float(clean_amt)
                        if num_val > 10 and num_val < 1000000:
                            valid_amounts.append(amt)
                    except ValueError:
                        continue

                if valid_amounts:
                    amount = valid_amounts[-2] if len(valid_amounts) > 1 else valid_amounts[-1]
                    description = re.sub(r'[+-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?', '', transaction_text).strip()
                    description = clean_account_description(description)

                    if not is_account_balance_description(description):
                        category = '支出'
                        desc_lower = description.lower()
                        if 'salary' in desc_lower:
                            category = '收入'
                        elif 'glb trf' in desc_lower or 'transfer' in desc_lower:
                            category = '轉帳'

                        month_map = {
                            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                            'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                        }
                        month_num = month_map.get(month, '01')
                        year = report_date.year if isinstance(report_date, datetime) else datetime.now().year
                        item_date = f"{year}-{month_num}-{int(day):02d}"

                        item = {
                            'item_name': description,
                            'amount': amount,
                            'item_date': item_date,
                            'category': category
                        }
                        items.append(item)

            i = j
        else:
            i += 1

    return items


def extract_credit_card_items_from_text(all_text: str, report_date: Optional[datetime] = None) -> List[Dict]:
    """
    從信用卡報表文本中提取交易項目
    """
    items = []
    if not all_text:
        return items

    lines = [line.strip() for line in all_text.splitlines() if line.strip()]
    transaction_pattern = re.compile(
        r'^(\d{2}[A-Z]{3})\s+(\d{2}[A-Z]{3})\s+(.+?)\s+([+-]?\d{1,3}(?:,\d{3})*\.\d{2}(?:CR|DR)?)$',
        re.IGNORECASE
    )

    last_item = None
    for line in lines:
        upper_line = line.upper()
        if upper_line.startswith('POST DATE') or upper_line.startswith('TRANS DATE') or upper_line.startswith('DESCRIPTION OF TRANSACTION'):
            continue

        match = transaction_pattern.match(line)
        if match:
            _, trans_date, description, amount_str = match.groups()
            item_name = clean_item_name(description)
            item_date = parse_credit_card_date(trans_date, report_date)
            amount_str = clean_amount_string(amount_str)
            category = '信用卡支出'

            item = {
                'item_name': item_name,
                'amount': amount_str,
                'item_date': item_date,
                'category': category
            }
            items.append(item)
            last_item = item
            continue

        if not last_item:
            continue

        if line.startswith('*'):
            continue

        if re.match(r'^(STATEMENT BALANCE|PREVIOUS BALANCE|TOTAL|REWARDCASH|ACCOUNT NUMBER|CARD TYPE|MINIMUM PAYMENT|OVERDUE|PLEASE|FOR IMPORTANT INFORMATION|NOTE:|IF YOU)', upper_line):
            continue

        # 將後續行追加到前一項目的描述中
        last_item['item_name'] = clean_item_name(f"{last_item['item_name']} {line}")

    return items


def parse_credit_card_date(date_str: str, report_date: Optional[datetime] = None) -> Optional[str]:
    if not date_str:
        return None

    cleaned = date_str.strip().upper().replace('/', '-').replace('.', '-')
    full_match = re.match(r'^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$', cleaned)
    if full_match:
        year, month, day = full_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    short_match = re.match(r'^(\d{1,2})([A-Z]{3})$', cleaned)
    if short_match:
        day, month_abbr = short_match.groups()
        month_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }
        month = month_map.get(month_abbr)
        if month:
            year = report_date.year if isinstance(report_date, datetime) else datetime.now().year
            return f"{year:04d}-{month:02d}-{int(day):02d}"

    return date_str


def extract_items_from_credit_card(all_tables: Dict[int, List], all_text: str, report_date: Optional[datetime] = None) -> List[Dict]:
    """
    從信用卡PDF中提取項目 (針對信用卡格式優化)
    """
    logger = Logger.get_logger(__name__)
    items = []

    if all_text:
        logger.info("嘗試從信用卡報表文本中提取交易...")
        items = extract_credit_card_items_from_text(all_text, report_date)
        if items:
            return items

    for page_num, tables in all_tables.items():
        for table in tables:
            # 跳過表頭行
            for row in table[1:]:
                if len(row) >= 3:
                    try:
                        item_date = str(row[0]).strip() if row[0] else None
                        item_name = str(row[1]).strip() if row[1] else '未知項目'
                        amount_str = str(row[2]).strip() if row[2] else '0'
                        interest = str(row[3]).strip() if len(row) > 3 and row[3] else None

                        item_name = clean_item_name(item_name)
                        amount_str = clean_amount_string(amount_str)

                        category = infer_category(item_name)
                        if category == '支出':
                            category = '信用卡支出'

                        item = {
                            'item_name': item_name,
                            'amount': amount_str,
                            'item_date': item_date,
                            'category': category
                        }

                        if interest and interest != '0':
                            item['description'] = f"利息: {interest}"

                        items.append(item)
                    except (IndexError, TypeError, AttributeError) as e:
                        logger.warning(f"處理信用卡表格行時出錯: {e}, 行數據: {row}")
                        continue

    return items


def extract_items_from_text(all_text: str) -> List[Dict]:
    """
    從文本中提取項目 (當表格提取失敗時的備用方案)
    
    Args:
        all_text: 全部文本內容
        
    Returns:
        項目列表
    """
    items = []
    
    # 使用正則表達式查找可能的交易記錄
    # 匹配日期 + 項目名稱 + 金額的模式
    patterns = [
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})\s+([^\d]+?)\s+([+-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # 日期 + 項目 + 金額
        r'([^\d]+?)\s+(\d{4}[/-]\d{1,2}[/-]\d{1,2})\s+([+-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # 項目 + 日期 + 金額
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, all_text, re.MULTILINE)
        for match in matches:
            try:
                # 解析匹配結果
                if len(match) == 3:
                    date_part, desc_part, amount_part = match
                    
                    # 確定哪個是日期，哪個是描述
                    if re.match(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', date_part):
                        item_date = date_part
                        item_name = desc_part.strip()
                    else:
                        item_date = desc_part
                        item_name = date_part.strip()
                    
                    amount_str = amount_part
                    
                    # 清理數據
                    item_name = clean_item_name(item_name)
                    amount_str = clean_amount_string(amount_str)
                    category = infer_category(item_name)
                    
                    item = {
                        'item_name': item_name,
                        'amount': amount_str,
                        'item_date': item_date,
                        'category': category
                    }
                    items.append(item)
            except Exception as e:
                logger.warning(f"解析文本匹配時出錯: {e}, 匹配: {match}")
                continue
    
    return items


def clean_item_name(name: str) -> str:
    """
    清理項目名稱
    
    Args:
        name: 原始名稱
        
    Returns:
        清理後的名稱
    """
    if not name:
        return '未知項目'
    
    # 移除常見的PDF提取噪聲
    name = name.replace('nnn', '').replace('nn', '').replace('n', '').strip()
    name = re.sub(r'\s+', ' ', name)  # 多個空格替換為單個空格
    
    # 移除特殊字符但保留中文和英文
    name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name)
    
    # 如果清理後還是空的，使用默認名稱
    if not name or name in ['', ' ', '未知']:
        return '未知項目'
    
    return name


def clean_amount_string(amount: str) -> str:
    """
    清理金額字符串
    
    Args:
        amount: 原始金額字符串
        
    Returns:
        清理後的金額字符串
    """
    if not amount:
        return '0'

    amount = str(amount).upper().strip()
    amount = amount.replace('HKD', '').replace('TWD', '').replace('USD', '').replace('$', '')
    amount = amount.replace(' ', '').replace(',', '').strip()

    negative = False
    if amount.endswith('CR') or amount.endswith('DR'):
        negative = amount.endswith('CR')
        amount = amount[:-2].strip()

    if amount.startswith('(') and amount.endswith(')'):
        negative = True
        amount = amount[1:-1]

    if not re.match(r'^[+-]?\d+(?:\.\d{1,2})?$', amount):
        return '0'

    if negative and not amount.startswith('-'):
        amount = '-' + amount

    return amount


def clean_category(category: str) -> str:
    """
    清理類別名稱
    
    Args:
        category: 原始類別
        
    Returns:
        清理後的類別
    """
    if not category:
        return '其他'
    
    # 清理噪聲字符
    category = category.replace('nnn', '').replace('nn', '').replace('n', '').strip()
    
    # 標準化常見類別名稱
    category_mapping = {
        '餐飲': '餐飲',
        '交通': '交通', 
        '購物': '購物',
        '娛樂': '娛樂',
        '收入': '收入',
        '支出': '支出',
        '其他': '其他'
    }
    
    return category_mapping.get(category, category) if category else '其他'


def infer_category(item_name: str) -> str:
    """
    根據項目名稱推斷類別
    
    Args:
        item_name: 項目名稱
        
    Returns:
        推斷的類別
    """
    item_lower = item_name.lower()
    
    # 信用卡相關
    if any(keyword in item_lower for keyword in ['信用卡', 'credit card', '利息', '手續費', '年費', '繳款', '還款']):
        return '信用卡支出'
    
    # 餐飲相關
    if any(keyword in item_lower for keyword in ['餐廳', '早餐', '午餐', '晚餐', '咖啡', '飲料', '食物', '餐費']):
        return '餐飲'
    
    # 交通相關
    if any(keyword in item_lower for keyword in ['計程車', '捷運', '公車', '加油', '停車', '交通']):
        return '交通'
    
    # 購物相關
    if any(keyword in item_lower for keyword in ['購物', '超市', '商店', '商城', '網購']):
        return '購物'
    
    # 娛樂相關
    if any(keyword in item_lower for keyword in ['電影', '遊戲', '娛樂', '休閒']):
        return '娛樂'
    
    # 收入相關
    if any(keyword in item_lower for keyword in ['薪資', '收入', '轉帳', '利息', '獎金']):
        return '收入'
    
    # 支出相關 (默認)
    return '支出'


def create_sample_items(report_date: datetime) -> List[Dict]:
    """
    創建示例項目數據
    
    Args:
        report_date: 報告日期
        
    Returns:
        示例項目列表
    """
    return [
        {
            'item_name': '月結單總計',
            'amount': '0.00',
            'item_date': report_date.strftime('%Y-%m-%d'),
            'category': '總計'
        }
    ]


def batch_process_files(directory: str = None, bank_name: str = None):
    """
    批量處理 PDF 文件
    
    Args:
        directory: PDF 目錄 (默認為配置中的 raw_data)
        bank_name: 銀行名稱
    """
    logger = Logger.get_logger(__name__)
    config = get_config()
    
    if directory is None:
        directory = str(config.RAW_DATA_DIR)
    
    directory = Path(directory)
    if not directory.exists():
        logger.error(f"目錄不存在: {directory}")
        return False
    
    # 檢查是否需要處理子資料夾
    account_dir = config.ACCOUNT_DATA_DIR
    credit_card_dir = config.CREDIT_CARD_DATA_DIR
    
    if account_dir.exists() and credit_card_dir.exists():
        # 分開處理 account 和 credit card 資料夾
        logger.info("檢測到 account 和 credit card 子資料夾，將分開處理")
        return batch_process_multiple_folders()
    
    # 原有的單一目錄處理邏輯
    # 找到所有PDF文件
    pdf_files = list(directory.glob('*.pdf'))
    if not pdf_files:
        logger.warning(f"在 {directory} 中沒有找到PDF文件")
        return False
    
    logger.info(f"找到 {len(pdf_files)} 個PDF文件待處理")
    
    success_count = 0
    for pdf_file in pdf_files:
        try:
            logger.info(f"處理文件: {pdf_file.name}")
            if process_single_file(str(pdf_file), bank_name):
                success_count += 1
                logger.info(f"成功處理: {pdf_file.name}")
            else:
                logger.error(f"處理失敗: {pdf_file.name}")
        except Exception as e:
            logger.error(f"處理文件 {pdf_file.name} 時發生錯誤: {e}")
    
    logger.info(f"批量處理完成: {success_count}/{len(pdf_files)} 個文件成功處理")
    return success_count > 0


def batch_process_multiple_folders():
    """
    批量處理多個資料夾 (account 和 credit card)
    
    Returns:
        處理成功與否
    """
    logger = Logger.get_logger(__name__)
    config = get_config()
    
    folders = [
        ('account', config.ACCOUNT_DATA_DIR, 'account'),
        ('credit card', config.CREDIT_CARD_DATA_DIR, 'credit_card')
    ]
    
    total_success = 0
    total_files = 0
    
    for folder_name, folder_path, bank_type in folders:
        if not folder_path.exists():
            logger.warning(f"{folder_name} 資料夾不存在: {folder_path}")
            continue
        
        # 找到該資料夾中的所有PDF文件
        pdf_files = list(folder_path.glob('*.pdf'))
        if not pdf_files:
            logger.info(f"在 {folder_name} 資料夾中沒有找到PDF文件")
            continue
        
        logger.info(f"在 {folder_name} 資料夾中找到 {len(pdf_files)} 個PDF文件")
        total_files += len(pdf_files)
        
        success_count = 0
        for pdf_file in pdf_files:
            try:
                logger.info(f"處理 {folder_name} 文件: {pdf_file.name}")
                # 使用資料夾名稱作為銀行名稱
                if process_single_file(str(pdf_file), bank_type):
                    success_count += 1
                    logger.info(f"成功處理 {folder_name} 文件: {pdf_file.name}")
                else:
                    logger.error(f"處理 {folder_name} 文件失敗: {pdf_file.name}")
            except Exception as e:
                logger.error(f"處理 {folder_name} 文件 {pdf_file.name} 時發生錯誤: {e}")
        
        total_success += success_count
        logger.info(f"{folder_name} 資料夾處理完成: {success_count}/{len(pdf_files)} 個文件成功")
    
    logger.info(f"全部資料夾批量處理完成: {total_success}/{total_files} 個文件成功處理")
    return total_success > 0


def init_db_command(reset: bool = False):
    """
    初始化數據庫
    
    Args:
        reset: 是否重置數據庫
    """
    logger = Logger.get_logger(__name__)
    config = get_config()
    
    if reset:
        if reset_database(config.DATABASE_PATH, confirm=True):
            logger.info("數據庫已重置")
    
    if init_database(config.DATABASE_PATH):
        logger.info("數據庫初始化成功")
        return True
    else:
        logger.error("數據庫初始化失敗")
        return False


def generate_monthly_report(year_month: str, bank_name: Optional[str] = None):
    """
    生成月份總結報告
    
    Args:
        year_month: 年月 (YYYY-MM 或 YYYY-MM:bank_name)
        bank_name: 銀行名稱 (可選)
        
    Returns:
        生成成功與否
    """
    logger = Logger.get_logger(__name__)
    config = get_config()
    
    # 解析參數
    if ':' in year_month:
        year_month, bank_name = year_month.split(':', 1)
    
    logger.info(f"生成月份報告: {year_month}, 銀行: {bank_name or '全部'}")
    
    # 數據庫初始化檢查
    db_manager = get_db_manager()
    if not check_database(config.DATABASE_PATH):
        logger.error("數據庫未初始化，請先運行 --init-db")
        return False
    
    # 獲取月份數據
    monthly_data = db_manager.get_monthly_summary(year_month, bank_name)
    if not monthly_data:
        logger.error(f"未找到 {year_month} 的數據")
        return False
    
    # 生成 Markdown
    markdown_generator = get_markdown_generator()
    output_path = config.MARKDOWN_DIR / f"monthly_{year_month}"
    if bank_name:
        output_path = output_path / f"{bank_name}_{year_month}.md"
    else:
        output_path = output_path / f"all_banks_{year_month}.md"
    
    markdown_content = markdown_generator.generate_monthly_summary(
        monthly_data, 
        output_path=output_path
    )
    
    if markdown_content:
        logger.info(f"成功生成月份總結報告: {output_path}")
        return True
    else:
        logger.error("生成月份總結報告失敗")
        return False


def main():
    """主程序入口"""
    # 應用初始化
    if not setup_app():
        print("應用初始化失敗", file=sys.stderr)
        return 1
    
    # 命令行參數解析
    parser = argparse.ArgumentParser(
        description='月結單自動處理系統',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python -m src.main --file raw_data/202404.pdf
  python -m src.main --batch
  python -m src.main --init-db
  python -m src.main --report 2024-04
  python -m src.main --report 2024-04:中國信託
        '''
    )
    
    parser.add_argument(
        '--file', 
        type=str,
        help='處理單個 PDF 文件'
    )
    parser.add_argument(
        '--batch',
        action='store_true',
        help='批量處理 raw_data 目錄中的所有 PDF'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='初始化數據庫'
    )
    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='重置數據庫 (刪除所有數據)'
    )
    parser.add_argument(
        '--bank',
        type=str,
        default=None,
        help='指定銀行名稱'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='啟用詳細日誌'
    )
    parser.add_argument(
        '--report',
        type=str,
        help='生成報告 (monthly:月份總結, 格式: YYYY-MM 或 YYYY-MM:bank_name)'
    )
    
    args = parser.parse_args()
    logger = Logger.get_logger(__name__)
    
    # 執行相應命令
    try:
        if args.init_db or args.reset_db:
            success = init_db_command(reset=args.reset_db)
            return 0 if success else 1
        
        elif args.file:
            file_path = Path(args.file)
            if file_path.is_dir():
                logger.info(f"--file 指定的是資料夾，轉為批量處理: {file_path}")
                success = batch_process_files(directory=str(file_path), bank_name=args.bank)
            else:
                success = process_single_file(args.file, args.bank)
            return 0 if success else 1
        
        elif args.batch:
            success = batch_process_files(bank_name=args.bank)
            return 0 if success else 1
        
        elif args.report:
            success = generate_monthly_report(args.report, args.bank)
            return 0 if success else 1
        
        else:
            # 默認行為: 初始化並執行批量處理
            logger.info("未指定命令，執行默認操作...")
            if init_db_command():
                batch_process_files(bank_name=args.bank)
                return 0
            return 1
    
    except KeyboardInterrupt:
        logger.info("程序被用戶中斷")
        return 130
    except Exception as e:
        logger.error(f"未預期的錯誤: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
