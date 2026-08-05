#!/usr/bin/env python3
"""
rewrite_img_urls.py — 把 HTML / CSS 裡的本地 img 引用與舊 GCS 外鏈，
統一改成 Cloudinary URL（讀取 cloudinary_manifest.json 對照表）。

用法：
  python rewrite_img_urls.py

行為：
  - 掃描所有 *.html 與 css/*.css
  - 依「檔名」全域匹配（含 img/xxx.jpg、../img/xxx.jpg、GCS 舊外鏈），
    統一替換為 manifest 中的 Cloudinary URL
  - 不動任何非 img 的資源（font/css/js 外鏈保留）
  - 冪等：可重跑
"""
import os
import re
import json
import glob

MANIFEST = "cloudinary_manifest.json"

def load_manifest():
    if not os.path.exists(MANIFEST):
        raise SystemExit(f"找不到 {MANIFEST}，請先跑 upload_to_cloudinary.py")
    with open(MANIFEST, encoding="utf-8") as fp:
        return json.load(fp)

def main():
    manifest = load_manifest()
    # 建立 檔名(含副檔名) -> URL
    name_to_url = {}
    for local, url in manifest.items():
        base = os.path.basename(local)
        name_to_url[base] = url

    files = glob.glob("*.html") + glob.glob("css/*.css")
    total_repl = 0
    for f in files:
        with open(f, encoding="utf-8") as fp:
            txt = fp.read()
        original = txt

        def repl(m):
            nonlocal total_repl
            full = m.group(0)          # 含前後引號的完整匹配
            path = m.group(2)          # 不含引號的圖片路徑
            base = os.path.basename(path.split("?")[0])
            if base in name_to_url:
                total_repl += 1
                return name_to_url[base]
            return full

        # 匹配任何以圖片副檔名結尾的本地路徑（img/ 或 ../img/ 或 ./img/），前後有引號
        txt = re.sub(r"(['\"])((?:(\.\./|\./)*img/)?[A-Za-z0-9_.\-]+\.(?:jpg|jpeg|png|webp))\1", repl, txt)
        # 匹配舊 GCS 外鏈（整條 URL）
        txt = re.sub(r"https?://storage\.(cloud\.google\.com|googleapis\.com)/kidson_dietitian/kidson_dietitian_profile/[^\s'\")]*\.(?:jpg|jpeg|png|webp)(?:\?[^\s'\")]*)?", repl, txt)

        if txt != original:
            with open(f, "w", encoding="utf-8") as fp:
                fp.write(txt)
            print(f"更新 {f}")

    print(f"\n完成：共替換 {total_repl} 處圖片引用")

if __name__ == "__main__":
    main()
