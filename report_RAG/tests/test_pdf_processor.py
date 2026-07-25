from pathlib import Path
from PyPDF2 import PdfWriter

from src.pdf_processor import PDFProcessor


def create_blank_pdf(path: Path):
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with open(path, 'wb') as f:
        writer.write(f)


def test_process_blank_pdf(tmp_path):
    pdf_path = tmp_path / 'blank.pdf'
    create_blank_pdf(pdf_path)

    processor = PDFProcessor()
    result = processor.process_pdf(pdf_path)
    assert result['success'] is True
    assert result['page_count'] == 1
    assert 'all_text' in result
    assert result['all_tables'] == {}
    assert result['file_name'] == 'blank.pdf'
