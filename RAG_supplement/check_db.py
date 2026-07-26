"""Quick check: how many chunks are in the vector store."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import psycopg2
except ImportError:
    print("psycopg2 not installed")
    sys.exit(1)

conn_str = os.environ.get("PGVECTOR_CONNECTION_STRING")
if not conn_str:
    print("PGVECTOR_CONNECTION_STRING not set")
    sys.exit(1)

try:
    conn = psycopg2.connect(conn_str)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM document_chunks;")
        chunk_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM processed_files;")
        file_count = cur.fetchone()[0]
        cur.execute("SELECT source_file, COUNT(*) FROM document_chunks GROUP BY source_file ORDER BY source_file LIMIT 10;")
        samples = cur.fetchall()
    conn.close()
    print(f"document_chunks: {chunk_count} rows")
    print(f"processed_files: {file_count} rows")
    print("\nSample files:")
    for row in samples:
        print(f"  {row[0]}: {row[1]} chunks")
except Exception as e:
    print(f"DB error: {e}")
