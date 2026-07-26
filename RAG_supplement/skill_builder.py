"""
skill_builder.py — Automated skill.md generator for the Dietary Supplements RAG system.

Generates a structured Agent Skill document by:
  1. Running RAG queries against the knowledge base (gather_knowledge)
  2. Synthesizing the Q&A pairs into a skill.md via LLM (synthesize_skill_doc)
  3. Validating the output structure (validate_skill_doc)
  4. Writing the result to disk (run_build)
"""

import os
import sys
import logging
import argparse
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # type: ignore

try:
    import litellm
except ImportError:
    litellm = None  # type: ignore

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None  # type: ignore

from rag_query import run_query

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
# Default questions for the dietary supplements domain
# ---------------------------------------------------------------------------
DEFAULT_QUESTIONS = [
    "這個知識庫涵蓋哪些保健食品成分？",
    "各成分的主要功效與適用族群為何？",
    "文獻中最常見的劑量建議範圍為何？",
    "有哪些成分具有交互作用或禁忌症的研究？",
    "目前研究最充分的保健食品成分有哪些？",
]


# ---------------------------------------------------------------------------
# 9.1  load_questions()
# ---------------------------------------------------------------------------

def load_questions(path: str | None) -> list[str]:
    """Load question list from a file, or return DEFAULT_QUESTIONS if path is None.

    Args:
        path: Path to a text file with one question per line, or None.

    Returns:
        List of non-empty question strings.
    """
    if path is None:
        return DEFAULT_QUESTIONS

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


# ---------------------------------------------------------------------------
# 9.2  gather_knowledge()
# ---------------------------------------------------------------------------

def gather_knowledge(questions: list[str], model: str, top_k: int = 5) -> list[dict]:
    """Run RAG queries for each question and collect Q&A pairs.

    Args:
        questions: List of question strings.
        model:     LiteLLM model identifier.
        top_k:     Number of chunks to retrieve per query.

    Returns:
        List of dicts: [{"question": str, "answer": str}]
    """
    qa_pairs = []
    total = len(questions)
    for i, question in enumerate(questions, start=1):
        logger.info("Gathering knowledge: %d/%d - %s", i, total, question)
        answer = run_query(question, top_k=top_k, model=model)
        qa_pairs.append({"question": question, "answer": answer})
    return qa_pairs


# ---------------------------------------------------------------------------
# 9.3  synthesize_skill_doc()
# ---------------------------------------------------------------------------

