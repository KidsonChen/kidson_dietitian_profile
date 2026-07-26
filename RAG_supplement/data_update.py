"""
data_update.py — Data ingestion, cleaning, chunking, embedding, and vector store update
for the Lightweight RAG System (Dietary Supplements knowledge base).
"""

import os
import re
import sys
import logging
import hashlib
import pathlib
import argparse

from dotenv import load_dotenv

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

try:
    import litellm as _litellm_embed
except ImportError:
    _litellm_embed = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
except ImportError:
    _SentenceTransformer = None  # type: ignore

_EMBEDDING_MODEL_CACHE: dict = {}

load_dotenv()

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 2.1  load_config()
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load configuration from environment variables.

    Required variables: EMBEDDING_MODEL, PGVECTOR_CONNECTION_STRING.
    Logs ERROR and exits with code 1 if any required variable is missing.
    """
    required = ["EMBEDDING_MODEL", "PGVECTOR_CONNECTION_STRING"]
    missing = [var for var in required if not os.environ.get(var)]

    if missing:
        logger.error(
            "Missing required environment variables: %s", ", ".join(missing)
        )
        sys.exit(1)

    return {
        "embedding_model": os.environ["EMBEDDING_MODEL"],
        "pgvector_connection_string": os.environ["PGVECTOR_CONNECTION_STRING"],
    }


# ---------------------------------------------------------------------------
# 2.2  read_file()
# ---------------------------------------------------------------------------

def read_file(path: str) -> "str | None":
    """Read a .pdf, .md, or .txt file.

    Returns a list of ``{"page": int, "text": str}`` dicts (one per PDF page;
    .md/.txt files are treated as a single page 1). Returns None for
    unsupported formats or when parsing fails.
    """
    suffix = pathlib.Path(path).suffix.lower()

    if suffix == ".pdf":
        return _read_pdf(path)
    elif suffix in (".md", ".txt"):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return [{"page": 1, "text": fh.read()}]
        except Exception as exc:
            logger.error("Failed to read file %s: %s", path, exc)
            return None
    else:
        logger.warning("Unsupported file format '%s' for file: %s", suffix, path)
        return None


def _read_pdf(path: str) -> "str | None":
    """Extract text from a PDF file, page by page.

    Tries pdfplumber first; falls back to PyPDF2 on failure.
    Returns a list of ``{"page": int, "text": str}`` or None if both fail.
    """
    # Primary: pdfplumber
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(path) as pdf:
            pages = [
                {"page": i + 1, "text": page.extract_text() or ""}
                for i, page in enumerate(pdf.pages)
            ]
        if any(p["text"].strip() for p in pages):
            return pages
        # Empty extraction — fall through to PyPDF2
    except Exception as exc:
        logger.debug("pdfplumber failed for %s (%s), trying PyPDF2", path, exc)

    # Fallback: PyPDF2
    try:
        import PyPDF2  # type: ignore

        with open(path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            pages = [
                {"page": i + 1, "text": reader.pages[i].extract_text() or ""}
                for i in range(len(reader.pages))
            ]
        return pages
    except Exception as exc:
        logger.error("PDF parsing failed for %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# 2.3  clean_text()
# ---------------------------------------------------------------------------

# Pre-compiled patterns for performance and idempotency
_RE_HTML = re.compile(r"<[^>]+>")
_RE_PAGE_MARKER = re.compile(
    r"(?i)\bpage\s+\d+\s+of\s+\d+\b"   # "Page X of Y"
    r"|\bpage\s+\d+\b"                   # "Page X"
    r"|\b\d+\s*/\s*\d+\b"               # "X / Y" (page fraction)
)
_RE_WHITESPACE = re.compile(r"[ \t\r\n]+")


def clean_text(text: str) -> str:
    """Clean raw text by removing HTML tags, page markers, and collapsing whitespace.

    The function is idempotent: clean(clean(x)) == clean(x).
    """
    # 1. Remove HTML tags
    text = _RE_HTML.sub(" ", text)
    # 2. Remove page header/footer markers
    text = _RE_PAGE_MARKER.sub(" ", text)
    # 3. Collapse all whitespace (spaces, tabs, newlines) to a single space
    text = _RE_WHITESPACE.sub(" ", text)
    # 4. Strip leading/trailing whitespace
    text = text.strip()
    return text


# ---------------------------------------------------------------------------
# 2.5  chunk_text()
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    source_file: str = "",
    chunk_size: int = 512,
    overlap: int = 64,
    page: int = 1,
    start_index: int = 0,
) -> "list[dict]":
    """Split text into fixed-length character chunks with overlap.

    Args:
        text:        Input text to split.
        source_file: Source file name stored in each chunk's metadata.
        chunk_size:  Maximum number of characters per chunk.
        overlap:     Number of characters to overlap between consecutive chunks.
        page:        Source page number stored in each chunk (for citation).
        start_index: Starting value for chunk_index (continue across pages).

    Returns:
        List of dicts with keys: ``text``, ``source_file``, ``chunk_index``, ``page``.
        Returns an empty list for empty/whitespace-only input.
    """
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        chunk_size = 512
    if overlap < 0:
        overlap = 0
    # overlap must be strictly less than chunk_size to make forward progress
    if overlap >= chunk_size:
        overlap = chunk_size - 1

    step = chunk_size - overlap
    chunks: list[dict] = []
    start = 0
    index = start_index

    while start < len(text):
        end = start + chunk_size
        chunk_text_content = text[start:end]
        chunks.append(
            {
                "text": chunk_text_content,
                "source_file": source_file,
                "chunk_index": index,
                "page": page,
            }
        )
        index += 1
        start += step

    return chunks


# ---------------------------------------------------------------------------
# 3.1  embed_texts()  — local sentence-transformers
# ---------------------------------------------------------------------------

def embed_texts(texts: list, model_name: str) -> list:
    """Embed a list of strings using local sentence-transformers model.

    Args:
        texts:      List of strings to embed.
        model_name: sentence-transformers model name (e.g. all-MiniLM-L6-v2).

    Returns:
        List of embedding vectors (each vector is a list of floats).
    """
    if _SentenceTransformer is None:
        logger.error("sentence-transformers is not installed. Run: pip install sentence-transformers")
        sys.exit(1)

    # Strip 'huggingface/sentence-transformers/' prefix if present
    clean_name = model_name
    for prefix in ("huggingface/sentence-transformers/", "sentence-transformers/"):
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]
            break

    if clean_name not in _EMBEDDING_MODEL_CACHE:
        try:
            logger.info("Loading embedding model: %s", clean_name)
            _EMBEDDING_MODEL_CACHE[clean_name] = _SentenceTransformer(clean_name)
        except Exception as exc:
            logger.error("Failed to load embedding model '%s': %s", clean_name, exc)
            sys.exit(1)

    model = _EMBEDDING_MODEL_CACHE[clean_name]
    return model.encode(texts, convert_to_numpy=True).tolist()


# ---------------------------------------------------------------------------
# 3.3  init_db()
# ---------------------------------------------------------------------------

def init_db(conn) -> None:
    """Initialise the pgvector schema (tables + index).

    Creates the ``document_chunks`` and ``processed_files`` tables if they do
    not already exist, and sets up the IVFFlat cosine-similarity index.

    Logs ERROR and exits with code 1 on failure.
    """
    ddl = """
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS document_chunks (
        id          SERIAL PRIMARY KEY,
        source_file VARCHAR(512) NOT NULL,
        chunk_index INTEGER NOT NULL,
        page        INTEGER DEFAULT 1,
        text        TEXT NOT NULL,
        embedding   vector(384),
        created_at  TIMESTAMP DEFAULT NOW(),
        UNIQUE (source_file, chunk_index)
    );

    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS page INTEGER DEFAULT 1;

    CREATE INDEX IF NOT EXISTS chunks_embedding_idx
        ON document_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);

    CREATE TABLE IF NOT EXISTS processed_files (
        id           SERIAL PRIMARY KEY,
        file_path    VARCHAR(512) UNIQUE NOT NULL,
        file_hash    VARCHAR(64) NOT NULL,
        processed_at TIMESTAMP DEFAULT NOW()
    );
    """
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    except Exception as exc:
        logger.error("Failed to initialise database schema: %s", exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# 3.4  compute_file_hash() / get_processed_files()
# ---------------------------------------------------------------------------

def compute_file_hash(path: str) -> str:
    """Compute the SHA-256 hash of a file, reading in 8 192-byte chunks.

    Args:
        path: Absolute or relative path to the file.

    Returns:
        Lowercase hex-encoded SHA-256 digest string.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(8192)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def get_processed_files(conn) -> dict:
    """Return a mapping of file_path → file_hash for all processed files.

    Args:
        conn: Active psycopg2 connection.

    Returns:
        Dict ``{file_path: file_hash}`` from the ``processed_files`` table.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT file_path, file_hash FROM processed_files;")
        rows = cur.fetchall()
    return {row[0]: row[1] for row in rows}


# ---------------------------------------------------------------------------
# 3.5  upsert_chunks()
# ---------------------------------------------------------------------------

def upsert_chunks(conn, source_file: str, chunks: list) -> None:
    """Delete existing chunks for *source_file* and insert the new ones.

    Also updates the ``processed_files`` record for the source file.

    Args:
        conn:        Active psycopg2 connection.
        source_file: Relative path of the source file (used as the key).
        chunks:      List of dicts with keys ``text``, ``embedding``,
                     ``chunk_index``, and optionally ``file_hash``.
    """
    file_hash = chunks[0].get("file_hash", "") if chunks else ""

    with conn.cursor() as cur:
        # Remove stale chunks for this source file
        cur.execute(
            "DELETE FROM document_chunks WHERE source_file = %s;",
            (source_file,),
        )

        # Batch-insert new chunks
        insert_sql = """
            INSERT INTO document_chunks (source_file, chunk_index, page, text, embedding)
            VALUES (%(source_file)s, %(chunk_index)s, %(page)s, %(text)s, %(embedding)s)
        """
        records = [
            {
                "source_file": source_file,
                "chunk_index": chunk["chunk_index"],
                "page": chunk.get("page", 1),
                "text": chunk["text"],
                "embedding": chunk["embedding"],
            }
            for chunk in chunks
        ]
        psycopg2.extras.execute_batch(cur, insert_sql, records)

        # Update processed_files record
        cur.execute(
            """
            INSERT INTO processed_files (file_path, file_hash)
            VALUES (%s, %s)
            ON CONFLICT (file_path) DO UPDATE
                SET file_hash    = EXCLUDED.file_hash,
                    processed_at = NOW();
            """,
            (source_file, file_hash),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# 4.1  run_update()
# ---------------------------------------------------------------------------

_SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


def run_update(data_dir: str = "data/raw", rebuild: bool = False) -> None:
    """Main pipeline: scan data_dir, embed files incrementally, update vector store.

    Args:
        data_dir: Path to the directory containing raw source files.
        rebuild:  When True, clears all existing data before processing.
    """
    config = load_config()
    model_name = config["embedding_model"]

    # Connect to pgvector
    try:
        conn = psycopg2.connect(config["pgvector_connection_string"])
    except Exception as exc:
        logger.error("Failed to connect to database: %s", exc)
        sys.exit(1)

    init_db(conn)

    if rebuild:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM document_chunks;")
            cur.execute("DELETE FROM processed_files;")
        conn.commit()

        # Clear processed .txt files
        processed_dir = pathlib.Path("data/processed")
        for txt_file in processed_dir.glob("*.txt"):
            try:
                txt_file.unlink()
            except Exception as exc:
                logger.warning("Could not delete %s: %s", txt_file, exc)

        logger.info("Rebuild mode: cleared all existing data.")

    processed = get_processed_files(conn)

    data_path = pathlib.Path(data_dir)
    source_files = [
        p for p in data_path.rglob("*")
        if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTENSIONS
    ]

    for path in source_files:
        rel_path = str(path.relative_to(data_path))
        filename = path.name

        file_hash = compute_file_hash(str(path))

        if not rebuild and processed.get(rel_path) == file_hash:
            logger.info("Skipping unchanged: %s", filename)
            continue

        pages = read_file(str(path))
        if pages is None:
            continue

        cleaned_pages = [
            {"page": p["page"], "text": clean_text(p["text"])} for p in pages
        ]

        # Save processed text
        processed_dir = pathlib.Path("data/processed")
        processed_dir.mkdir(parents=True, exist_ok=True)
        processed_out = processed_dir / (path.stem + ".txt")
        try:
            processed_out.write_text(
                "\n\n".join(
                    f"[page {p['page']}]\n{p['text']}" for p in cleaned_pages if p["text"]
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Could not write processed file %s: %s", processed_out, exc)

        chunks: list = []
        for p in cleaned_pages:
            page_chunks = chunk_text(
                p["text"],
                source_file=rel_path,
                page=p["page"],
                start_index=len(chunks),
            )
            chunks.extend(page_chunks)
        if not chunks:
            logger.info("Skipping empty content: %s", filename)
            continue

        embeddings = embed_texts([c["text"] for c in chunks], model_name)
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i]
            chunk["file_hash"] = file_hash

        upsert_chunks(conn, rel_path, chunks)
        logger.info("Processed: %s (%d chunks)", filename, len(chunks))

    conn.close()
    logger.info("Update complete.")


# ---------------------------------------------------------------------------
# 4.4  CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update RAG vector store from data/raw/")
    parser.add_argument("--rebuild", action="store_true", help="Clear and rebuild entire index")
    parser.add_argument("--data-dir", default="data/raw", help="Path to raw data directory")
    args = parser.parse_args()
    run_update(data_dir=args.data_dir, rebuild=args.rebuild)
