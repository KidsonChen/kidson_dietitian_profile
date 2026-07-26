"""
ingest_to_workers.py — 把 data/raw/ 的文獻切塊後上傳到 Cloudflare Workers RAG API
（重用 data_update.py 的逐頁 PDF 解析 + 清洗 + 切塊，含頁碼 metadata）

用法：
  set WORKER_URL=https://kidson-supplement-rag.<subdomain>.workers.dev
  set INGEST_KEY=<你的 ingest key>
  python ingest_to_workers.py [--data-dir data/raw]
"""

import os
import time
import sys
import json
import pathlib
import argparse
import urllib.request
import urllib.error

from data_update import read_file, clean_text, chunk_text

BATCH_SIZE = 25   # docs per request (worker cap = 100; smaller = gentler on AI rate limits)
MAX_RETRIES = 4
DONE_MANIFEST = pathlib.Path(".ingest_done.json")


def post_json(url: str, payload: dict, ingest_key: str) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Ingest-Key": ingest_key,
                "User-Agent": "Mozilla/5.0 (kidson-rag-ingest)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                err_body = ""
            # retry on transient server-side errors / rate limits
            if exc.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = 5 * attempt
                print(f"  HTTP {exc.code} ({err_body}), retry {attempt}/{MAX_RETRIES} in {wait}s...")
                time.sleep(wait)
                last_err = exc
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < MAX_RETRIES:
                wait = 5 * attempt
                print(f"  Network error ({exc}), retry {attempt}/{MAX_RETRIES} in {wait}s...")
                time.sleep(wait)
                last_err = exc
                continue
            raise
    raise RuntimeError(f"upload failed after {MAX_RETRIES} retries: {last_err}")


def load_done() -> set:
    if DONE_MANIFEST.exists():
        try:
            return set(json.loads(DONE_MANIFEST.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def mark_done(done: set, rel_path: str) -> None:
    done.add(rel_path)
    DONE_MANIFEST.write_text(json.dumps(sorted(done), ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/raw")
    args = parser.parse_args()

    worker_url = os.environ.get("WORKER_URL", "").rstrip("/")
    ingest_key = os.environ.get("INGEST_KEY", "")
    if not worker_url:
        print("ERROR: 請設定 WORKER_URL 環境變數")
        sys.exit(1)

    endpoint = f"{worker_url}/api/ingest"
    data_path = pathlib.Path(args.data_dir)
    done = load_done()
    files = [
        p for p in sorted(data_path.rglob("*"))
        if p.is_file() and p.suffix.lower() in {".pdf", ".md", ".txt"}
    ]

    total = 0
    for path in files:
        rel_path = str(path.relative_to(data_path))
        if rel_path in done:
            print(f"SKIP (already uploaded): {rel_path}")
            continue
        pages = read_file(str(path))
        if pages is None:
            print(f"SKIP (unreadable): {rel_path}")
            continue

        chunks: list = []
        for p in pages:
            cleaned = clean_text(p["text"])
            chunks.extend(
                chunk_text(cleaned, source_file=rel_path, page=p["page"],
                           start_index=len(chunks))
            )
        if not chunks:
            print(f"SKIP (empty): {rel_path}")
            continue

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            docs = [
                {
                    "source_file": c["source_file"],
                    "page": c["page"],
                    "chunk_index": c["chunk_index"],
                    "text": c["text"],
                }
                for c in batch
            ]
            result = post_json(endpoint, {"docs": docs}, ingest_key)
            if not result.get("ok"):
                print(f"ERROR uploading {rel_path}: {result}")
                sys.exit(1)
            time.sleep(1)  # gentle pacing for Workers AI rate limits
        total += len(chunks)
        mark_done(done, rel_path)
        print(f"OK: {rel_path} ({len(chunks)} chunks)")

    print(f"\n完成：共上傳 {total} 個 chunks 到 {worker_url}")


if __name__ == "__main__":
    main()
