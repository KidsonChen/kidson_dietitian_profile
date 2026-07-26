"""
rag_query.py — RAG query interface for the Lightweight RAG System
(Dietary Supplements knowledge base).

Provides core query functions:
  - embed_query:      embed a single query string
  - similarity_search: retrieve top-k similar chunks from pgvector
  - assemble_prompt:  build LiteLLM messages with context and history
  - format_answer:    append citation list to LLM response
"""

import os
import sys
import logging
import argparse

from dotenv import load_dotenv

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore

try:
    import litellm
except ImportError:
    litellm = None  # type: ignore

_EMBEDDING_MODEL_CACHE: dict = {}

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None  # type: ignore

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
# Module-level embedding model cache
# ---------------------------------------------------------------------------
_EMBEDDING_MODEL_CACHE: dict = {}

# ---------------------------------------------------------------------------
# System prompt for the dietary supplements domain
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """你是一位保健食品專業顧問，專門根據學術文獻回答關於保健食品成分功效與劑量建議的問題。
請根據以下提供的文獻片段回答問題，並：
1. 明確說明每個功效或劑量建議所對應的研究族群（Study Population）
2. 若文獻未指定研究族群，請標注「未指定研究族群」
3. 回答結尾列出引用來源（[來源: 檔案名稱, p.頁碼]）
4. 若提供的文獻片段與問題無關，請告知使用者知識庫中無相關資訊
5. 僅能引用文獻片段中實際出現的數據與劑量，禁止外推或自行推估劑量建議"""


# ---------------------------------------------------------------------------
# 6.1  embed_query()  — local sentence-transformers
# ---------------------------------------------------------------------------

def embed_query(query: str, model_name: str) -> list:
    """Embed a single query string using local sentence-transformers model.

    Args:
        query:      The query string to embed.
        model_name: sentence-transformers model name.

    Returns:
        Embedding vector as a list of floats.
    """
    if SentenceTransformer is None:
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
            _EMBEDDING_MODEL_CACHE[clean_name] = SentenceTransformer(clean_name)
        except Exception as exc:
            logger.error("Failed to load embedding model '%s': %s", clean_name, exc)
            sys.exit(1)

    model = _EMBEDDING_MODEL_CACHE[clean_name]
    return model.encode([query], convert_to_numpy=True).tolist()[0]


# ---------------------------------------------------------------------------
# 6.2  similarity_search()
# ---------------------------------------------------------------------------

