/**
 * kidson-supplement-rag — Cloudflare Workers RAG API
 *
 * 端點：
 *   POST /api/ingest  {docs:[{source_file, page, chunk_index, text}], key}
 *       → Workers AI bge-m3 嵌入 → Vectorize upsert
 *   POST /api/query   {query, top_k?}
 *       → 嵌入查詢 → Vectorize 檢索 → LLM 生成 → 附頁碼引用
 *   GET  /api/health
 *
 * Embedding: @cf/baai/bge-m3（多語，1024 維，中文查詢可命中英文文獻）
 * LLM:       OpenRouter (nvidia/nemotron-3-super-120b-a12b:free)，Workers AI llama-3.1-8b 為 fallback
 */

const EMBED_MODEL = "@cf/baai/bge-m3";
const FALLBACK_LLM = "@cf/nvidia/nemotron-3-super-120b-a12b:free"; // Workers AI fallback

const SYSTEM_PROMPT = `你是一位保健食品專業顧問，專門根據學術文獻回答關於保健食品成分功效與劑量建議的問題。
請根據以下提供的文獻片段，主動、積極地為使用者整理出完整的分析報告，包括：
1. 各成分的功效機制與臨床實證（明確說明對應的研究族群與試驗設計）
2. 建議攝取劑量範圍（以文獻中的臨床試驗劑量為優先依據；若文獻片段未直接列出某成分劑量，可基於文中相關營養素的常規臨床用量補充，並標注「依營養學常規」）
3. 注意事項與禁忌（如懷孕、藥物交互作用、最佳攝取時機）
4. 若提供的文獻片段確實與問題完全無關，才告知使用者知識庫中無相關資訊
請以繁體中文回答，語氣專業、條理清晰，直接給出可執行的建議，不要退縮或只重複「文獻未提及」。`;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Ingest-Key",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...CORS },
  });
}

async function embed(env, texts) {
  const res = await env.AI.run(EMBED_MODEL, { text: texts });
  // bge-m3 returns {data: [[...1024 floats], ...]}
  if (!res || !res.data) {
    throw new Error("EMBED_BAD_RESPONSE: " + JSON.stringify(res).slice(0, 300));
  }
  return res.data;
}

async function shortId(sourceFile, chunkIndex) {
  // Vectorize ID limit = 64 bytes; long filenames overflow, so hash them.
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(String(sourceFile))
  );
  const hex = [...new Uint8Array(buf)]
    .slice(0, 12)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `${hex}#${chunkIndex}`;
}

async function handleIngest(request, env) {
  if (env.INGEST_REQUIRE_KEY === "true") {
    const key = request.headers.get("X-Ingest-Key");
    if (!env.INGEST_KEY || key !== env.INGEST_KEY) {
      return json({ error: "unauthorized" }, 401);
    }
  }
  const body = await request.json();
  const docs = body.docs || [];
  if (!docs.length) return json({ error: "docs is empty" }, 400);
  if (docs.length > 100) return json({ error: "max 100 docs per request" }, 400);

  const embeddings = await embed(env, docs.map((d) => d.text));
  const vectors = await Promise.all(
    docs.map(async (d, i) => ({
      id: await shortId(d.source_file, d.chunk_index ?? i),
      values: embeddings[i],
      metadata: {
        source_file: String(d.source_file || ""),
        page: Number(d.page || 1),
        chunk_index: Number(d.chunk_index || i),
        text: String(d.text).slice(0, 9000),
      },
    }))
  );

  const result = await env.VECTORIZE.upsert(vectors);
  return json({ ok: true, upserted: vectors.length, mutation: result });
}

async function handleQuery(request, env) {
  try {
    return await _handleQuery(request, env);
  } catch (e) {
    const msg = (e && e.message) ? e.message : String(e);
    const stack = (e && e.stack) ? e.stack : "";
    return json({ error: "INTERNAL_ERR", message: msg, stack: stack.slice(0, 500) }, 500);
  }
}

