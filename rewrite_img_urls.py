#!/usr/bin/env python3
"""
rewrite_img_urls.py — 把 HTML / CSS 裡的本地 img 引用與舊 GCS 外鏈，
統一改成 Cloudinary URL（讀取 cloudinary_manifest.json 對照表）。

用法：
  python rewrite_img_urls.py

行為：
  - 掃描所有 *.html 與 css/*.css
  - 將 'img/xxx.jpg' / 'img/xxx.png' 替換為 manifest 中的 Cloudinary URL
  - 將舊 'https://storage.googleapis.com/kidson_dietitian/.../img/xxx.jpg' 與
        'https://storage.cloud.google.com/kidson_dietitian/.../img/xxx.jpg'
    也替換為對應 Cloudinary URL（依檔名匹配）
  - 不動任何非 img 的資源（font/css/js 外鏈保留）
  - 改前會先 git stash 友好提示；此腳本只做文字替換，可重跑（冪等）
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
    # 建立 檔名 -> URL 的查表（去掉 'img/' 前綴）
    name_to_url = {}
    for local, url in manifest.items():
        base = os.path.basename(local)
        name, _ = os.path.splitext(base)
        name_to_url[base] = url
        name_to_url[name] = url  # 也用無副檔名鍵

    files = glob.glob("*.html") + glob.glob("css/*.css")
    total_repl = 0
    for f in files:
        with open(f, encoding="utf-8") as fp:
            txt = fp.read()
        original = txt

        # 1) 本地 img/xxx 引用
        def repl_local(m):
            nonlocal total_repl
            ref = m.group(1)            # 例如 img/photo.jpg 或 ../img/photo.jpg
            base = os.path.basename(ref)
            if base in name_to_url:
                total_repl += 1
                return m.group(0).replace(ref, name_to_url[base])
            return m.group(0)
        txt = re.sub(r"(['\"])((?:(\.\./)*img/)?img/[A-Za-z0-9_.\-]+\.(?:jpg|jpeg|png|webp))(['\"])", repl_local, txt)

        # 2) 舊 GCS 外鏈（依檔名匹配）
        def repl_gcs(m):
            nonlocal total_repl
            full = m.group(0)
            base = os.path.basename(full.split("?")[0])
            if base in name_to_url:
                total_repl += 1
                return name_to_url[base]
            return full
        txt = re.sub(r"https?://storage\.cloud\.google\.com/kidson_dietitian/kidson_dietitian_profile/img/[A-Za-z0-9_.\-]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s'\"]*)?", repl_gcs, txt)
        txt = re.sub(r"https?://storage\.googleapis\.com/kidson_dietitian/kidson_dietitian_profile/img/[A-Za-z0-9_.\-]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s'\"]*)?", repl_gcs, txt)

        if txt != original:
            with open(f, "w", encoding="utf-8") as fp:
                fp.write(txt)
            print(f"更新 {f}")

    print(f"\n完成：共替換 {total_repl} 處圖片引用")

if __name__ == "__main__":
    main()
