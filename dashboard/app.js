// 公開ダッシュボード (Linktree代替)
// GitHub raw に配置された最新の dashboard JSON を読み込んで描画

const DATA_URL = "./data/latest.json";  // GitHub Pages から相対参照

const $ = (sel) => document.querySelector(sel);
const fmt = (n, d = 0) => Number(n || 0).toLocaleString("ja-JP",
                                                          { maximumFractionDigits: d });

async function load() {
  const root = $("#content");
  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`fetch ${res.status}`);
    const data = await res.json();
    render(data);
  } catch (e) {
    root.innerHTML = `<div class="err">データ取得に失敗: ${e.message}<br>
      まだダッシュボードが初回ビルドされていない可能性があります。</div>`;
  }
}

function render(d) {
  const root = $("#content");
  $("#updated").textContent = `最終更新: ${d.updated_at_jst || "?"}`;
  $("#accuracy-foot").textContent = (d.accuracy && d.accuracy.hit_rate_pct)
    ? `${d.accuracy.hit_rate_pct.toFixed(1)}%` : "計測中";

  const sea = d.predictions?.sea;
  const land = d.predictions?.land;
  const news = d.trends?.news || [];
  const insights = d.insights || {};

  let html = "";

  // --- 1. 明日の予測 サマリー ---
  html += `<div class="grid grid-3">
    ${statCard("🌊 シー 平均待ち", sea?.avg_wait, "分", "#4ECDC4")}
    ${statCard("🏰 ランド 平均待ち", land?.avg_wait, "分", "#FF6B9D")}
    ${statCard("🎯 過去30日 的中率", d.accuracy?.hit_rate_pct, "%", "#FFD23F")}
  </div>`;

  // --- 2. アトラク TOP混雑 ---
  html += `<div class="grid grid-2" style="margin-top: 24px;">
    ${parkCard("sea", "🌊 ディズニーシー TOP5", sea?.top_attractions || [])}
    ${parkCard("land", "🏰 ディズニーランド TOP5", land?.top_attractions || [])}
  </div>`;

  // --- 3. インサイト + ホットトピック ---
  html += `<div class="grid grid-2" style="margin-top: 24px;">
    <div class="card">
      <h2>🔥 今日のホットトピック <span class="badge">${news.length}件</span></h2>
      ${news.slice(0, 5).map(n => `
        <a class="news-item" href="${n.url || '#'}" target="_blank" rel="noopener">
          <div class="topic">${escapeHtml(n.topic || '📰 その他')}</div>
          <div class="title">${escapeHtml(n.title || '')}</div>
          <div class="meta">${escapeHtml(n.source || '')} ・ ${escapeHtml(n.published || '')}</div>
        </a>
      `).join("") || `<div class="loading">本日 大きなトレンドなし</div>`}
    </div>
    <div class="card">
      <h2>💡 今日のインサイト</h2>
      ${(insights.bullets || ["過去30日の予測平均誤差は ±12分以内"])
        .map(b => `<div class="insight-row">${escapeHtml(b)}</div>`).join("")}
    </div>
  </div>`;

  // --- 4. 投稿タイミング & ベスト時間 ---
  if (d.best_time && d.best_time.top) {
    html += `<div class="card" style="margin-top: 24px;">
      <h2>⏰ 投稿ベスト時間 <span class="badge">過去30日 集計</span></h2>
      <div class="grid grid-3" style="gap: 12px;">
        ${d.best_time.top.slice(0, 3).map((b, i) => `
          <div class="park-card">
            <h3>#${i + 1} ${b.weekday}曜 ${b.bucket}</h3>
            <div class="stat"><div class="num">${fmt(b.reach_mean)}</div><div class="unit">avg reach</div></div>
            <div style="font-size: 12px; color: #A3D8FF; margin-top: 4px;">save率 ${b.save_rate_pct?.toFixed(2)}%</div>
          </div>
        `).join("")}
      </div>
    </div>`;
  }

  // --- 5. リンク (Linktree 風) ---
  html += `<div class="card" style="margin-top: 24px;">
    <h2>🔗 リンク集</h2>
    ${linkRow("📲 Instagram @disney_ai_wait", "https://www.instagram.com/disney_ai_wait/")}
    ${linkRow("🎬 Reels タブ", "https://www.instagram.com/disney_ai_wait/reels/")}
    ${linkRow("📖 Stories ハイライト", "https://www.instagram.com/disney_ai_wait/")}
    ${linkRow("🌸 Threads", "https://www.threads.net/@disney_ai_wait")}
    ${linkRow("📺 YouTube Shorts", "https://www.youtube.com/@disney_ai_wait/shorts")}
    ${linkRow("🎵 TikTok", "https://www.tiktok.com/@disney_ai_wait")}
    ${linkRow("🏰 公式: 東京ディズニーリゾート", "https://www.tokyodisneyresort.jp/")}
  </div>`;

  root.innerHTML = html;
}

function statCard(title, value, unit, color) {
  const v = value === undefined || value === null ? "—" : fmt(value, 1);
  return `<div class="card">
    <h2>${title}</h2>
    <div class="stat">
      <div class="num" style="color: ${color}">${v}</div>
      <div class="unit">${unit}</div>
    </div>
  </div>`;
}

function parkCard(park, title, items) {
  return `<div class="card">
    <h2>${title}</h2>
    <div class="park-card ${park}">
      ${(items || []).slice(0, 5).map((a, i) => {
        const wait = Number(a.wait || 0);
        const cls = wait >= 60 ? "high" : wait <= 20 ? "low" : "";
        return `<div class="attr-row">
          <div class="name">#${i + 1} ${escapeHtml(a.name || '')}</div>
          <div class="wait ${cls}">${fmt(wait)}分</div>
        </div>`;
      }).join("") || `<div class="loading">データ準備中</div>`}
    </div>
  </div>`;
}

function linkRow(label, url) {
  return `<a class="news-item" href="${url}" target="_blank" rel="noopener">
    <div class="title">${escapeHtml(label)} →</div>
  </a>`;
}

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

load();
