# Kidson營養師 SEO 優化指南

## ✅ 已完成的 SEO 優化項目

### 1. Meta 標籤優化

#### 基本 SEO 標籤
- [x] `<meta charset="UTF-8">` - 放在第一行
- [x] `<meta name="viewport">` - 設置響應式設計
- [x] `<title>` - 每頁獨特的標題（70-80字元）
- [x] `<meta name="description">` - 150-160字元的獨特描述
- [x] `<meta name="keywords">` - 相關關鍵字
- [x] `<meta name="author">` - 作者信息
- [x] `<meta name="robots">` - 指示搜索引擎索引和追蹤

#### 地方 SEO 標籤
- [x] `<meta name="geo.region">` - 地區代碼 (TW-TPE)
- [x] `<meta name="geo.placename">` - 城市名稱
- [x] `<meta name="geo.position">` - 緯度和經度
- [x] `<meta name="ICBM">` - 國際地理坐標

#### 社交媒體優化 (Open Graph)
- [x] `og:type` - 網站類型 (website/profile)
- [x] `og:url` - 標準化的 URL
- [x] `og:title` - 社交媒體顯示標題
- [x] `og:description` - 社交媒體顯示描述
- [x] `og:image` - 社交媒體分享圖片
- [x] `og:site_name` - 網站名稱
- [x] `og:locale` - 地區設定 (zh_TW)

#### Twitter Card 優化
- [x] `twitter:card` - 卡片類型 (summary_large_image)
- [x] `twitter:title` - Twitter 標題
- [x] `twitter:description` - Twitter 描述
- [x] `twitter:image` - Twitter 圖片
- [x] `twitter:site` - Twitter 賬號
- [x] `twitter:creator` - 創作者標識

#### 網頁性能
- [x] `<link rel="preconnect">` - 提前連接第三方資源
- [x] `<link rel="canonical">` - 標準化 URL（避免重複內容）
- [x] `<link rel="alternate">` - 多語言版本標識

### 2. 結構化數據 (Schema.org)

#### 首頁 - Professional Service Schema
- [x] `@type: Nutritionist` - 營養師類型
- [x] 聯繫信息（電話、 email、地址）
- [x] 經營時間規範
- [x] 社交媒體連結
- [x] 提供的服務列表（4項服務）
- [x] 總評分（AggregateRating）

#### 關於頁面 - Person Schema
- [x] `@type: Person` - 個人類型
- [x] 學歷信息（校友）
- [x] 證書信息
- [x] 專業經歷

#### 聯繫頁面 - Contact Page Schema
- [x] `@type: ContactPage` - 聯繫頁面類型
- [x] 主要實體信息

#### 服務頁面 - Service Schema
- [x] `@type: Service` - 服務類型
- [x] 服務詳細描述
- [x] 提供者信息
- [x] 服務區域
- [x] 價格信息

### 3. 網站結構優化

#### 站點文件
- [x] `robots.txt` - 搜索引擎爬蟲指令
- [x] `sitemap.xml` - 網站地圖

#### 站點結構
- [x] 首頁 (index.html) - Priority: 1.0
- [x] 關於我 (about.html) - Priority: 0.8
- [x] 聯繫我 (contact.html) - Priority: 0.8
- [x] 服務頁面 (services_info.html) - Priority: 0.9
- [x] 單獨服務頁面 (service_1-4.html) - Priority: 0.7

### 4. 前端性能優化

#### JavaScript 優化
- [x] 創建 `js/seo.js` 文件
- [x] 圖片延遲加載 (IntersectionObserver)
- [x] 結構化數據驗證
- [x] 內部連結分析
- [x] 頁面加載性能監測
- [x] 無障礙性增強（跳過連結、ARIA 標籤）
- [x] 圖片 alt 文字自動補充

### 5. 內容優化

#### 首頁
- [x] H1 標籤 "專業營養師諮詢服務"
- [x] 關鍵字密度優化
- [x] 內部連結結構
- [x] FAQ 區塊（提升用戶停留時間）
- [x] 客戶見證（社會證明）

#### 關於頁面
- [x] H1 標籤 "關於我"
- [x] 教育背景詳細列出
- [x] 證書信息明確標註
- [x] 專業經歷時間軸

#### 聯繫頁面
- [x] H1 標籤 "聯繫我"
- [x] 聯繫信息清晰
- [x] 預約系統

### 6. 移動優化
- [x] 响應式設計
- [x] 媒體查詢 (media queries)
- [x] 觸摸友好的按鈕大小
- [x] 移動導航

### 7. GA4 預約轉換追蹤（contact.html）

