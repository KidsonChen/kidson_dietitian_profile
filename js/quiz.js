/* 簡易版純 JS 問卷元件
   使用方法：在頁面放一個 <div id="nutrition-quiz"></div>
   並在頁面底部引入 <script src="/js/quiz.js"></script>
*/
(function () {
  // RAG API（Cloudflare Workers + Vectorize，回答附文獻頁碼引用）
  const RAG_API = 'https://kidson-supplement-rag.kidson7911.workers.dev/api/query';
  // 產品購買連結（1shop 賣場）
  const SHOP_URL = 'https://drnutrii.1shop.tw/HUG';

  const questions = [
    {
      id: 'gender',
      question: "您的生理性別是？",
      options: [
        { label: "女性", value: "female" },
        { label: "男性", value: "male" },
      ],
    },
    {
      id: 'ageGroup',
      question: "您的年齡層是？",
      options: [
        { label: "4–12 歲（孩童）", value: "child" },
        { label: "13–18 歲（青少年）", value: "teen" },
        { label: "19–50 歲（成年）", value: "adult" },
        { label: "51 歲以上（銀髮族）", value: "senior" },
      ],
    },
    {
      id: 'group',
      question: "您目前屬於哪個特殊族群？（可跳過視為一般）",
      options: [
        { label: "一般族群", value: "general" },
        { label: "懷孕中", value: "pregnant" },
        { label: "哺乳期", value: "lactating" },
        { label: "慢性病用藥中", value: "chronic" },
      ],
    },
    {
      id: 1,
      question: "您目前最想改善的健康問題是？",
      options: [
        { label: "睡眠品質不佳、難以入睡", value: "sleep" },
        { label: "消化不良、排便不順", value: "digestion" },
        { label: "容易疲勞、精神不濟", value: "energy" },
        { label: "皮膚暗沉、想要美白", value: "beauty" },
        { label: "體重管理、想要瘦身", value: "weight" },
      ],
    },
    {
      id: 3,
      question: "您的生活型態是？",
      options: [
        { label: "久坐辦公、少運動", value: "sedentary" },
        { label: "輕度運動（每週1-2次）", value: "light" },
        { label: "規律運動（每週3次以上）", value: "active" },
        { label: "高強度運動/健身", value: "intense" },
      ],
    },
    {
      id: 4,
      question: "您目前有在補充保健品嗎？",
      options: [
        { label: "完全沒有", value: "none" },
        { label: "偶爾吃維他命", value: "occasional" },
        { label: "有固定在吃幾種", value: "regular" },
        { label: "吃很多種但不確定是否正確", value: "confused" },
      ],
    },
    {
      id: 5,
      question: "您的飲食習慣是？",
      options: [
        { label: "三餐正常、均衡飲食", value: "balanced" },
        { label: "經常外食、營養不均", value: "eating-out" },
        { label: "素食者", value: "vegetarian" },
        { label: "經常節食或不規律進食", value: "irregular" },
      ],
    },
  ];

  // 基本資料中文標籤（結果頁顯示用）
  const profileLabels = {
    gender: { female: "女性", male: "男性" },
    ageGroup: { child: "孩童（4–12 歲）", teen: "青少年（13–18 歲）", adult: "成年（19–50 歲）", senior: "銀髮族（51 歲以上）" },
    group: { general: "一般族群", pregnant: "懷孕中", lactating: "哺乳期", chronic: "慢性病用藥中" },
  };

  // 台灣 DRIs 第八版關鍵營養素每日建議攝取量（RDA 或 AI）
  // 單位：鈣 mg、鐵 mg、鋅 mg、鎂 mg、維生素D μg、葉酸 μg、DHA mg
  // 索引順序：gender(0=女,1=男) × ageGroup(child/teen/adult/senior) × group(general/pregnant/lactating/chronic)
  const DRIS = {
    calcium: {
      child:   { f: 800, m: 800 }, teen: { f: 1200, m: 1200 }, adult: { f: 1000, m: 1000 }, senior: { f: 1000, m: 1000 },
      preg: 1000, lact: 1000,
    },
    iron: {
      child:   { f: 10, m: 10 }, teen: { f: 15, m: 15 }, adult: { f: 15, m: 10 }, senior: { f: 10, m: 10 },
      preg: 27, lact: 15,
    },
    zinc: {
      child:   { f: 10, m: 10 }, teen: { f: 12, m: 15 }, adult: { f: 12, m: 15 }, senior: { f: 12, m: 15 },
      preg: 15, lact: 12,
    },
    magnesium: {
      child:   { f: 180, m: 180 }, teen: { f: 350, m: 410 }, adult: { f: 320, m: 380 }, senior: { f: 310, m: 340 },
      preg: 355, lact: 320,
    },
    vitD: {
      child: 10, teen: 10, adult: 10, senior: 15, preg: 10, lact: 10,
    },
    folate: {
      child: 200, teen: 400, adult: 400, senior: 400, preg: 600, lact: 500,
    },
    dha: {
      child: "300–500", teen: "300–500", adult: "300–500", senior: "300–500", preg: "300–500", lact: "300–500",
    },
  };

  // 依性別 / 年齡層 / 特殊族群計算該客戶的 DRIs 基準
  function getDrisBaseline(answers) {
    const g = answers.gender === 'male' ? 'm' : 'f';
    const age = answers.ageGroup || 'adult';
    const grp = answers.group || 'general';
    const base = {};
    const key = grp === 'pregnant' ? 'preg' : grp === 'lactating' ? 'lact' : null;
    if (key) {
      base.calcium = DRIS.calcium[key];
      base.iron = DRIS.iron[key];
      base.zinc = DRIS.zinc[key];
      base.magnesium = DRIS.magnesium[key];
      base.vitD = DRIS.vitD[key];
      base.folate = DRIS.folate[key];
      base.dha = DRIS.dha[key];
    } else {
      base.calcium = DRIS.calcium[age][g];
      base.iron = DRIS.iron[age][g];
      base.zinc = DRIS.zinc[age][g];
      base.magnesium = DRIS.magnesium[age][g];
      base.vitD = DRIS.vitD[age];
      base.folate = DRIS.folate[age];
      base.dha = DRIS.dha[age];
    }
    return base;
  }

  function getRecommendation(answers) {
    const primary = answers[1];

    const recommendations = {
      sleep: {
        title: "好眠放鬆方案",
        products: [
          { name: "晚安膠囊", reason: "南非醉茄+GABA+芝麻素，四大天王幫助入睡", price: "$837" },
          { name: "胺基酸鎂", reason: "高吸收率胺基酸型態鎂，放鬆肌肉助眠", price: "$393" },
          { name: "高濃度藻油", reason: "DHA 幫助神經系統放鬆", price: "$1,008" },
        ],
        advice: "建議睡前1小時服用晚安膠囊+胺基酸鎂，搭配減少藍光暴露，建立固定就寢時間。",
      },
      digestion: {
        title: "消化順暢方案",
        products: [
          { name: "機能益生菌", reason: "五大益生菌+三大益生質，改善腸道環境", price: "$618" },
          { name: "飽足感Fiber", reason: "4大植物纖維，促進腸道蠕動", price: "$418" },
          { name: "綜合酵素", reason: "80種植物發酵酵素，幫助消化分解", price: "$669" },
        ],
        advice: "建議餐前服用益生菌，餐後搭配酵素。每日補充足夠水分（2000ml以上）效果更佳。",
      },
      energy: {
        title: "活力充沛方案",
        products: [
          { name: "綜合B群 PREMIUM", reason: "9種維生素+牛磺酸+刺五加，精神旺盛", price: "$485" },
          { name: "EPA 85%高濃度魚油", reason: "促進新陳代謝，好心情好活力", price: "$1,426" },
          { name: "CoQ10 輔酵素", reason: "細胞能量工廠，抗疲勞", price: "$585" },
        ],
        advice: "建議早餐後服用B群和魚油，CoQ10可在午餐後補充。搭配規律作息效果更好。",
      },
      beauty: {
        title: "美麗光采方案",
        products: [
          { name: "穀胱甘肽複合膠囊", reason: "98%高純度，美白抗氧化", price: "$753" },
          { name: "雪淬", reason: "賽洛美+玻尿酸，由內而外水潤", price: "$963" },
          { name: "PureWay C 750", reason: "高濃度維生素C，促進膠原蛋白合成", price: "$1,122" },
        ],
        advice: "建議空腹服用穀胱甘肽效果最佳，維生素C餐後補充。搭配防曬和充足睡眠。",
      },
      weight: {
        title: "健康管理方案",
        products: [
          { name: "飽飽雙纖", reason: "魔芋纖維+白腎豆+藤黃果，餐前控制", price: "$671" },
          { name: "飽足感Fiber", reason: "低卡高纖，增加飽足感", price: "$418" },
          { name: "綜合B群 PREMIUM", reason: "維持代謝正常運作", price: "$485" },
        ],
        advice: "建議餐前30分鐘服用飽飽雙纖，搭配高蛋白飲食和適度運動，健康不復胖。",
      },
    };

    return recommendations[primary] || recommendations.energy;
  }

  // 呼叫 RAG API 產生個人化文獻分析報告
  function fetchAiReport(rec, answers, targetEl) {
    const ingredients = rec.products.map(function (p) { return p.name + '（' + p.reason + '）'; }).join('、');
    const gender = profileLabels.gender[answers.gender] || '未填寫';
    const ageGroup = profileLabels.ageGroup[answers.ageGroup] || '未填寫';
    const group = profileLabels.group[answers.group] || '一般族群';
    const query =
      '客戶基本資料：生理性別 ' + gender + '，年齡層 ' + ageGroup + '，特殊族群 ' + group + '。' +
      '客戶主要健康需求：' + rec.title + '。' +
      '考慮補充的產品成分：' + ingredients + '。' +
      '請根據科學文獻與台灣DRIs第八版，說明這些相關營養素對此族群的功效證據、有效劑量範圍，以及對比該族群的每日建議攝取量（如孕婦葉酸600μg、鐵27mg；銀髮族維生素D 15μg；孩童鈣600-800mg），並提醒注意事項。';

    // 重試直到報告含三個小節（避免免費模型截斷）
    function tryOnce(attempt) {
      if (attempt > 2) {
        targetEl.innerHTML = '<div style="color:#6b7280;line-height:1.7">分析生成不完整，請重新整理問卷或稍後再試。您仍可參考上方營養師推薦方案。</div>';
        return;
      }
      fetch(RAG_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query }),
      })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then(function (data) {
          var text = data.answer || '';
          // 完整性檢測：必須含三個小節標題
          var hasAll = /1\.?\s*各成分怎麼幫你/.test(text) &&
                           /2\.?\s*建議吃多少/.test(text) &&
                           /3\.?\s*什麼時候吃/.test(text);
          if (!hasAll && attempt <= 2) {
            tryOnce(attempt + 1);
            return;
          }
          if (!text) text = '暫時無法產生分析報告。';
          renderAiCards(targetEl, text);
        })
        .catch(function (err) {
          if (attempt <= 2) { tryOnce(attempt + 1); return; }
          targetEl.innerHTML =
            '<div style="color:#dc2626;line-height:1.7">AI 分析暫時無法使用（' + err.message + '）。您仍可參考上方營養師推薦方案，或預約免費諮詢由營養師為您解說。</div>';
        });
    }
    tryOnce(1);
  }

  // 把 Worker 回傳的 markdown 渲染成 wellness 風格卡片
  // 支援多種小節格式：## / ### / 1. / 一、 / 數字列表
  function renderAiCards(targetEl, md) {
    targetEl.innerHTML = '';
    md = cleanAiText(md);
    // 依小節切分（##、###、或行首 1. 2. 3. / 一、二、）
    const blocks = md.split(/^#{2,3}\s+|^[0-9]+[.、]\s+|^[一二三四五六七八九]+\s*、/m)
      .filter(function (s) { return s.trim(); });
    if (blocks.length <= 1) {
      // 沒有標準小節：降級成純文字卡片（保留 • 條列）
      const card = document.createElement('div');
      card.style.lineHeight = '1.7';
      card.style.color = '#374151';
      card.style.fontSize = '14px';
      card.innerHTML = formatBold(md.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>'));
      targetEl.appendChild(card);
      return;
    }
    blocks.forEach(function (block, idx) {
      const nl = block.indexOf('\n');
      const title = (nl === -1 ? block : block.slice(0, nl)).trim();
      const body = (nl === -1 ? '' : block.slice(nl + 1)).trim();

      const card = document.createElement('div');
      card.style.marginTop = idx === 0 ? '0' : '12px';
      card.style.padding = '14px 16px';
      card.style.borderRadius = '10px';
      card.style.background = '#fdf2f8';
      card.style.borderLeft = '4px solid #EC4899';

      const h = document.createElement('div');
      h.textContent = title;
      h.style.fontWeight = '700';
      h.style.fontSize = '15px';
      h.style.color = '#831843';
      h.style.marginBottom = '6px';
      card.appendChild(h);

      // 條列（• 或 - 或 * 或數字列表）
      const lines = body.split('\n').map(function (l) { return l.trim(); }).filter(function (l) { return l; });
      lines.forEach(function (line) {
        const item = document.createElement('div');
        item.style.lineHeight = '1.7';
        item.style.color = '#374151';
        item.style.fontSize = '14px';
        const clean = line.replace(/^[•\-\*]\s*/, '').replace(/^[0-9]+[.、]\s*/, '');
        item.innerHTML = '• ' + formatBold(clean);
        card.appendChild(item);
      });

      targetEl.appendChild(card);
    });
  }

  // 把 **粗體** 轉成 <b> 標籤（先 escape 防止 XSS）
  function formatBold(text) {
    const esc = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return esc.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  }

  // 去 AI 味：過濾模型偶發的模糊誇大詞（前端最後一道防線）
  function cleanAiText(text) {
    return text
      .replace(/顯著/g, '')
      .replace(/強效/g, '')
      .replace(/廣泛落在/g, '')
      .replace(/根據文獻/g, '')
      .replace(/一般建議/g, '')
      .replace(/正面影響/g, '明確作用')
      .replace(/支持（?[^）]*功能）?/g, '參與')
      .replace(/，舒緩焦慮與壓力/g, '，幫助放鬆')
      .replace(/，幫助放鬆。/g, '。');
  }

  // 渲染元件
  function createQuiz(container) {
    let currentStep = 0;
    const answers = {};

    function render() {
      container.innerHTML = '';

      const wrapper = document.createElement('div');
      wrapper.style.maxWidth = '720px';
      wrapper.style.margin = '0 auto';
      wrapper.style.padding = '24px';

      // Header
      const header = document.createElement('div');
      header.style.textAlign = 'center';
      header.style.marginBottom = '16px';
      const h1 = document.createElement('h2');
      h1.textContent = '營養需求檢測';
      h1.style.margin = '0 0 8px 0';
      h1.style.fontSize = '20px';
      const p = document.createElement('p');
      p.textContent = '回答 7 個問題，找到最適合您的保健方案';
      p.style.margin = '0';
      p.style.color = '#6b7280';
      header.appendChild(h1);
      header.appendChild(p);
      wrapper.appendChild(header);

      // progress
      const progressWrap = document.createElement('div');
      progressWrap.style.margin = '16px 0';
      const progressInfo = document.createElement('div');
      progressInfo.style.display = 'flex';
      progressInfo.style.justifyContent = 'space-between';
      progressInfo.style.fontSize = '14px';
      progressInfo.style.color = '#6b7280';
      progressInfo.textContent = '';
      const percent = Math.round(((currentStep + 1) / questions.length) * 100);
      progressInfo.textContent = `問題 ${currentStep + 1} / ${questions.length}    ${percent}%`;
      const prog = document.createElement('div');
      prog.style.background = '#e5e7eb';
      prog.style.height = '10px';
      prog.style.borderRadius = '999px';
      const bar = document.createElement('div');
      bar.style.width = percent + '%';
      bar.style.height = '100%';
      bar.style.background = '#2D6A4F';
      bar.style.borderRadius = '999px';
      prog.appendChild(bar);
      progressWrap.appendChild(progressInfo);
      progressWrap.appendChild(prog);
      wrapper.appendChild(progressWrap);

      // card
      const card = document.createElement('div');
      card.style.padding = '20px';
      card.style.borderRadius = '12px';
      card.style.boxShadow = '0 4px 12px rgba(0,0,0,0.06)';
      card.style.background = '#ffffff';

      if (currentStep < questions.length) {
        const q = questions[currentStep];
        const qh = document.createElement('h3');
        qh.textContent = q.question;
        qh.style.marginTop = '0';
        qh.style.marginBottom = '12px';
        card.appendChild(qh);

        const opts = document.createElement('div');
        opts.style.display = 'grid';
        opts.style.gap = '8px';

        q.options.forEach((opt) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.textContent = opt.label;
          btn.style.textAlign = 'left';
          btn.style.padding = '12px';
          btn.style.borderRadius = '10px';
          btn.style.border = '2px solid #e6e6e6';
          btn.style.background = answers[q.id] === opt.value ? '#e8f5ee' : '#fff';
          btn.addEventListener('click', function () {
            answers[q.id] = opt.value;
            render();
          });
          opts.appendChild(btn);
        });

        card.appendChild(opts);

        // nav
        const nav = document.createElement('div');
        nav.style.display = 'flex';
        nav.style.justifyContent = 'space-between';
        nav.style.marginTop = '16px';

        const back = document.createElement('button');
        back.type = 'button';
        back.textContent = '上一題';
        back.disabled = currentStep === 0;
        back.addEventListener('click', function () {
          if (currentStep > 0) {
            currentStep--;
            render();
          }
        });

        const next = document.createElement('button');
        next.type = 'button';
        next.textContent = currentStep === questions.length - 1 ? '查看結果' : '下一題';
        next.disabled = !answers[questions[currentStep].id];
        next.style.background = '#40916C';
        next.style.color = '#fff';
        next.style.border = 'none';
        next.style.padding = '8px 12px';
        next.style.borderRadius = '8px';
        next.addEventListener('click', function () {
          if (currentStep < questions.length - 1) {
            currentStep++;
            render();
          } else {
            showResult();
          }
        });

        nav.appendChild(back);
        nav.appendChild(next);
        card.appendChild(nav);
        wrapper.appendChild(card);
      }

      container.appendChild(wrapper);
    }

    function showResult() {
      container.innerHTML = '';
      const rec = getRecommendation(answers);

      const wrap = document.createElement('div');
      wrap.style.maxWidth = '720px';
      wrap.style.margin = '0 auto';
      wrap.style.padding = '24px';

      // 基本資料摘要
      const profileBox = document.createElement('div');
      profileBox.style.padding = '12px 16px';
      profileBox.style.borderRadius = '10px';
      profileBox.style.background = '#f0fdf4';
      profileBox.style.border = '1px solid #bbf7d0';
      profileBox.style.marginBottom = '16px';
      profileBox.style.fontSize = '14px';
      profileBox.style.color = '#166534';
      profileBox.style.lineHeight = '1.6';
      const g = profileLabels.gender[answers.gender] || '未填寫';
      const a = profileLabels.ageGroup[answers.ageGroup] || '未填寫';
      const grp = profileLabels.group[answers.group] || '一般族群';
      profileBox.innerHTML = '基本資料：<b>' + g + '</b> ・ <b>' + a + '</b> ・ <b>' + grp + '</b>';
      wrap.appendChild(profileBox);

      // 每日建議攝取量（台灣 DRIs 第八版）卡片
      const dris = getDrisBaseline(answers);
      const drisBox = document.createElement('div');
      drisBox.style.padding = '14px 16px';
      drisBox.style.borderRadius = '10px';
      drisBox.style.background = '#eff6ff';
      drisBox.style.border = '1px solid #bfdbfe';
      drisBox.style.marginBottom = '16px';
      drisBox.style.fontSize = '13px';
      drisBox.style.color = '#1e40af';
      drisBox.style.lineHeight = '1.8';
      const drisRows = [
        '鈣 ' + dris.calcium + ' mg',
        '鐵 ' + dris.iron + ' mg',
        '鋅 ' + dris.zinc + ' mg',
        '鎂 ' + dris.magnesium + ' mg',
        '維生素 D ' + dris.vitD + ' μg',
        '葉酸 ' + dris.folate + ' μg',
        'DHA ' + dris.dha + ' mg',
      ];
      drisBox.innerHTML = '<b>您的每日建議攝取量（台灣 DRIs 第八版）</b><br>' + drisRows.join('　・　');
      wrap.appendChild(drisBox);

      const header = document.createElement('div');
      header.style.textAlign = 'center';
      header.style.marginBottom = '16px';
      const h1 = document.createElement('h2');
      h1.textContent = '您的專屬推薦';
      h1.style.margin = '0 0 8px 0';
      const p = document.createElement('p');
      p.textContent = '根據您的回答，我們推薦以下方案';
      p.style.color = '#6b7280';
      header.appendChild(h1);
      header.appendChild(p);
      wrap.appendChild(header);

      const card = document.createElement('div');
      card.style.padding = '20px';
      card.style.borderRadius = '12px';
      card.style.boxShadow = '0 4px 12px rgba(0,0,0,0.06)';
      card.style.background = '#fff';

      const title = document.createElement('h3');
      title.textContent = rec.title;
      title.style.color = '#2D6A4F';
      card.appendChild(title);

      rec.products.forEach((pdt) => {
        const item = document.createElement('div');
        item.style.display = 'flex';
        item.style.justifyContent = 'space-between';
        item.style.padding = '10px';
        item.style.borderRadius = '8px';
        item.style.background = '#f8fafc';
        item.style.marginTop = '8px';

        const left = document.createElement('div');
        const name = document.createElement('div');
        name.textContent = pdt.name;
        name.style.fontWeight = '600';
        const reason = document.createElement('div');
        reason.textContent = pdt.reason;
        reason.style.color = '#6b7280';
        left.appendChild(name);
        left.appendChild(reason);

        const right = document.createElement('div');
        right.style.textAlign = 'right';
        right.style.flexShrink = '0';
        right.style.marginLeft = '12px';

        const price = document.createElement('div');
        price.textContent = pdt.price + ' 起';
        price.style.color = '#2D6A4F';
        price.style.fontWeight = '600';

        const buyLink = document.createElement('a');
        buyLink.href = pdt.url || SHOP_URL;
        buyLink.target = '_blank';
        buyLink.rel = 'noopener noreferrer';
        buyLink.textContent = '🛒 前往購買';
        buyLink.style.display = 'inline-block';
        buyLink.style.marginTop = '6px';
        buyLink.style.fontSize = '13px';
        buyLink.style.color = '#fff';
        buyLink.style.background = '#40916C';
        buyLink.style.padding = '4px 12px';
        buyLink.style.borderRadius = '999px';
        buyLink.style.textDecoration = 'none';

        right.appendChild(price);
        right.appendChild(buyLink);

        item.appendChild(left);
        item.appendChild(right);
        card.appendChild(item);
      });

      const adviceBox = document.createElement('div');
      adviceBox.style.marginTop = '12px';
      adviceBox.style.padding = '12px';
      adviceBox.style.borderRadius = '8px';
      adviceBox.style.background = '#eef7f1';
      adviceBox.textContent = '營養師建議：' + rec.advice;
      card.appendChild(adviceBox);

      wrap.appendChild(card);

      // --- AI 個人化分析報告（RAG，文獻佐證） ---
      const aiBox = document.createElement('div');
      aiBox.style.marginTop = '16px';
      aiBox.style.padding = '20px';
      aiBox.style.borderRadius = '12px';
      aiBox.style.background = '#fff';
      aiBox.style.boxShadow = '0 4px 12px rgba(0,0,0,0.06)';

      const aiTitle = document.createElement('h3');
      aiTitle.textContent = 'AI 分析報告';
      aiTitle.style.color = '#2D6A4F';
      aiTitle.style.marginTop = '0';
      aiBox.appendChild(aiTitle);

      const aiBody = document.createElement('div');
      aiBody.style.lineHeight = '1.7';
      aiBody.style.color = '#374151';
      aiBody.innerHTML = '<div style="color:#6b7280;font-size:14px">正在根據科學文獻為您產生個人化分析（約需 10–20 秒）…</div>';
      aiBox.appendChild(aiBody);
      wrap.appendChild(aiBox);

      fetchAiReport(rec, answers, aiBody);

      // CTA
      const ctas = document.createElement('div');
      ctas.style.marginTop = '16px';
      ctas.style.display = 'grid';
      ctas.style.gap = '8px';

      const buy = document.createElement('a');
      buy.href = 'https://drnutrii.1shop.tw/HUG';
      buy.target = '_blank';
      buy.rel = 'noopener noreferrer';
      buy.textContent = '立即選購推薦產品';
      buy.style.display = 'inline-block';
      buy.style.textAlign = 'center';
      buy.style.background = '#40916C';
      buy.style.color = '#fff';
      buy.style.padding = '10px';
      buy.style.borderRadius = '999px';

      const consult = document.createElement('a');
      consult.href = 'https://line.me/R/ti/p/@452lxymx';
      consult.target = '_blank';
      consult.rel = 'noopener noreferrer';
      consult.textContent = '預約免費諮詢，了解更多';
      consult.style.display = 'inline-block';
      consult.style.textAlign = 'center';
      consult.style.border = '1px solid #e6e6e6';
      consult.style.padding = '10px';
      consult.style.borderRadius = '999px';

      const restart = document.createElement('button');
      restart.textContent = '重新測驗';
      restart.addEventListener('click', function () {
        currentStep = 0;
        for (const k in answers) delete answers[k];
        render();
      });
      restart.style.background = 'transparent';
      restart.style.border = 'none';
      restart.style.color = '#6b7280';

      ctas.appendChild(buy);
      ctas.appendChild(consult);
      ctas.appendChild(restart);
      wrap.appendChild(ctas);

      container.appendChild(wrap);
    }

    render();
  }

  // auto init
  document.addEventListener('DOMContentLoaded', function () {
    const mount = document.getElementById('nutrition-quiz');
    if (mount) createQuiz(mount);
  });
})();