def synthesize_skill_doc(
    qa_pairs: list[dict],
    model: str,
    source_count: int = 0,
) -> str:
    """Synthesize a skill.md document from Q&A pairs using an LLM.

    Args:
        qa_pairs:     List of {"question": str, "answer": str} dicts.
        model:        LiteLLM model identifier.
        source_count: Number of source documents in the knowledge base.

    Returns:
        Generated skill.md content as a string.
    """
    today_date = date.today().isoformat()

    # Build Q&A section for the prompt
    qa_text_parts = []
    for i, pair in enumerate(qa_pairs, start=1):
        qa_text_parts.append(
            f"問題 {i}：{pair['question']}\n回答 {i}：{pair['answer']}"
        )
    qa_text = "\n\n".join(qa_text_parts)

    system_prompt = (
        "你是一位知識整合專家，請根據以下保健食品學術文獻的問答資料，"
        "生成一份符合格式規範的 Agent Skill 文件。"
    )

    user_prompt = f"""以下是保健食品知識庫的問答資料：

{qa_text}

請生成以下格式的 skill.md：

# Skill: 保健食品知識庫

## Metadata
- **知識領域**：保健食品 / Dietary Supplements
- **資料來源數量**：{source_count} 份文件
- **最後更新時間**：{today_date}
- **適用 Agent 類型**：健康營養研究助手 / 保健食品顧問

## Overview（一段話摘要，200字以內）
[根據問答資料撰寫]

## Core Concepts（核心概念，5-15個）
[每個概念附1-2句說明]

## Key Trends（最新趨勢，3-10個）
[條列]

## Key Entities（重要實體）
[作者、機構、成分、工具等，分類條列]

## Methodology & Best Practices（方法論與最佳實踐）
[條列]

## Knowledge Gaps & Limitations（知識邊界）
[說明]

## Example Q&A（代表性問答，3-5組）
[問題與簡短答案]

## Source References（來源索引）
[列出資料來源]

請嚴格按照上述格式輸出，確保每個章節標題完整出現。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if litellm is None and InferenceClient is None:
        logger.error("Neither litellm nor huggingface_hub is installed.")
        return ""

    hf_token = os.environ.get("HF_TOKEN", "")
    model_id = model.replace("huggingface/", "") if model.startswith("huggingface/") else model

    # Try InferenceClient first
    if InferenceClient is not None and hf_token:
        try:
            client = InferenceClient(model=model_id, token=hf_token)
            response = client.chat_completion(messages=messages, max_tokens=2048)
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("InferenceClient failed (%s), trying LiteLLM...", exc)

    # Fallback: LiteLLM
    if litellm is not None:
        os.environ["HUGGINGFACE_API_KEY"] = hf_token
        full_model = model if model.startswith("huggingface/") else f"huggingface/{model}"
        try:
            response = litellm.completion(model=full_model, messages=messages)
            return response.choices[0].message.content
        except Exception as exc:
            logger.error("LiteLLM call failed during synthesis: %s", exc)
            return ""

    return ""


# ---------------------------------------------------------------------------
# 9.6  validate_skill_doc()
# ---------------------------------------------------------------------------

def validate_skill_doc(content: str) -> bool:
    """Validate that the skill.md content contains all required sections.

    Args:
        content: The skill.md content string.

    Returns:
        True if all required sections are present, False otherwise.
    """
    required_sections = [
        "## Overview",
        "## Core Concepts",
        "## Key Trends",
        "## Key Entities",
        "## Methodology",
        "## Knowledge Gaps",
        "## Example Q&A",
        "## Source References",
    ]

    missing = [s for s in required_sections if s not in content]
    if missing:
        logger.warning(
            "skill.md is missing required sections: %s", ", ".join(missing)
        )
        return False

    return True


# ---------------------------------------------------------------------------
# 9.6  run_build()
# ---------------------------------------------------------------------------

def run_build(
    output: str = "skill.md",
    model: str = "huggingface/Qwen/Qwen2.5-72B-Instruct",
    questions_path: str | None = None,
) -> None:
    """Main build pipeline: load questions → gather knowledge → synthesize → validate → write.

    Args:
        output:         Output file path for the generated skill.md.
        model:          LiteLLM model identifier.
        questions_path: Path to a custom questions file, or None for defaults.
    """
    # 1. Load questions
    questions = load_questions(questions_path)

    # 2. Gather knowledge via RAG
    qa_pairs = gather_knowledge(questions, model)

    # 3. Count source documents from processed_files table
    source_count = 0
    connection_string = os.environ.get("PGVECTOR_CONNECTION_STRING")
    if psycopg2 is not None and connection_string:
        try:
            conn = psycopg2.connect(connection_string)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM processed_files")
                    row = cur.fetchone()
                    if row:
                        source_count = row[0]
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Could not query processed_files table: %s", exc)

    # 4. Synthesize skill document
    content = synthesize_skill_doc(qa_pairs, model, source_count)

    # 5. Validate (log result but do not abort)
    is_valid = validate_skill_doc(content)
    if is_valid:
        logger.info("skill.md validation passed: all required sections present.")
    else:
        logger.warning("skill.md validation failed: some sections may be missing.")

    # 6. Write to disk
    Path(output).write_text(content, encoding="utf-8")
    logger.info("skill.md generated: %s", output)


# ---------------------------------------------------------------------------
# 9.7  CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成保健食品 Agent Skill 文件")
    parser.add_argument("--output", default="skill.md", help="輸出路徑（預設 skill.md）")
    parser.add_argument(
        "--model",
        default="huggingface/Qwen/Qwen2.5-72B-Instruct",
        help="LLM 模型名稱",
    )
    parser.add_argument(
        "--questions",
        default=None,
        help="自訂問題清單檔案路徑",
    )
    args = parser.parse_args()
    run_build(output=args.output, model=args.model, questions_path=args.questions)
