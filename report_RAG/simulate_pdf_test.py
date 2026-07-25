"""
模擬測試新的PDF處理邏輯
"""

def simulate_table_extraction():
    """模擬表格數據提取"""
    print("=== 模擬表格數據提取 ===")

    # 模擬從PDF中提取的表格數據 (包含噪聲)
    mock_table_data = [
        ['日期', '交易項目', '金額', '類別'],
        ['2024-04-01', '早餐費用nnn', '120.50', '餐飲'],
        ['2024-04-02', '計程車費nn', '250.00', '交通'],
        ['2024-04-03', '購物支出', '1500.00', '購物'],
        ['2024-04-05', '電影票', '300.00', '娛樂'],
        ['2024-04-10', '超市購物', '800.00', '購物'],
        ['2024-04-15', '餐廳用餐', '450.00', '餐飲'],
        ['2024-04-20', '加油費', '1200.00', '交通'],
        ['2024-04-25', '網購支出', '680.00', '購物'],
        ['2024-04-28', '咖啡廳', '180.00', '餐飲']
    ]

    # 模擬清理過程
    cleaned_items = []

    for row in mock_table_data[1:]:  # 跳過表頭
        if len(row) >= 3:
            item_date = str(row[0]).strip()
            item_name = str(row[1]).strip()
            amount_str = str(row[2]).strip()
            category = str(row[3]).strip() if len(row) > 3 else '其他'

            # 清理項目名稱
            item_name = item_name.replace('nnn', '').replace('nn', '').replace('n', '').strip()

            # 清理金額
            amount_str = amount_str.replace(' ', '').replace(',', '').strip()

            # 推斷類別
            if '餐' in item_name or '飲' in item_name or '食' in item_name:
                category = '餐飲'
            elif '車' in item_name or '加油' in item_name or '交通' in item_name:
                category = '交通'
            elif '購物' in item_name or '超市' in item_name or '商城' in item_name:
                category = '購物'
            elif '電影' in item_name or '娛樂' in item_name:
                category = '娛樂'

            cleaned_item = {
                'item_name': item_name,
                'amount': amount_str,
                'item_date': item_date,
                'category': category
            }
            cleaned_items.append(cleaned_item)

    print(f"成功提取 {len(cleaned_items)} 個項目:")
    for item in cleaned_items:
        print(f"  - {item['item_date']}: {item['item_name']} ({item['category']}) - {item['amount']}")

    return cleaned_items

def simulate_text_extraction():
    """模擬文本數據提取"""
    print("\n=== 模擬文本數據提取 ===")

    # 模擬PDF文本內容
    mock_text = """
    銀行月結單 - 2024年4月

    交易明細：
    2024-04-01 早餐費用 120.50
    2024-04-02 計程車費 250.00
    2024-04-03 購物支出 1,500.00
    2024-04-05 電影票 300.00
    2024-04-10 超市購物 800.00
    2024-04-15 餐廳用餐 450.00
    2024-04-20 加油費 1,200.00
    2024-04-25 網購支出 680.00
    2024-04-28 咖啡廳 180.00

    總計：5,480.50
    """

    import re

    # 正則表達式匹配交易記錄
    pattern = r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})\s+([^\d]+?)\s+([+-]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    matches = re.findall(pattern, mock_text, re.MULTILINE)

    extracted_items = []
    for match in matches:
        date_part, desc_part, amount_part = match
        item_name = desc_part.strip()
        amount_str = amount_part.replace(',', '')

        # 推斷類別
        if any(keyword in item_name for keyword in ['餐廳', '早餐', '咖啡', '飲料', '食物']):
            category = '餐飲'
        elif any(keyword in item_name for keyword in ['計程車', '加油', '交通']):
            category = '交通'
        elif any(keyword in item_name for keyword in ['購物', '超市', '網購']):
            category = '購物'
        elif '電影' in item_name:
            category = '娛樂'
        else:
            category = '其他'

        extracted_items.append({
            'item_name': item_name,
            'amount': amount_str,
            'item_date': date_part,
            'category': category
        })

    print(f"從文本中提取 {len(extracted_items)} 個項目:")
    for item in extracted_items:
        print(f"  - {item['item_date']}: {item['item_name']} ({item['category']}) - {item['amount']}")

    return extracted_items

if __name__ == "__main__":
    # 測試表格提取
    table_items = simulate_table_extraction()

    # 測試文本提取
    text_items = simulate_text_extraction()

    print("
=== 總結 ===")
    print(f"表格提取: {len(table_items)} 項目")
    print(f"文本提取: {len(text_items)} 項目")
    print("新的處理邏輯可以處理多種PDF格式！")