預約頁 `contact.html` 已埋 GA4 事件，與現有 `gtag`（G-0JX194EGE5）共用。所有事件 `event_category` 皆為 `booking`。

#### 已埋事件清單
| 事件名稱 | 觸發時機 | 參數 | 防重複 |
|---|---|---|---|
| `view_booking_calendar` | 日曆區塊滾動進入視窗（≥40%） | `method: google_calendar` | IntersectionObserver 觸發一次後 `disconnect()` |
| `interact_booking_calendar` | 使用者點擊 / 聚焦日曆 iframe | `method: google_calendar` | 首次觸發後移除監聽 |
| `click_line_booking` | 點擊「加 LINE 直接預約」按鈕 | `method: line` | 每次點擊計（高意圖） |

#### 埋碼位置（contact.html 內聯 script）
```js
function trackBookingEvent(action, params) {
  if (typeof gtag === 'function') {
    gtag('event', action, Object.assign({ event_category: 'booking' }, params || {}));
  }
}
// view：IntersectionObserver(threshold 0.4) → view_booking_calendar
// interact：calEl click/focusin → interact_booking_calendar
// LINE：a[href*="lin.ee"] click → click_line_booking
```

#### GA4 後台需手動設定（否則報表看不到轉換）
1. **標記為轉換**：GA4 後台 → 報表 → 事件 → 找到 `click_line_booking`、`interact_booking_calendar` → 開啟「標記為轉換（關鍵事件）」。
2. **（選用）Google Ads 匯入**：GA4 → 廣告偏好設定 → 連結 Google Ads → 把上述事件匯入為 Ads 轉換。
3. 詳細圖文步驟見 `ga4-booking-setup.html`（本機開啟參考）。

#### 注意事項
- `view_booking_calendar` 為非同步（IntersectionObserver），頁面載入不會立即出現，需使用者滾動到日曆區才計。
- 若更換 Google 日曆預約連結（scheduleId），事件邏輯不受影響，僅替換 iframe 網址即可。

## 🔍 下一步建議

### 技術 SEO
1. **頁面加載速度優化**
   - 壓縮圖片（使用 WebP 格式）
   - 縮小 CSS/JavaScript 文件
   - 使用 CDN 分發靜態資源
   - 啟用瀏覽器緩存

2. **SSL 證書**
   - 確保使用 HTTPS 協議
   - 重定向 HTTP 到 HTTPS

3. **結構化數據測試**
   - 使用 Google Rich Results Test 驗證
   - 使用 Schema.org 驗證工具檢查

4. **頁面體驗信號**
   - Core Web Vitals 優化
   - LCP (Largest Contentful Paint) < 2.5s
   - FID (First Input Delay) < 100ms
   - CLS (Cumulative Layout Shift) < 0.1

### 內容 SEO
1. **博客/文章功能**
   - 添加營養知識文章
   - 定期更新內容
   - 使用關鍵字優化

2. **圖片優化**
   - 添加描述性 alt 文字
   - 壓縮圖片大小
   - 使用正確的文件格式

3. **內部連結**
   - 增加頁面間的內部連結
   - 使用描述性的錨文本
   - 創建相關內容網格

### 外部 SEO
1. **搜索引擎控制台**
   - 提交 sitemap 給 Google Search Console
   - 配置 Google Analytics
   - 設置 Google Business Profile

2. **本地 SEO**
   - 在 Google Business Profile 中添加業務信息
   - 獲得本地目錄列表
   - 獲取負責任的本地反向連結

3. **社交媒體整合**
   - 確保社交媒體資料一致
   - 添加社交分享按鈕
   - 優化社交媒體封面圖

### 維護建議
1. **內容更新**
   - 每週新增至少 1 篇博客文章
   - 更新服務信息
   - 新增客戶見證

2. **SEO 分析**
   - 每月檢查 Search Console 數據
   - 追蹤關鍵字排名
   - 分析用戶行為

3. **技術審查**
   - 每季度進行 SEO 審查
   - 更新結構化數據
   - 檢查死鏈

## 📊 關鍵字策略

### 主要關鍵字
- 營養師
- 體重管理
- 慢性病營養
- 營養諮詢
- 台灣營養師
- 台北營養師

### 長尾關鍵字
- 體重管理營養師
- 糖尿病飲食指導
- 營養諮詢 台北
- 專業營養師 預約
- 個人化飲食規劃
- 保健食品規劃

## 🔗 外部連結建議

1. **教育機構** - 臺北醫學大學、義守大學
2. **專業協會** - 相關營養師學會
3. **合作夥伴** - 醫院、診所、健身房
4. **資源** - �生醫相關網站

---

**最後更新**: 2025年6月17日
**SEO 責任人**: Kidson營養師
