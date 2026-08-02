# -*- coding: utf-8 -*-
"""
Generate 6 single-article detail pages + rewrite articles.html as an index.
Run: python build_articles.py
"""
import datetime, html

BASE = "https://storage.googleapis.com/kidson_dietitian/kidson_dietitian_profile"
TODAY = "2025-06-20"

# Shared footer (identical across site)
FOOTER = '''
    <!-- 頁腳 -->
    <footer class="footer">
        <div class="container">
            <div class="row">
                <div class="col-md-4 mb-3 mb-md-0">
                    <h5>聯絡資訊</h5>
                    <ul class="list-unstyled">
                        <li><a href="https://lin.ee/ZDUOvpG"><img src="https://scdn.line-apps.com/n/line_add_friends/btn/zh-Hant.png" alt="加入好友" height="36" border="0" loading="lazy"></a></li>
                        <li><i class="fas fa-envelope me-2"></i>kidson7911@gmail.com</li>
                    </ul>
                </div>
                <div class="col-md-4 mb-3 mb-md-0">
                    <h5>快速連結</h5>
                    <ul class="list-unstyled">
                        <li><a href="index.html" class="text-white">首頁</a></li>
                        <li><a href="services_info.html" class="text-white">服務</a></li>
                        <li><a href="articles.html" class="text-white">衛教文章</a></li>
                        <li><a href="about.html" class="text-white">關於我</a></li>
                        <li><a href="contact.html" class="text-white">預約諮詢</a></li>
                    </ul>
                </div>
                <div class="col-md-4">
                    <h5>關注我</h5>
                    <ul class="list-inline">
                        <li class="list-inline-item"><a href="https://www.facebook.com/kidsonnutritionist" class="text-white"><i class="fab fa-facebook fa-2x"></i></a></li>
                        <li class="list-inline-item"><a href="https://www.instagram.com/kidsondietitian" class="text-white"><i class="fab fa-instagram fa-2x"></i></a></li>
                    </ul>
                </div>
            </div>
            <hr class="my-4 bg-light">
            <p>© 2025 Kidson營養師. All Rights Reserved.</p>
            <p><small>網站地圖 | 隱私政策 | 服務條款</small></p>
        </div>
    </footer>
'''

NAV = '''
    <!-- 導航欄 -->
    <nav class="navbar navbar-expand-lg navbar-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="index.html">Kidson營養師</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link" href="index.html">首頁</a></li>
                    <li class="nav-item"><a class="nav-link" href="services_info.html">服務</a></li>
                    <li class="nav-item"><a class="nav-link" href="quiz.html">健康檢測</a></li>
                    <li class="nav-item"><a class="nav-link" href="articles.html">衛教文章</a></li>
                    <li class="nav-item"><a class="nav-link" href="about.html">關於我</a></li>
                    <li class="nav-item"><a class="nav-link" href="contact.html">聯繫我</a></li>
                </ul>
            </div>
        </div>
    </nav>
'''

SCRIPTS = '''
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <!-- AOS JS -->
    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <!-- Font Awesome -->
    <script src="https://kit.fontawesome.com/031b362d26.js" crossorigin="anonymous"></script>
    <!-- Custom JS -->
    <script>
        AOS.init({ duration: 1000, once: true });
        const navbarEl = document.querySelector('.navbar');
        const navObserver = new IntersectionObserver(([entry]) => {
            navbarEl.classList.toggle('scrolled', !entry.isIntersecting);
        }, { rootMargin: '-0px 0px 0px 0px', threshold: 0 });
        const headerSection = document.querySelector('.contact-header');
        if (headerSection && navbarEl) {
            const sentinel = document.createElement('div');
            sentinel.setAttribute('data-nav-sentinel', 'true');
            headerSection.appendChild(sentinel);
            navObserver.observe(sentinel);
        }
        document.querySelectorAll('.nav-link, .navbar-brand, a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                if (href.startsWith('#')) {
                    e.preventDefault();
                    const t = document.getElementById(href.substring(1));
                    if (t) window.scrollTo({ top: t.offsetTop - 70, behavior: 'smooth' });
                }
            });
        });
    </script>
'''