async function _handleQuery(request, env) {
  const body = await request.json();
  const query = (body.query || "").trim();
  if (!query) return json({ error: "query is required" }, 400);

  const topK = Math.min(Number(body.top_k) || Number(env.TOP_K) || 5, 20);
  const threshold = Number(env.SCORE_THRESHOLD) || 0.3;

  // 1. embed query
  const [qvec] = await embed(env, [query]);

  // 2. retrieve
  const matches = await env.VECTORIZE.query(qvec, {
    topK,
    returnMetadata: "all",
  });
  const chunks = (matches.matches || [])
    .filter((m) => m.score >= threshold)
    .map((m) => ({
      text: m.metadata?.text || "",
      source_file: m.metadata?.source_file || "unknown",
      page: m.metadata?.page || 1,
      score: m.score,
    }));

  if (!chunks.length) {
    return json({
      answer:
        "目前知識庫中無與您查詢相關的文獻資料。請確認知識庫已包含相關論文，或嘗試調整查詢關鍵字。",
      citations: [],
    });
  }

  // 限制送給 LLM 的 context 長度（避免超出模型上限導致 500）
  const MAX_CHUNKS = 3;
  const MAX_CHUNK_CHARS = 800;
  const top = chunks.slice(0, MAX_CHUNKS);

  // 3. assemble prompt
  const context = top
    .map(
      (c, i) =>
        `[文獻片段 ${i + 1}] 來源: ${c.source_file}, p.${c.page}\n${c.text.slice(0, MAX_CHUNK_CHARS)}`
    )
    .join("\n\n");

  // 4. generate — OpenRouter first (if key set), Workers AI fallback
  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: `${context}\n\n問題：${query}` },
  ];
  const { answer, model_used } = await generate(env, messages);

  const citations = chunks.map((c, i) => ({
    n: i + 1,
    source_file: c.source_file,
    page: c.page,
    score: Math.round(c.score * 100) / 100,
  }));

  return json({ answer, citations, model: model_used });
}

async function generate(env, messages) {
  // Primary: OpenRouter (OpenAI-compatible). Try both possible secret names.
  const orKey = env.OPENROUTER_API_KEY || env["sk-or-...1889"];
  if (orKey) {
    const model = env.LLM_MODEL || "nvidia/nemotron-3-super-120b-a12b:free";
    try {
      const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${orKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ model, messages, max_tokens: 1024 }),
      });
      if (res.ok) {
        const text = await res.text();
        try {
          const data = JSON.parse(text);
          const content = data.choices?.[0]?.message?.content;
          if (content) return { answer: content, model_used: data.model || model };
        } catch (parseErr) {
          console.log("OpenRouter JSON parse failed:", parseErr, text.slice(0, 200));
        }
      } else {
        const errBody = (await res.text()).slice(0, 300);
        console.log("OpenRouter error", res.status, errBody);
        return { answer: `OpenRouter API 錯誤 (HTTP ${res.status}): ${errBody}`, model_used: model };
      }
    } catch (err) {
      console.log("OpenRouter fetch failed:", err);
    }
  }
  // Fallback: Workers AI
  const llm = await env.AI.run(FALLBACK_LLM, { messages, max_tokens: 1024 });
  return { answer: llm.response, model_used: FALLBACK_LLM };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }

    try {
      if (url.pathname === "/api/health") {
        return json({
          ok: true,
          embed_model: EMBED_MODEL,
          llm: env.OPENROUTER_API_KEY
            ? `openrouter:${env.LLM_MODEL || "nvidia/nemotron-3-super-120b-a12b:free"}`
            : `workers-ai:${FALLBACK_LLM}`,
        });
      }
      if (url.pathname === "/api/ingest" && request.method === "POST") {
        return await handleIngest(request, env);
      }
      if (url.pathname === "/api/query" && request.method === "POST") {
        return await handleQuery(request, env);
      }
      return json({ error: "not found" }, 404);
    } catch (err) {
      return json({ error: String(err?.message || err) }, 500);
    }
  },
};
