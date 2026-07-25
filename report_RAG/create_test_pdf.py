"""
創建測試PDF文件的腳本
用於測試月結單處理系統
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from pathlib import Path
import sys

def create_test_pdf(output_path: str):
    """
    創建測試PDF文件

    Args:
        output_path: 輸出文件路徑
    """
    # 創建PDF文檔
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # 標題
    title = Paragraph("測試銀行月結單", styles['Title'])
    story.append(title)

    # 基本信息
    info_text = """
    <b>銀行名稱:</b> 測試銀行<br/>
    <b>結算月份:</b> 2024年4月<br/>
    <b>帳戶號碼:</b> 1234-5678-9012<br/>
    <b>貨幣:</b> TWD<br/>
    <b>生成日期:</b> 2024-04-30<br/>
    """
    story.append(Paragraph(info_text, styles['Normal']))

    # 交易明細表格
    data = [
        ['日期', '交易項目', '金額', '類別'],  # 表頭
        ['2024-04-01', '薪資收入', '35000.00', '收入'],
        ['2024-04-02', '早餐費用', '-120.50', '餐飲'],
        ['2024-04-03', '計程車費', '-250.00', '交通'],
        ['2024-04-05', '購物支出', '-1500.00', '購物'],
        ['2024-04-08', '電費', '-2500.00', '支出'],
        ['2024-04-10', '超市購物', '-800.00', '購物'],
        ['2024-04-15', '餐廳用餐', '-450.00', '餐飲'],
        ['2024-04-18', '轉帳收入', '5000.00', '收入'],
        ['2024-04-20', '加油費', '-1200.00', '交通'],
        ['2024-04-25', '網購支出', '-680.00', '購物'],
        ['2024-04-28', '利息收入', '230.00', '收入'],
    ]

    # 創建表格
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(table)

    # 總計信息
    total_text = """
    <br/><br/>
    <b>總收入:</b> NT$ 40,230.00<br/>
    <b>總支出:</b> NT$ 7,400.50<br/>
    <b>淨額:</b> NT$ 32,829.50<br/>
    <b>交易筆數:</b> 11 筆<br/>
    <b>平均每筆:</b> NT$ 2,984.50<br/>
    """
    story.append(Paragraph(total_text, styles['Normal']))

    # 生成PDF
    doc.build(story)
    print(f"測試PDF已創建: {output_path}")

if __name__ == "__main__":
    # 安裝reportlab如果沒有安裝
    try:
        import reportlab
    except ImportError:
        print("安裝reportlab...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])

    # 創建測試PDF
    output_dir = Path("raw_data")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "test_statement.pdf"

    create_test_pdf(str(output_path))