# Article specs ---------------------------------------------------------------
ARTICLES = [
    {
        "file": "article-1-control-sugar.html",
        "cat": "減重",
        "cat_en": "weight",
        "img": "img/svc_weight.jpg",
        "title": "減重不用餓肚子：營養師的5個科學控醣技巧",
        "desc": "減重不是比誰吃得少，而是比誰吃得聰明。掌握控醣順序與蛋白質分配，就能在吃飽的前提下穩定體重。營養師的5個實證技巧一次看。",
        "keywords": "減重技巧,控醣,減肥不吃飽,低GI飲食,餐盤順序,減重蛋白質,科學減重",
        "read": "4 分鐘",
        "body": '''
<p class="lead-p">很多人一聽到減重就想到「挨餓」，但極端節食不只難以堅持，還會讓基礎代謝下降、肌肉流失，反而更容易復胖。以下 5 個技巧，幫你用科學方式控醣：</p>

<h2>1. 溫和熱量缺口，不求速效</h2>
<p>每天比維持熱量少 300–500 大卡，約每週穩定減 0.3–0.5 公斤，是身體較能長期承受的速度，也較不易掉肌肉。速效減重多半減掉的是水分與肌肉，停掉就復胖。</p>

<h2>2. 餐盤進食順序：菜 → 肉 → 飯</h2>
<p>先吃蔬菜（膳食纖維）與蛋白質，最後吃澱粉，能讓餐後血糖上升更平緩，飽足感更持久，自然少吃幾口飯。這是最簡單、不用算熱量就能執行的方法。</p>

<h2>3. 選低 GI 澱粉</h2>
<p>以糙米、五穀飯、地瓜、燕麥取代白飯與白麵包，消化較慢、較耐餓，也有助於血糖控制。同樣份量，選對種類就能減少飢餓感。</p>

<h2>4. 每餐一掌心優質蛋白質</h2>
<p>豆魚蛋肉奶各類輪替，蛋白質能維持肌肉量、提高食物產熱效應，是減重期的「抗餓神隊友」。肌肉量守住，基礎代謝才不會掉。</p>

<h2>5. 喝水與睡眠別忽略</h2>
<p>身體有時會把「渴」誤認成「餓」；每天 2000 cc 水分、充足睡眠能減少假性飢餓與夜間嘴饞。睡不好時皮質醇上升，更容易囤積腹部脂肪。</p>

<div class="article-cta-inline">
    <p>想針對自己的體重目標設計菜單？讓營養師幫你算熱量與份量。</p>
    <a href="contact.html" class="btn btn-primary">預約個人化減重諮詢</a>
</div>
'''
    },
    {
        "file": "article-2-eating-out.html",
        "cat": "外食技巧",
        "cat_en": "eating",
        "img": "img/svc_diet.jpg",
        "title": "便當、自助餐、火鍋這樣點，外食也能瘦",
        "desc": "外食 ≠ 減重破功。掌握便當、自助餐、火鍋三大常見場景的點餐邏輯，一樣能吃得均衡、熱量不爆表。營養師實測點法公開。",
        "keywords": "外食減肥,便當怎麼吃,自助餐減肥,火鍋減肥,外食技巧,減重外食,健康外食",
        "read": "5 分鐘",
        "body": '''
<p class="lead-p">外食 ≠ 減重破功。掌握三大常見場景的點餐邏輯，一樣能吃得均衡、熱量不爆表。</p>

<h2>便當：聰明替換配菜</h2>
<ul>
    <li>主食換糙米或五穀飯，吃不下的飯可留 1/3。</li>
    <li>青菜加點一份，纖維吃足更耐餓。</li>
    <li>主菜選去皮雞腿、滷魚、蒸蛋，少選炸物。</li>
    <li>湯汁、醬汁別拌飯，隱藏油鹽都在裡面。</li>
</ul>

<h2>自助餐：先夾菜再夾肉</h2>
<ul>
    <li>盤子一半給蔬菜，1/4 給豆魚蛋肉，1/4 給澱粉。</li>
    <li>烹調方式以蒸、煮、清炒優先，避免糖醋與裹粉油炸。</li>
    <li>勾芡濃汁（如咖哩、羹湯）熱量密度高，淺嚐即可。</li>
</ul>

<h2>火鍋：清湯底最穩</h2>
<ul>
    <li>湯底選昆布、番茄、清湯，避開牛奶與麻辣鍋。</li>
    <li>多放葉菜與菇類，蛋白質選豆腐、雞肉片、魚片原態食材。</li>
    <li>加工餃類、丸子熱量高，淺嚐；沾醬用蔥薑蒜＋醋＋少許醬油，取代沙茶。</li>
</ul>

<p>飲料一律無糖茶或氣泡水，就能再省下 300–500 大卡。</p>

<div class="article-cta-inline">
    <p>常外食不知道怎麼搭配？交給營養師幫你排一週外食菜單。</p>
    <a href="services_info.html" class="btn btn-primary">看外食飲食規劃服務</a>
</div>
'''
    },
    {
        "file": "article-3-protein.html",
        "cat": "減重",
        "cat_en": "weight",
        "img": "img/page_combo.jpg",
        "title": "減重期蛋白質吃多少？一張表算給你",
        "desc": "蛋白質是減重期的核心營養素。用體重就能簡單算出每日需求，避免掉肌肉、復胖。營養師教你分配與優質來源。",
        "keywords": "減重蛋白質,蛋白質攝取量,蛋白質計算,減重不掉肌肉,高蛋白飲食,營養師蛋白質",
        "read": "3 分鐘",
        "body": '''
<p class="lead-p">蛋白質是減重期的核心營養素。用體重就能簡單算出每日需求，避免掉肌肉、復胖。</p>

<p>一般成人每日蛋白質建議約 0.8 g/kg；若有減重或規律運動需求，可提高到 <strong>1.2–1.6 g/kg</strong>，有助維持肌肉、增加飽足。</p>

<h2>快速估算</h2>
<ul>
    <li>50 kg → 約 60–80 g/天</li>
    <li>60 kg → 約 72–96 g/天</li>
    <li>70 kg → 約 84–112 g/天</li>
</ul>

<h2>怎麼分配最省力</h2>
<p>把份量分散到三餐，每餐約「一個掌心」的豆魚蛋肉奶；例如早餐無糖豆漿＋蛋、午餐雞胸、晚餐魚或豆腐，就能輕鬆達標。</p>

<h2>優質來源這樣搭</h2>
<ul>
    <li>動物性：雞肉、魚、蛋、乳製品</li>
    <li>植物性：豆腐、毛豆、無糖豆漿、黑豆</li>
    <li>植物＋動物交替，胺基酸更完整</li>
</ul>

<p class="mt-3">蛋白質消化需要較多能量（食物產熱效應），又能延長飽足，是減重菜單裡最該顧好的營養素。</p>

<div class="article-cta-inline">
    <p>不確定自己每天吃夠了沒？營養諮詢幫你精算每日份量。</p>
    <a href="contact.html" class="btn btn-primary">預約營養諮詢</a>
</div>
'''
    },
    {
        "file": "article-4-breakfast.html",
        "cat": "減重",
        "cat_en": "weight",
        "img": "img/page_consult.jpg",
        "title": "早餐決定代謝：3款低GI早餐範例",
        "desc": "跳過早餐容易午餐暴飲暴食。三款方便準備、低GI又抗餓的早餐，幫你穩住一整天的食慾與代謝。",
        "keywords": "低GI早餐,減重早餐,早餐範例,健康早餐,控制食慾,代謝早餐,減肥早餐",
        "read": "3 分鐘",
        "body": '''
<p class="lead-p">吃對早餐能啟動一天的代謝、避免午後嘴饞。關鍵是「蛋白質＋低GI碳水＋纖維」的組合，避開純糖類與精緻澱粉。</p>

<h2>範例一：中式均衡組</h2>
<p>無糖豆漿 1 杯 ＋ 全麥吐司 1 片 ＋ 水煮蛋 1 顆 ＋ 小番茄 5–6 顆。</p>

<h2>範例二：優格燕麥碗</h2>
<p>無糖希臘優格 ＋ 燕麥片 3 湯匙 ＋ 堅果 1 小把 ＋ 藍莓少許。</p>

<h2>範例三：地瓜拿鐵組</h2>
<p>蒸地瓜 1 小條 ＋ 茶葉蛋 1 顆 ＋ 無糖拿鐵（或鮮奶）。</p>

<h2>早餐地雷</h2>
<ul>
    <li>含糖果汁、蜂蜜檸檬：液態糖，血糖起伏大</li>
    <li>可頌、奶油麵包：高油高糖，飽足感短</li>
    <li>玉米片/含糖穀片：看似健康，實則空熱量</li>
</ul>

<div class="article-cta-inline">
    <p>想建立適合自己的早餐與全天飲食節奏？來做一對一諮詢。</p>
    <a href="contact.html" class="btn btn-primary">預約營養諮詢</a>
</div>
'''
    },
    {
        "file": "article-5-hidden-calories.html",
        "cat": "外食技巧",
        "cat_en": "eating",
        "img": "img/service2.jpg",
        "title": "上班族外食隱藏熱量排行與替代",
        "desc": "真正讓人變胖的往往不是正餐，而是那些「以為沒關係」的飲料、醬料與下午茶。營養師幫你抓出隱形熱量與替代方案。",
        "keywords": "隱藏熱量,外食熱量,手搖飲熱量,上班族減肥,下午茶熱量,便利商店選擇,隱形熱量",
        "read": "4 分鐘",
        "body": '''
<p class="lead-p">真正讓人變胖的往往不是正餐，而是那些「以為沒關係」的飲料、醬料與下午茶。幫你抓出隱形熱量。</p>

<h2>隱藏熱量排行（估算）</h2>
<ul>
    <li>全糖奶茶 / 手搖飲：約 400–500 大卡，相當於一碗飯</li>
    <li>炸物（薯條、雞塊）：吸油量高，一份可破 300 大卡</li>
    <li>勾芡濃湯、羹類：澱粉＋油，一碗約 150–250 大卡</li>
    <li>沙拉醬（千島、凱薩）：2 湯匙就可能 150 大卡</li>
    <li>下午茶蛋糕：一塊約 300–400 大卡</li>
</ul>

<h2>聰明替代</h2>
<ul>
    <li>飲料：無糖茶、黑咖啡、氣泡水，或微糖去冰</li>
    <li>烹調：以烤、氣炸、蒸煮取代油炸</li>
    <li>湯品：選清湯，避開勾芡</li>
    <li>沙拉醬：油醋醬、和風醬，或檸檬汁代替</li>
    <li>下午茶：水果、無糖優格、堅果一小把</li>
</ul>

<h2>便利商店聰明選</h2>
<p>茶葉蛋、無糖希臘優格、原味堅果、蒸地瓜，都是熱量可控、營養實在的好選擇。</p>

<div class="article-cta-inline">
    <p>每天一杯手搖飲就多一份熱量？讓營養師幫你找出口。</p>
    <a href="services_info.html" class="btn btn-primary">看飲食規劃服務</a>
</div>
'''
    },
    {
        "file": "article-6-plateau.html",
        "cat": "減重",
        "cat_en": "weight",
        "img": "img/svc_chronic.jpg",
        "title": "遇到減重平台期怎麼辦？4個可能原因",
        "desc": "體重卡關別慌，平台期很常見。先釐清原因，再對症調整，比盲目少吃更有效。營養師整理4個常見原因與對策。",
        "keywords": "減重平台期,體重卡關,減重停滯,突破平台期,減重遇瓶頸,代謝適應,減重對策",
        "read": "4 分鐘",
        "body": '''
<p class="lead-p">體重卡關別慌，平台期很常見。先釐清原因，再對症調整，比盲目少吃更有效。</p>

<h2>1. 身體在適應</h2>
<p>體重下降後，維持熱量也跟著降低，原本的缺口變小，體重自然停滯。這時可微調活動量或重新計算需求。</p>

<h2>2. 熱量被低估</h2>
<p>隱藏的油、糖、醬料與「試吃」都會累積。建議回到 1–2 週的飲食紀錄，誠實盤點真實攝取。</p>

<h2>3. 水分與肌肉波動</h2>
<p>鹽分、生理期、開始運動後的肌肉儲水，都會讓體重數字短期不動，甚至上升；可看腰圍與體脂變化，不只看體重機。</p>

<h2>4. 睡眠與壓力</h2>
<p>壓力賀爾蒙（皮質醇）偏高會影響脂肪代謝與食慾。規律睡眠、適度紓壓，對突破平台期同樣關鍵。</p>

<p class="mt-3">小提醒：增加非運動活動消耗（NEAT），例如多走路、爬樓梯、多站立，是溫和又容易堅持的突破方式。</p>

<div class="article-cta-inline">
    <p>卡關很久？先做健康檢測，了解自己的體態風險與方向。</p>
    <a href="quiz.html" class="btn btn-primary">先做健康檢測</a>
</div>
'''
    },
]


