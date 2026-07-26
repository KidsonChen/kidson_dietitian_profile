/**
 * kidson-supplement-rag — Cloudflare Workers RAG API
 *
 * 路由：
 *   POST /api/ingest  {docs:[{source_file, page, chunk_index, text}], key}
 *       → Workers AI bge-m3 嵌入 → Vectorize upsert
 *   POST /api/query   {query, top_k?}
 *       → 嵌入查詢 → Vectorize 檢索 → LLM 生成 → 附帶引用
 *   GET  /api/health
 *
 * Embedding: @cf/baai/bge-m3（多語，1024 維，中文查詢可命中英文文獻）
 * LLM:       OpenRouter (nvidia/nemotron-3-super-120b-a12b:free)，Workers AI llama-3.1-8b 為 fallback
 */

const EMBED_MODEL = "@cf/baai/bge-m3";
const FALLBACK_LLM = "@cf/meta/llama-3.1-8b-instruct-fp8"; // Workers AI fallback

const SYSTEM_PROMPT = `你是一位臨床營養師，正在面對一位來詢問的客戶，用口語、像在診間解釋的語氣寫分析報告。根據提供的文獻片段，主動整理出建議，不要退縮。

【格式】
報告分三個小節，標題固定用數字開頭（前端要靠這個切卡片，不可省略編號）：
1. 各成分怎麼幫你
2. 建議吃多少
3. 什麼時候吃、要注意什麼
每節內用「•」條列，不要寫成一整段。重要劑量數字用 **粗體**。全部繁體中文，標點用全形（，。：；！？），計量範圍用全形連字號（如 300–500 mg／天），斜線用全形「／」。

【去 AI 味的寫作規範——務必遵守】
- 每個成分只講一次核心機制，禁止把同一句話重複兩遍（例如不要同時寫「降低皮質醇」又寫「顯著降低皮質醇」）。
- 禁用模糊誇大詞與填充詞，以下詞彙【絕對禁止出現】：「顯著」「強效」「支持Ｘ功能」「一般建議」「根據文獻」「正面影響」「廣泛落在」。要具體：
  · 不寫「強效抗氧化」，改寫成具體作用，如「減少脂質過氧化、減輕肝臟代謝負擔」。
  · 不寫「對睡眠有正面影響」，改寫成具體機制，如「參與褪黑激素合成，幫助調整生理時鐘」。
  · 不寫「根據文獻」或「一般建議」，直接給根據：有具體研究就寫出族群與試驗設計（如「失眠成人每日 300 mg、連續 8 週的隨機試驗」）；沒有就直接給劑量範圍，並標「（依營養學常規）」。
  · 不寫「臨床有效劑量廣泛落在」，直接寫「每日 300–500 mg」這種具體範圍即可。
- 五個成分（南非醉茄、GABA、芝麻素、鋅、藻油）每個寫【一句專屬描述】，彼此不能重複同一句話、不能複製貼上。
- 攝取時機：GABA 與芝麻素是晚安膠囊的內容物，寫「晚安膠囊睡前 30–60 分鐘」即可，不要單獨列；鋅與藻油分開寫「早餐後」，不要也寫成晚安膠囊。
- 結尾不要罐頭免責（不要寫「懷孕哺乳等情況建議諮詢醫師」這種每篇都一樣的話）。給一句具體行動建議，例如「先從睡前一顆晚安膠囊開始，兩週後看入睡速度再決定要不要加量」。

【成分中英文名嚴格對應】
南非醉茄 = Ashwagandha、芝麻素 = sesamin（不是 sesame oil）、藻油 = algae oil（含 DHA／EPA）、GABA = GABA、鋅 = zinc。

【台灣 DRIs 第八版對應——前端已處理，模型勿自行編寫數值】
客戶的每日建議攝取量（鈣、鐵、鋅、鎂、維生素D、葉酸、DHA）會由網站前端依其性別／年齡／族群精算並顯示，你【不需要】在報告裡寫 DRIs 數值，也不要自己編寫或對比這些數字（避免錯誤）。你只需專注在：
· 各成分對此族群的功效機制與臨床實證（用白話）。
· 產品建議劑量。
· 該族群相關的具體注意事項（如孕婦避免某些成分、鐵劑與鈣錯開、抗凝血藥與魚油間隔、孩童劑量減半）。

【內容要求】
- 各成分：說明機制與臨床實證，點出研究族群（如健康志願者、失眠族群），用白話。
- 劑量：以文獻臨床試驗劑量為優先；未直接列出就給常規用量並標「（依營養學常規）」。務必對比客戶族群的 DRIs 建議量。
- 注意：攝取時機、真正相關的禁忌（如特定藥物交互作用、懷孕哺乳注意），寫具體的，不寫罐頭。
- 有證據就積極給建議，不要只重複「文獻未提及」。`;

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
  if (!res || !res.data) {
    throw new Error("EMBED_BAD_RESPONSE: " + JSON.stringify(res).slice(0, 300));
  }
  return res.data;
}

async function shortId(sourceFile, chunkIndex) {
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
        "目前知識庫中沒有與您查詢相關的文獻資料。請確認知識庫已包含相關文獻，或嘗試調整查詢關鍵字。",
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
  // Primary: OpenRouter (OpenAI-compatible) when OPENROUTER_API_KEY secret is set
  if (env.OPENROUTER_API_KEY) {
    const model = env.LLM_MODEL || "nvidia/nemotron-3-super-120b-a12b:free";
    try {
      const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.OPENROUTER_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ model, messages, max_tokens: 4096, temperature: 0.3 }),
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
        console.log("OpenRouter error (falling back to Workers AI):", res.status, errBody);
        // 不 return：fall through 到下方 Workers AI fallback
      }
    } catch (err) {
      console.log("OpenRouter fetch failed (falling back to Workers AI):", err);
    }
  }
  // Fallback: Workers AI（OpenRouter 失敗/429/無 key 時自動接手）
  try {
    const llm = await env.AI.run(FALLBACK_LLM, { messages, max_tokens: 4096, temperature: 0.3 });
    return { answer: llm.response, model_used: FALLBACK_LLM };
  } catch (fbErr) {
    console.log("Workers AI fallback also failed:", fbErr);
    return { answer: "AI 分析暫時無法使用，請稍後再試。您仍可參考上方營養師推薦方案。", model_used: "none" };
  }
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
