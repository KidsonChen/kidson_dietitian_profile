#!/usr/bin/env python3
"""
upload_to_cloudinary.py — 把 img/ 下所有圖片上傳到 Cloudinary（unsigned preset），產生 URL 對照表。

用法：
  export CLOUDINARY_CLOUD_NAME=xxxx
  export CLOUDINARY_UPLOAD_PRESET=web_img
  python upload_to_cloudinary.py

unsigned upload 不允許指定 public_id（preset 會自動命名），
所以直接採用上傳回傳的 secure_url 當作真實 URL，並插入 f_auto,q_auto 優化。
manifest 鍵值：本地相對路徑 -> 優化後 Cloudinary URL
"""
import os
import json
import glob

try:
    import cloudinary
    import cloudinary.uploader
except ImportError:
    raise SystemExit("請先安裝 cloudinary：pip install cloudinary")

CLOUD = os.environ.get("CLOUDINARY_CLOUD_NAME", "dv4m2q1i8")
PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "web_img")
IMG_DIR = "img"

def optimize(url):
    # https://res.cloudinary.com/<c>/image/upload/v123/xxx.jpg
    # -> https://res.cloudinary.com/<c>/image/upload/f_auto,q_auto/v123/xxx.jpg
    return url.replace("/image/upload/", "/image/upload/f_auto,q_auto/", 1)

def main():
    files = sorted(glob.glob(os.path.join(IMG_DIR, "*.jpg")) +
                   glob.glob(os.path.join(IMG_DIR, "*.png")) +
                   glob.glob(os.path.join(IMG_DIR, "*.webp")))
    manifest = {}
    for f in files:
        base = os.path.basename(f)
        print(f"上傳 {base} ...", end=" ", flush=True)
        try:
            res = cloudinary.uploader.unsigned_upload(f, PRESET)
            secure = res.get("secure_url")
            if not secure:
                raise RuntimeError("no secure_url in response")
            manifest[f] = optimize(secure)
            print("OK")
        except Exception as e:
            print(f"失敗: {e}")

    with open("cloudinary_manifest.json", "w", encoding="utf-8") as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=2)
    print(f"\n完成：{len(manifest)} 張上傳，對照表寫入 cloudinary_manifest.json")

if __name__ == "__main__":
    main()