def breadcrumb(a):
    return f'''
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb-k">
        <li><a href="index.html">首頁</a></li>
        <li><a href="articles.html">衛教文章</a></li>
        <li aria-current="page">{html.escape(a['title'])}</li>
      </ol>
    </nav>
'''

def related_sidebar(current_file):
    items = [a for a in ARTICLES if a['file'] != current_file]
    # show 3 related (prefer same category, else others)
    cur = next(a for a in ARTICLES if a['file'] == current_file)
    same = [a for a in items if a['cat'] == cur['cat']]
    others = [a for a in items if a['cat'] != cur['cat']]
    picks = (same + others)[:3]
    lis = "\n".join(
        f'        <a class="related-item" href="{a["file"]}"><img class="related-thumb" src="{a["img"]}" alt="{html.escape(a["title"])}" loading="lazy"><span>{html.escape(a["title"])}</span></a>'
        for a in picks
    )
    return f'''
            <div class="side-card">
                <h4>相關文章</h4>
{lis}
            </div>
            <div class="side-card">
                <h4>需要個人化建議？</h4>
                <p class="mb-3">把這些技巧交給營養師，變成專屬你的可執行菜單。</p>
                <a href="contact.html" class="btn btn-primary btn-sm">預約營養諮詢</a>
            </div>
'''