def similarity_search(conn, query_vector: list, top_k: int = 5) -> list:
    """Retrieve the top-k most similar chunks from pgvector using cosine similarity.

    Filters out results with score < 0.3 (too dissimilar).

    Args:
        conn:         Active psycopg2 connection.
        query_vector: Query embedding as a list of floats.
        top_k:        Maximum number of results to return.

    Returns:
        List of dicts: [{"text": str, "source_file": str, "chunk_index": int, "score": float}]
        Returns an empty list if no results meet the threshold.
    """
    sql = """
        SELECT source_file, chunk_index, page, text,
               1 - (embedding <=> %s::vector) AS score
        FROM document_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (query_vector, query_vector, top_k))
            rows = cur.fetchall()
    except Exception as exc:
        logger.error("Similarity search failed: %s", exc)
        return []

    results = []
    for source_file, chunk_index, page, text, score in rows:
        if score < 0.3:  # filter out dissimilar chunks (matches docstring)
            continue
        results.append({
            "text": text,
            "source_file": source_file,
            "chunk_index": chunk_index,
            "page": page or 1,
            "score": float(score),
        })

    return results


# ---------------------------------------------------------------------------
# 6.4  assemble_prompt()
# ---------------------------------------------------------------------------

def assemble_prompt(query: str, chunks: list, history: list) -> list:
    """Assemble a LiteLLM messages list with system prompt, history, context, and query.

    Args:
        query:   The user's current question.
        chunks:  Retrieved document chunks (from similarity_search).
        history: Conversation history as list of {"role": str, "content": str} dicts.

    Returns:
        List of message dicts in LiteLLM format.
    """
    messages = []

    # System prompt
    messages.append({"role": "system", "content": _SYSTEM_PROMPT})

    # Conversation history: keep last 3 turns (6 messages)
    recent_history = history[-6:] if len(history) > 6 else history
    for turn in recent_history:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Build context from chunks
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks, start=1):
            context_parts.append(
                f"[文獻片段 {i}] 來源: {chunk['source_file']}, p.{chunk.get('page', 1)}\n"
                f"{chunk['text']}"
            )
        context = "\n\n".join(context_parts)
        user_content = f"{context}\n\n問題：{query}"
    else:
        user_content = f"問題：{query}"

    messages.append({"role": "user", "content": user_content})

    return messages


# ---------------------------------------------------------------------------
# 6.5  format_answer()
# ---------------------------------------------------------------------------

def format_answer(response: str, chunks: list) -> str:
    """Append a citation list to the LLM response.

    Args:
        response: The raw LLM response text.
        chunks:   Retrieved document chunks used to generate the response.

    Returns:
        Formatted answer string with citations appended, or the original
        response if chunks is empty.
    """
    if not chunks:
        return response

    citation_lines = []
    for i, chunk in enumerate(chunks, start=1):
        citation_lines.append(
            f"[{i}] {chunk['source_file']}, p.{chunk.get('page', 1)}"
            f" (相似度 {chunk.get('score', 0):.2f})"
        )

    citations = "\n".join(citation_lines)
    return f"{response}\n\n---\n📚 引用來源：\n{citations}"


# ---------------------------------------------------------------------------
# 7.1  run_query()
# ---------------------------------------------------------------------------

def _call_llm(messages: list, model: str) -> str:
    """Call LLM via HuggingFace InferenceClient or LiteLLM fallback.

    Strips the 'huggingface/' prefix if present for InferenceClient.
    """
    hf_token = os.environ.get("HF_TOKEN", "")

    # Extract model ID (remove 'huggingface/' prefix if present)
    model_id = model.replace("huggingface/", "") if model.startswith("huggingface/") else model

    # Try HuggingFace InferenceClient first (most reliable for free tier)
    if InferenceClient is not None and hf_token:
        try:
            client = InferenceClient(model=model_id, token=hf_token)
            response = client.chat_completion(messages=messages, max_tokens=1024)
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("InferenceClient failed (%s), trying LiteLLM...", exc)

    # Fallback: LiteLLM
    if litellm is not None:
        os.environ["HUGGINGFACE_API_KEY"] = hf_token
        full_model = model if model.startswith("huggingface/") else f"huggingface/{model}"
        response = litellm.completion(model=full_model, messages=messages)
        return response.choices[0].message.content

    raise RuntimeError("No LLM backend available (huggingface_hub and litellm both unavailable)")


def run_query(
    query: str,
    top_k: int = 5,
    model: str = "huggingface/Qwen/Qwen2.5-72B-Instruct",
    history: list = None,
) -> str:
    """Execute a full RAG query and return a formatted answer with citations.

    Reads EMBEDDING_MODEL and PGVECTOR_CONNECTION_STRING from the environment.
    Logs ERROR and exits with code 1 if either variable is missing.

    Args:
        query:   The user's question.
        top_k:   Number of chunks to retrieve.
        model:   LiteLLM model identifier.
        history: Conversation history (list of role/content dicts).

    Returns:
        Formatted answer string (with citations), or an error/no-result message.
    """
    if history is None:
        history = []

    # --- Load required environment variables ---
    embedding_model = os.environ.get("EMBEDDING_MODEL")
    connection_string = os.environ.get("PGVECTOR_CONNECTION_STRING")

    missing = [v for v, val in [("EMBEDDING_MODEL", embedding_model),
                                 ("PGVECTOR_CONNECTION_STRING", connection_string)]
               if not val]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

    # --- Connect to database ---
    if psycopg2 is None:
        logger.error("psycopg2 is not installed. Cannot connect to the database.")
        sys.exit(1)

    try:
        conn = psycopg2.connect(connection_string)
    except Exception as exc:
        logger.error("Failed to connect to the database: %s", exc)
        sys.exit(1)

    try:
        # --- Embed query ---
        query_vector = embed_query(query, embedding_model)

        # --- Retrieve similar chunks ---
        chunks = similarity_search(conn, query_vector, top_k)

        # --- Handle empty results ---
        if not chunks:
            return (
                "目前知識庫中無與您查詢相關的文獻資料。"
                "請確認知識庫已包含相關論文，或嘗試調整查詢關鍵字。"
            )

        # --- Assemble prompt ---
        messages = assemble_prompt(query, chunks, history or [])

        # --- Call LLM ---
        try:
            answer = _call_llm(messages, model)
        except Exception as exc:
            logger.error("LiteLLM call failed: %s", exc)
            return f"LLM 呼叫失敗，請稍後重試。錯誤：{exc}"

        # --- Format and return ---
        return format_answer(answer, chunks)

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 7.2  run_interactive()
# ---------------------------------------------------------------------------

def run_interactive(
    top_k: int = 5,
    model: str = "huggingface/Qwen/Qwen2.5-72B-Instruct",
) -> None:
    """Run an interactive multi-turn conversation loop.

    Maintains the last 3 turns (6 messages) of conversation history.
    Type 'exit', 'quit', or press Enter on an empty line to quit.

    Args:
        top_k:  Number of chunks to retrieve per query.
        model:  LiteLLM model identifier.
    """
    print("保健食品 RAG 問答系統（輸入 'exit' 或 'quit' 結束）")
    history = []
    while True:
        query = input("\n您的問題：").strip()
        if query.lower() in ("exit", "quit", ""):
            print("再見！")
            break
        answer = run_query(query, top_k=top_k, model=model, history=history)
        print(f"\n{answer}")
        # 更新歷史（保留最近 3 輪 = 6 條訊息）
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 6:
            history = history[-6:]


# ---------------------------------------------------------------------------
# 7.3  CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="保健食品 RAG 問答系統")
    parser.add_argument("--query", type=str, help="單次查詢問題")
    parser.add_argument("--top-k", type=int, default=5, help="檢索 chunk 數量（預設 5）")
    parser.add_argument(
        "--model",
        type=str,
        default="huggingface/Qwen/Qwen2.5-72B-Instruct",
        help="LLM 模型名稱",
    )
    args = parser.parse_args()

    if args.query:
        result = run_query(args.query, top_k=args.top_k, model=args.model)
        print(result)
    else:
        run_interactive(top_k=args.top_k, model=args.model)
