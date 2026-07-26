"""
download_papers.py — 從保健食品文獻報告的引用清單，批次下載可免費取得的全文到 data/raw/

優先順序（對 RAG 最友善，免登入、無 PDF 抽取雜訊）：
  1. PMC OA XML 全文（eutils efetch） → 存 .xml， ingest 前轉 .txt
  2. 直連 PDF（Frontiers / SemanticScholar）→ 存 .pdf

用法：
  python download_papers.py
  python download_papers.py --check     # 只列出，不下載
  python download_papers.py --to-txt      # 把已下載的 PMC xml 轉成 .txt 全文

特性：跳過已存在的檔案（斷點續傳）；每個目標含最小大小檢查，太小視為落敗。
"""

import os
import re
import sys
import time
import pathlib
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

OUT_DIR = pathlib.Path(__file__).resolve().parent / "data" / "raw"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# (safe_name_no_ext, kind, locator, min_kb)
#   kind = "pmc_xml" -> locator = PMC id
#   kind = "pdf"     -> locator = URL
# 僅收確定可免費取得者；MDPI / ResearchGate / Taylor&Francis 等需登入或 403 者已剔除
TARGETS = [
    # --- PMC OA XML 全文（最適 RAG，純文字無雜訊） ---
    ("vitd_omega3_autoimmune_VITAL", "pmc_xml", "PMC7240168", 60),
    ("vitd_cardiac_events_meta", "pmc_xml", "PMC9739673", 150),
    ("aquamin_colonic_Aslam2021", "pmc_xml", "PMC7964319", 400),
    ("glutathione_liposomal", "pmc_xml", "PMC6389332", 60),
    ("fucoidan_antiangiogenic", "pmc_xml", "PMC10223425", 400),
    ("vitd_uti", "pmc_xml", "PMC7569126", 200),
    ("yeast_selenium_biofort", "pmc_xml", "PMC13157416", 200),
    ("zinc_bioavailability", "pmc_xml", "PMC11677333", 200),
    ("iron_microencapsulated", "pmc_xml", "PMC12790682", 200),
    ("omega3_cv_meta", "pmc_xml", "PMC8413259", 400),
    ("uc2_knee_OA", "pmc_xml", "PMC13077837", 200),
    # --- 直連 PDF（確定可下載） ---
    ("nattokinase_redyeastrice_Frontiers2024", "pdf",
     "https://www.frontiersin.org/journals/nutrition/articles/10.3389/fnut.2024.1380727/pdf", 400),
    ("epa_pci_reduceit_SemanticScholar", "pdf",
     "https://pdfs.semanticscholar.org/f6ea/89338bc07b94611234412a856418263c3db7.pdf", 300),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def download_pmc_xml(pmc_id, dest, min_kb):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pmc&id={pmc_id.replace('PMC','')}&rettype=xml")
    try:
        data = fetch(url)
    except Exception as e:
        return False, f"HTTP {e}"
    if len(data) < min_kb * 1024:
        return False, f"too small ({len(data)//1024}KB)"
    dest.write_bytes(data)
    return True, f"{len(data)//1024}KB"


def download_pdf(url, dest, min_kb):
    try:
        data = fetch(url)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)
    if len(data) < min_kb * 1024 or b"%PDF" not in data[:1024]:
        return False, f"too small/not pdf ({len(data)//1024}KB)"
    dest.write_bytes(data)
    return True, f"{len(data)//1024}KB"


def xml_to_text(xml_path):
    """從 PMC NXML 抽取純文字全文（去 tag、去參考區可選保留）。"""
    txt_path = xml_path.with_suffix(".txt")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        return False, f"parse fail: {e}"
    # 抓 <body> 內文字；參考文獻 <ref> 也留著供 RAG 引用識別
    parts = []
    for el in root.iter():
        if el.tag in ("title", "p", "caption", "td", "th", "li", "article-title"):
            if el.text and el.text.strip():
                parts.append(re.sub(r"\s+", " ", el.text.strip()))
            # 含子元素的段落，補抓 tail
            for child in el.itertext():
                t = (child or "").strip()
                if t:
                    parts.append(re.sub(r"\s+", " ", t))
    text = "\n\n".join(p for p in parts if p)
    if not text.strip():
        return False, "empty text"
    txt_path.write_text(text, encoding="utf-8")
    return True, f"{len(text)//1024}KB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--to-txt", action="store_true",
                    help="把已下載的 PMC xml 轉 .txt")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.to_txt:
        n = 0
        for xml in sorted(OUT_DIR.glob("*.xml")):
            ok, info = xml_to_text(xml)
            print(f"{'OK' if ok else 'FAIL'}: {xml.name} ({info})")
            n += ok
        print(f"\n轉檔完成：{n} 篇")
        return

    ok = skip = fail = 0
    for name, kind, loc, min_kb in TARGETS:
        if kind == "pmc_xml":
            dest = OUT_DIR / f"{name}.xml"
            label = f"PMC {loc}"
        else:
            dest = OUT_DIR / f"{name}.pdf"
            label = loc
        if dest.exists() and dest.stat().st_size >= min_kb * 1024:
            print(f"SKIP (exists): {dest.name}")
            skip += 1
            continue
        if args.check:
            print(f"WILL DL: {dest.name}\n   [{kind}] {label}")
            continue
        if kind == "pmc_xml":
            status, info = download_pmc_xml(loc, dest, min_kb)
        else:
            status, info = download_pdf(loc, dest, min_kb)
        if status:
            print(f"OK: {dest.name} ({info})")
            ok += 1
        else:
            print(f"FAIL: {dest.name} — {info}")
            fail += 1
        time.sleep(1.5)

    print(f"\n下載完成：新增 {ok}，跳過 {skip}，失敗 {fail}")
    print("提示：執行 python download_papers.py --to-txt 把 PMC xml 轉成全文 .txt")


if __name__ == "__main__":
    main()