def build_detail(a):
    url = f"{BASE}/{a['file']}"
    jsonld = f'''
    <!-- Article JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "{a['title']}",
      "description": "{a['desc']}",
      "image": "{BASE}/{a['img']}",
      "datePublished": "{TODAY}",
      "dateModified": "{TODAY}",
      "author": {{ "@type": "Person", "name": "Kidson營養師" }},
      "publisher": {{
        "@type": "Organization",
        "name": "Kidson營養師",
        "logo": {{ "@type": "ImageObject", "url": "{BASE}/img/photo.jpg" }}
      }},
      "mainEntityOfPage": "{url}",
      "articleSection": "{a['cat']}",
      "inLanguage": "zh-TW"
    }}
    </script>

    <!-- Breadcrumb JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{ "@type": "ListItem", "position": 1, "name": "首頁", "item": "{BASE}/index.html" }},
        {{ "@type": "ListItem", "position": 2, "name": "衛教文章", "item": "{BASE}/articles.html" }},
        {{ "@type": "ListItem", "position": 3, "name": "{a['title']}", "item": "{url}" }}
      ]
    }}
    </script>
'''
    page = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-0JX194EGE5"></script>
    <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-0JX194EGE5');
    </script>

    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{a['title']}｜Kidson營養師</title>
    <meta name="description" content="{a['desc']}">
    <meta name="keywords" content="{a['keywords']}">
    <meta name="author" content="Kidson營養師">
    <meta name="robots" content="index, follow">
    <meta name="revisit-after" content="7 days">
    <meta name="geo.region" content="TW-TPE">
    <meta name="geo.placename" content="台北市">
    <meta name="geo.position" content="25.0330;121.5654">
    <meta name="ICBM" content="25.0330, 121.5654">

    <meta property="og:type" content="article">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="{a['title']}｜Kidson營養師">
    <meta property="og:description" content="{a['desc']}">
    <meta property="og:image" content="{BASE}/{a['img']}">
    <meta property="og:site_name" content="Kidson營養師">
    <meta property="og:locale" content="zh_TW">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{a['title']}｜Kidson營養師">
    <meta name="twitter:description" content="{a['desc']}">
    <meta name="twitter:image" content="{BASE}/{a['img']}">
    <meta name="twitter:site" content="@kidsonnutritionist">

    <link rel="canonical" href="{url}">
    <link rel="icon" href="img/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" sizes="180x180" href="img/apple-touch-icon.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://cdn.jsdelivr.net">
    <link rel="preconnect" href="https://unpkg.com">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
    <link rel="stylesheet" href="css/style.css">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Noto+Serif+TC:wght@600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
{jsonld}
</head>
<body>
{NAV}

    <section class="contact-header">
        <div class="container">
            <span class="section-label" data-aos="fade-up">Health Article</span>
            <h1 data-aos="fade-up">衛教文章</h1>
            <p class="lead" data-aos="fade-up" data-aos-delay="100">減重 × 外食技巧，營養師帶你吃對、瘦得健康</p>
        </div>
    </section>

    <section class="section bg-light">
        <div class="container">
            <div class="row g-5">
                <div class="col-lg-8" data-aos="fade-up">
                    <article class="article-detail">
{breadcrumb(a)}
                        <img class="article-hero" src="{a['img']}" alt="{html.escape(a['title'])}" loading="lazy">
                        <div class="article-byline">
                            <span class="cat-tag">{a['cat']}</span>
                            <span><i class="far fa-calendar me-1"></i>{TODAY}</span>
                            <span><i class="far fa-clock me-1"></i>閱讀 {a['read']}</span>
                            <span><i class="far fa-user me-1"></i>Kidson營養師</span>
                        </div>
                        <div class="article-content">
                            <h1>{a['title']}</h1>
{a['body']}
                        </div>
                        <div class="mt-4">
                            <a href="articles.html" class="btn btn-outline-primary"><i class="fas fa-arrow-left me-1"></i> 回到文章列表</a>
                            <a href="contact.html" class="btn btn-primary float-end">預約營養諮詢</a>
                        </div>
                    </article>
                </div>
                <div class="col-lg-4" data-aos="fade-up" data-aos-delay="100">
{related_sidebar(a['file'])}
                </div>
            </div>
        </div>
    </section>

