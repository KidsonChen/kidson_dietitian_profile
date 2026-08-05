#!/usr/bin/env python3
"""
upload_to_cloudinary.py — 把 img/ 下所有圖片上傳到 Cloudinary，產生 URL 對照表。

用法：
  1) 設環境變數（建議）：
     export CLOUDINARY_CLOUD_NAME=xxxx
     export CLOUDINARY_API_KEY=xxxx
     export CLOUDINARY_API_SECRET=xxxx
  2) 或在此檔直接填寫下方 CRED 變數（不建議 commit 到 git）
  3) 執行：python upload_to_cloudinary.py

上傳後會產生 cloudinary_manifest.json：
  { "img/photo.jpg": "https://res.cloudinary.com/<cloud>/image/upload/<public_id>", ... }

設計：
  - public_id 用原檔名（不含副檔名），folder = "kidson"（避免與其他專案撞名）
  - 真人照 photo.jpg / leslie.jpg 一同上傳，內容不變
  - 加 f_auto,q_auto 讓 Cloudinary 自動優化格式與畫質
"""
import os
import json
import glob

try:
    import cloudinary
    import cloudinary.uploader
except ImportError:
    raise SystemExit("請先安裝 cloudinary：pip install cloudinary")

CRED = {
    "cloud_name": os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
    "api_key": os.environ.get("CLOUDINARY_API_KEY", ""),
    "api_secret": os.environ.get("CLOUDINARY_API_SECRET", ""),
}

if not all(CRED.values()):
    raise SystemExit("缺少 Cloudinary 憑證：請設 CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET 環境變數")

cloudinary.config(
    cloud_name=CRED["cloud_name"],
    api_key=CRED["api_key"],
    api_secret=CRED["api_secret"],
)

IMG_DIR = "img"
FOLDER = "kidson"

def build_url(public_id):
    return f"https://res.cloudinary.com/{CRED['cloud_name']}/image/upload/f_auto,q_auto/{public_id}"

def main():
    files = sorted(glob.glob(os.path.join(IMG_DIR, "*.jpg")) +
                   glob.glob(os.path.join(IMG_DIR, "*.png")) +
                   glob.glob(os.path.join(IMG_DIR, "*.webp")))
    manifest = {}
    for f in files:
        base = os.path.basename(f)
        name, _ = os.path.splitext(base)
        public_id = f"{FOLDER}/{name}"
        print(f"上傳 {base} -> {public_id} ...", end=" ", flush=True)
        try:
            res = cloudinary.uploader.upload(
                f,
                public_id=public_id,
                overwrite=True,
                folder=FOLDER,
            )
            manifest[f] = build_url(public_id)
            print("OK")
        except Exception as e:
            print(f"失敗: {e}")

    with open("cloudinary_manifest.json", "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=2)
    print(f"\n完成：{len(manifest)} 張上傳，對照表寫入 cloudinary_manifest.json")

if __name__ == "__main__":
    main()