{FOOTER}
{SCRIPTS}
</body>
</html>
'''
    return page


def build_index():
    cards = []
    for a in ARTICLES:
        cards.append(f'''
                <div class="col-lg-4 col-md-6 mb-4" data-aos="fade-up">
                    <article class="article-card">
                        <div class="article-card-img">
                            <img src="{a['img']}" alt="{html.escape(a['title'])}" loading="lazy">
                            <span class="article-badge">{a['cat']}</span>
                        </div>
                        <div class="article-card-body">
                            <div class="article-meta"><i class="far fa-calendar me-1"></i>{TODAY} · 閱讀 {a['read']}</div>
                            <h3 class="article-card-title">{html.escape(a['title'])}</h3>
                            <p class="article-excerpt">{html.escape(a['desc'])}</p>
                            <div class="article-toggle mt-auto pt-3">
                                <a href="{a['file']}" class="btn btn-link article-toggle-btn p-0">閱讀全文 <i class="fas fa-arrow-right"></i></a>
                            </div>
                        </div>
                    </article>
                </div>''')
    cards_html = "\n".join(cards)

    jsonld = f'''
    <!-- CollectionPage JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      "name": "營養衛教文章｜減重與外食技巧",
      "description": "由 Kidson 營養師撰寫的減重與外食技巧衛教文章彙整。",
      "url": "{BASE}/articles.html",
      "inLanguage": "zh-TW",
      "mainEntity": {{
        "@type": "ItemList",
        "numberOfItems": {len(ARTICLES)},
        "itemListElement": [
'''

    item_ld = ",\n".join(
        f'          {{ "@type": "ListItem", "position": {i+1}, "item": {{ "@type": "Article", "headline": "{a["title"]}", "author": {{ "@type": "Person", "name": "Kidson營養師" }}, "datePublished": "{TODAY}", "articleSection": "{a["cat"]}" }} }}'
        for i, a in enumerate(ARTICLES)
    )
    jsonld += item_ld + "\n        ]\n      }\n    }\n    </script>\n"

    page = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-0JX194EGE5"></script>
    <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-0JX194EGE5');
    </script>

    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>營養衛教文章｜減重與外食技巧大全 — Kidson營養師</title>
    <meta name="description" content="營養師整理的減重與外食技巧衛教文章：科學控醣、便當火鍋怎麼點、減重期蛋白質攝取、低GI早餐、隱藏熱量與平台期對策。實用、可執行，幫你吃對也瘦得健康。">
    <meta name="keywords" content="營養衛教,減重技巧,外食技巧,減肥,熱量控制,低GI飲食,蛋白質攝取,外食減肥,便當怎麼吃,火鍋減肥,減重平台期,營養師文章,健康飲食">
    <meta name="author" content="Kidson營養師">
    <meta name="robots" content="index, follow">
    <meta name="geo.region" content="TW-TPE">
    <meta name="geo.placename" content="台北市">
    <meta name="geo.position" content="25.0330;121.5654">
    <meta name="ICBM" content="25.0330, 121.5654">
    <meta name="revisit-after" content="7 days">
    <meta name="distribution" content="global">
    <meta name="rating" content="general">

    <meta property="og:type" content="website">
    <meta property="og:url" content="{BASE}/articles.html">
    <meta property="og:title" content="營養衛教文章｜減重與外食技巧大全 — Kidson營養師">
    <meta property="og:description" content="營養師整理的減重與外食技巧衛教文章：科學控醣、便當火鍋怎麼點、減重期蛋白質攝取、低GI早餐與平台期對策。">
    <meta property="og:image" content="{BASE}/img/svc_weight.jpg">
    <meta property="og:site_name" content="Kidson營養師">
    <meta property="og:locale" content="zh_TW">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="營養衛教文章｜減重與外食技巧大全 — Kidson營養師">
    <meta name="twitter:description" content="營養師整理的減重與外食技巧衛教文章，實用可執行，幫你吃對也瘦得健康。">
    <meta name="twitter:image" content="{BASE}/img/svc_weight.jpg">
    <meta name="twitter:site" content="@kidsonnutritionist">

    <link rel="canonical" href="{BASE}/articles.html">
    <link rel="icon" href="img/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" sizes="180x180" href="img/apple-touch-icon.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://cdn.jsdelivr.net">
    <link rel="preconnect" href="https://unpkg.com">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
    <link rel="stylesheet" href="css/style.css">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Noto+Serif+TC:wght@600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
{jsonld}
</head>
<body>
{NAV}

    <section class="contact-header">
        <div class="container">
            <span class="section-label" data-aos="fade-up">Health Articles</span>
            <h1 data-aos="fade-up">營養衛教文章</h1>
            <p class="lead" data-aos="fade-up" data-aos-delay="100">減重 × 外食技巧，營養師帶你吃對、瘦得健康</p>
        </div>
    </section>

    <section class="section bg-light">
        <div class="container">
            <div class="section-header" data-aos="fade-up">
                <span class="section-label">衛教專欄</span>
                <h2 class="section-title">精選減重與外食技巧</h2>
                <p class="section-subtitle">由臨床營養師整理，融合實證營養與台灣飲食實況，幫你把知識變成餐桌上的行動。</p>
                <div class="section-divider"></div>
            </div>

            <div class="row" id="articleGrid">
{cards_html}
            </div>
        </div>
    </section>

    <section class="cta-section">
        <div class="container text-center">
            <h3 data-aos="fade-up">文章看完了，想針對自己的狀況調整飲食？</h3>
            <p class="mb-4" data-aos="fade-up" data-aos-delay="100">把這些技巧交給營養師，變成專屬你的可執行菜單。</p>
            <a href="contact.html" class="btn btn-primary btn-lg" data-aos="fade-up" data-aos-delay="200">立即預約營養諮詢</a>
        </div>
    </section>

{FOOTER}
{SCRIPTS}
</body>
</html>
'''
    return page


if __name__ == "__main__":
    for a in ARTICLES:
        with open(a["file"], "w", encoding="utf-8") as f:
            f.write(build_detail(a))
        print("wrote", a["file"])
    with open("articles.html", "w", encoding="utf-8") as f:
        f.write(build_index())
    print("wrote articles.html (index)")
