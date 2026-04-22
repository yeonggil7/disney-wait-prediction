# Instagram グロース運用ガイド

`@disney_ai_wait` のフォロワー獲得を最大化するために構築した、コンテンツ自動生成 & 投稿パイプラインの運用メモ。

---

## 投稿の全体像

| 種別 | スクリプト | スケジュール (JST) | GitHub Actions |
|------|------------|-------------------|----------------|
| **翌日予報フィード (carousel 1本)** | `daily_instagram_post.py --carousel` | 毎日 20:05 | `instagram_post.yml` |
| **答え合わせ** | `daily_recap_post.py` | 毎日 11:30 | `instagram_recap.yml` |
| **週間混雑ランキング** | `weekly_ranking_post.py` | 日曜 21:00 | `instagram_weekly.yml` |
| **ストーリーズ朝briefing** | `daily_story_post.py --mode morning` | 毎日 07:30 | `instagram_story.yml` |
| **ストーリーズ ホットトピック** | `daily_story_post.py --mode hot_topic` | 毎日 07:30 | `instagram_hot_topic.yml` |
| **ストーリーズ夕プレビュー** | `daily_story_post.py --mode preview` | 毎日 17:00 | `instagram_story.yml` |
| **30秒リール** | `daily_reel_post.py` | 毎日 21:30 | `instagram_reel.yml` |
| **週次インサイトレポート (フォロワー要因分析付き)** | `scripts/ig_insights_report.py` | 月曜 09:00 | `instagram_insights.yml` |
| **カバー A/B レポート** | `scripts/cover_ab_report.py` | 月曜 10:00 | `instagram_cover_ab.yml` |
| **トレンドダイジェスト** | `scripts/generate_trend_digest.py` | 毎日 07:00 | `disney_trend.yml` |

合計で **週20〜25投稿（フィード + ストーリーズ + リール）** がフルオートで回ります。
※ フィードは「品質特化」のため 1日1本 (carousel) に削減。リール/ストーリーズに重点配分。

---

## 🆕 グロース v2 アップデート (2026-04 実施)

| 改善 | 効果 |
|---|---|
| **A** A/B 勝者ロジック恒久化 (`daily_reel_post.resolve_cover_variant`) | サンプル n≥10 & 3-of-3 制覇で自動的に勝者カバーへ統一 |
| **B** トレンド連動「今日のホットトピック」ストーリーズ | `instagram_hot_topic.yml` で 07:30 自動投稿 |
| **C** トレンド連動ハッシュタグ自動挿入 (`scripts/trend_hashtags.py`) | 全フィード/リール/ランキング投稿の冒頭タグを今日のニュースで動的生成 |
| **D** プロフィール最適化 (`PROFILE_OPTIMIZATION.md` + `scripts/generate_profile_mock.py`) | bio / ハイライト / アクションボタン の改善案 + ビジュアルモック |
| **E** 週次レポートに「フォロワー増加要因分析」セクション追加 | 投稿レベルの `follows` メトリクス + 投稿タイプ別効率 |
| **F** フィード投稿を 1日2本 → 1本 (carousel) に削減 | 平均エンゲージメント率の向上を狙う |

---

## 🚀 グロース v3 アップデート (2026-04 実施)

| 改善 | 機能 |
|---|---|
| **G** 最適投稿時間 自動分析 (`scripts/best_time_analyzer.py`) | 過去30日の reach / save 率を曜日 × 3時間帯 で集計、TOP5 + 推奨 cron を出力 (週次 `instagram_insights.yml` に組込) |
| **H** トレンド連動 BGM 自動切替 (`scripts/trending_bgm_selector.py`) | Hot Topic・天気・イベント に応じて BGM の bpm/key/装飾 を 5ムードから動的選択。Reels の `--bgm trending` で利用 |
| **I** カルーセル 1枚目フックの A/B (`scripts/generate_carousel_hook.py` + `carousel_hook_ab_report.py`) | V1 好奇心 / V2 数字 / V3 警告 / V4 CTA の 4変種をローテ → save率で自動勝者ロック |
| **J** Threads クロスポスト自動化 (`scripts/post_to_threads.py` + `cross_post_threads_from_ig.py`) | IG 投稿の 60〜90分後に Threads にも自動投稿 (`threads_crosspost.yml`) |
| **K** 天候・特別日アダプティブ投稿 (`scripts/weather_adaptive.py`) | Open-Meteo + 内蔵祝日カレンダーで「雨/猛暑/イベント」専用ストーリー自動生成 |
| **L** コメント FAQ 自動返信 (`scripts/auto_reply_comments.py`) | 10種類のFAQパターン (精度/データ元/雨/子連れ/おすすめ等) に丁寧に自動返信。`INSTAGRAM_AUTO_REPLY_ENABLED=true` で実投稿 |
| **M** TikTok / YouTube Shorts クロスポスト (`scripts/cross_post_tiktok.py` + `cross_post_youtube_shorts.py`) | 直近 IG Reels を TikTok 下書き / YT Shorts に自動アップ (`multi_platform_crosspost.yml`) |
| **N** 雨予報トリガー「雨の日ストーリー」 | K の派生。雨 PoP≥60% or 5mm 以上で 06:30 JST に「屋内アトラクTOP5+Tips」を自動配信 (`instagram_adaptive_story.yml`) |
| **O** 公開ダッシュボード Web (Linktree 代替) | `dashboard/` 一式 + `scripts/build_dashboard_data.py` を GitHub Pages デプロイ。bio リンク差し替えで「予測+ホットトピック+リンク集」を1ページに集約 |

### 必要な追加 GitHub Secrets

| Secret | 用途 | 必須? |
|---|---|---|
| `THREADS_USER_ID` / `THREADS_ACCESS_TOKEN` | Threads クロスポスト (J) | 任意 |
| `INSTAGRAM_AUTO_REPLY_ENABLED=true` | コメント FAQ 自動返信 を実投稿モードで有効化 (L) | 任意 |
| `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN` | YT Shorts クロスポスト (M) | 任意 |
| `TIKTOK_ACCESS_TOKEN` / `TIKTOK_OPEN_ID` / `TIKTOK_DIRECT_POST` | TikTok クロスポスト (M) | 任意 |

→ いずれも **未設定なら自動でスキップ** されるため、IG だけの運用は影響を受けません。

---

## ① 答え合わせ投稿 — `daily_recap_post.py`

「昨日のAI予測 vs 実測」を比較するインフォグラフィック (1080x1350)。

```bash
# 昨日分をシー+ランドのカルーセルで投稿
python daily_recap_post.py --post --carousel

# 任意日付
python daily_recap_post.py --post --date 2026-04-19

# 画像とキャプションだけ生成 (投稿しない)
python daily_recap_post.py --dry-run
```

- 画像: `predictions_x/ig_recap_{park}_{date}.png`
- 「±10分以内的中率」「平均誤差」「ベスト/ワースト的中ライド」を表示
- 「AI当たってる！」をフックに保存・シェア・フォローを誘発

## ② 週間混雑ランキング — `weekly_ranking_post.py`

来週7日間の予測平均待ち時間を集計し、狙い目DAY / 激混みDAY を見せる。

```bash
# 次の月曜起点で7日間
python weekly_ranking_post.py --post --carousel

# 任意起点
python weekly_ranking_post.py --post --start 2026-04-21 --days 7
```

- 画像: `predictions_x/ig_weekly_{park}_{start}.png`
- 「保存して旅行カレンダーに♪」のCTAで保存率↑

## ③ ストーリーズ — `daily_story_post.py`

シンプルな1枚briefing (1080x1920)。

```bash
# 当日の予報を朝に
python daily_story_post.py --mode morning --post

# 翌日の予報を夕方に
python daily_story_post.py --mode preview --post
```

- 画像: `predictions_x/ig_story_{mode}_{park}_{date}.png`
- 中央に大きな「混雑度」ラベル + 平均待ち
- カード: ★狙い目アトラクション / ▲最も混むライド / ●ピーク時間
- 「詳しい時間帯別予報はフィード投稿へ」でフィード誘導

## ④ 30秒リール — `daily_reel_post.py`

「30秒で分かる明日のディズニー混雑予報」コンセプトの mp4 (1080x1920 / H.264 / 24fps / AAC)。
イントロ → 24時間スロットを補間しながら流すバーチャートレース → 狙い目/ピーク時間+CTA のアウトロ。

```bash
# 翌日のシー+ランド両方を 20秒リールで投稿
python daily_reel_post.py --post

# 動画長を変える (5〜90秒)
python daily_reel_post.py --post --duration 25

# 任意日付 / 単一パーク
python daily_reel_post.py --post --date 2026-04-22 --park sea

# Reels タブのみ (フィードに表示しない)
python daily_reel_post.py --post --no-share-to-feed

# BGM の制御
python daily_reel_post.py --post --bgm none                # 無音
python daily_reel_post.py --post --bgm bgm/my_track.mp3    # 任意の音源
python daily_reel_post.py --post --bgm-volume-db -12       # ちょっと控えめに

# 動画とキャプションだけ生成
python daily_reel_post.py --dry-run
```

- 動画: `predictions_x/ig_reel_{park}_{date}.mp4`
- カバー: `predictions_x/ig_reel_{park}_{date}_cover.png`（**プロフィールグリッド 4:5 セーフゾーン対応**の専用デザイン）
- 動画ホスティング: catbox.moe (litterbox 1h) → 0x0.st → catbox の3段フォールバック
- Reelsコンテナの処理は最大5分待機 (`post_via_instagram_graph.post_reel`)
- リーチ拡大に最も寄与する形式（保存・シェアの分母を増やす）

> **動画のフォーマット**: 1080x1920 / H.264 / yuv420p / 24fps / AAC 48kHz / `+faststart` (moov 先頭) を ffmpeg で自動エンコード。IG Reels API の要件をフル充足。

### 🖼️ カバーサムネ最適化 (`_draw_cover`)

リールのカバーは Instagram 内で **3つの異なる比率** で表示されるため、それぞれに最適化:

| 表示場所 | 比率 | 解説 |
|---|---|---|
| Reels 専用フィード / 発見タブ | 9:16 (1080×1920) | 全画面表示 |
| プロフィール グリッド | 4:5 (1080×1350) | **中央クロップ** (上下 285px ずつカット) |

`_draw_cover` の設計原則:
- **セーフゾーン** (中央 y∈[0.148, 0.852]) に必須情報をすべて収める
  - 日付ピル / パーク名 / 狙い目・ピーク KPIカード / 1日の混雑トレンド ミニ折れ線 / "▶ タップして再生"
- **アウター** (上下端、グリッドでは隠れる) にブランド要素を配置
  - 上: "30秒で分かる / AI 待ち時間予報" フック
  - 下: `@disney_ai_wait` ハンドル + "保存推奨" CTA
- **ミニ折れ線** で「動画を見ると1日の混雑がわかる」と一目で伝える（max=赤・min=緑のドット）
- パーク色グラデーション背景 (sea: turquoise / land: rose magenta)

カバー差し替えだけでも CTR (タップ率) と保存率の改善が期待できます。

### 🧪 A/B テスト (`scripts/cover_ab_report.py`)

新カバー vs 旧カバー (1フレーム目) を **自動的に交互投稿 → 1週間で集計**できる仕組み:

```bash
# 投稿時 (デフォルト 'auto' で日付×パークで交互割り当て)
python daily_reel_post.py --post                          # auto: doy+park で new/old 交互
python daily_reel_post.py --post --cover-variant new      # 強制で new
python daily_reel_post.py --post --cover-variant old      # 強制で old

# レポート生成 (過去14日)
python scripts/cover_ab_report.py --days 14 \
  --out reports/cover_ab.md --json reports/cover_ab.json

# ローカルログだけで動作確認
python scripts/cover_ab_report.py --dry-run --since 2026-04-15
```

仕組み:
- `instagram_post_log.csv` の **`extra` (JSON) カラム** に `cover_variant`/`park`/`target_date`/`duration`/`bgm` を投稿時に記録
- レポートが Graph API で各 Reels の insights (reach / views / saved / likes / comments / shares) を取得
- variant ごとに集計し **CTR (views/reach) / 保存率 (saved/reach)** を中心に比較
- 3指標 (CTR / 保存率 / 平均再生) のうち過半数で勝った方を **🏆 暫定勝者** として表示

割当ロジック (`resolve_cover_variant`):
```
variant = ['old','new'][(day_of_year + park_offset) % 2]
park_offset = 0 if 'sea' else 1
```
1日2投稿 (sea+land) のうち必ず 1 つは old、もう 1 つは new に振られ、週単位でも各パーク 3〜4 ずつのバランスで揃う。

**自動実行**: `instagram_cover_ab.yml` が毎週月曜 10:00 JST に過去14日分でレポート生成・コミット (`reports/cover_ab_YYYY-MM-DD.md`)。

---

## ⑥ ディズニートレンド ダイジェスト — `scripts/generate_trend_digest.py`

毎朝7時に「**今日と最近のディズニー動向**」を 1ファイルでまとめる、運用補助の日次ブリーフィング。

### 取得ソース (graceful fallback 設計)
| ソース | 認証 | 内容 |
|---|---|---|
| **Google ニュース RSS** | 不要 | "東京ディズニーシー / ランド / TDR" 等で日本語ニュース検索 (1クエリあたり最大8件) |
| GIGAZINE / ねとらぼ RSS | 不要 | ディズニーキーワード抽出 |
| **Reddit r/Disneyland 等** | 任意 (`REDDIT_CLIENT_ID/SECRET`) | 海外コミュニティの今日のホット投稿 |
| **自社実績データ** | 不要 | 昨日の混雑サマリ / 先週同曜日比較 / 過去7日トレンド / TOP/BOTTOM5 アトラク |

### 出力
- `reports/disney_trend_{date}.json` : 元データ
- `reports/disney_trend_digest_{date}.md` : Markdownダイジェスト (人が読む用)
- `reports/disney_trend_digest_{date}.png` : 1080x1350 ダッシュボード画像 (個人参照 / 必要なら IG 投稿に転用可)

### Markdown構成
1. 📊 **昨日の実績** (パーク別 平均 / ピーク / TOP混雑)
2. 📈 **先週同曜日比較** (▲▼ アローと %)
3. 📅 **過去7日トレンド** (テーブル)
4. 🎯 **狙い目 / 激混みTOP5** (パーク別)
5. 📰 **今日のディズニー話題** (8トピック自動分類)
   - 🎉 25周年・記念 / 🏰 新エリア / 🎁 グッズ・フード / 🎪 イベント / 💰 料金 / ⚠️ トラブル 等
6. 💬 **Reddit 海外人気** (任意)
7. 💡 **今日の投稿ヒント** — トレンドから派生する運用 Tips を自動生成

### 投稿ヒント自動生成の例
- "25周年関連がトレンド → ジュビリー系ハッシュタグ追加"
- "料金関連がバズ中 → コスパ良く回るルート系の投稿チャンス"
- "シーが先週比 +45% → 「最近混んでる！」系の警告投稿を検討"

### コマンド
```bash
# 収集 → ダイジェスト 一気通貫
python scripts/generate_trend_digest.py --collect

# 既存 JSON から再描画
python scripts/generate_trend_digest.py --input reports/disney_trend_2026-04-20.json

# Markdown のみ
python scripts/generate_trend_digest.py --collect --no-image
```

**自動実行**: `disney_trend.yml` が毎日 07:00 JST に生成 → `reports/` にコミット。
朝の 1分のチェックで「今日の運用方針」と「世間の話題」を把握できます。

### 🎵 BGM (`generate_bgm.py`)

著作権フリーで使えるよう、numpy で**自前合成**したチル系BGMを ffmpeg でミックスします。

| パーク | 進行 | キャラクター |
|---|---|---|
| **シー** | Am-F-C-G (短調起点) | 落ち着き / 大人っぽい |
| **ランド** | C-G-Am-F (長調) | 明るく軽快 / ポップ |

- 92BPM / 4小節ループ・ペンタトニックの装飾音 (キラキラ) + ソフトキック
- 1pole ローパス + tanh ソフトクリップでマイルドな音作り
- ffmpeg 側で `volume=-8dB` + フェードイン/アウト (1.0/1.5s) を自動付与
- 計測ラウドネス: **約 -19 LUFS**（IG推奨 -14 LUFS の範囲内 / 視聴中の聴き疲れを抑える BGM 帯域）
- 任意の音源を使いたい場合は `bgm/sea.mp3` または `bgm/default.mp3` を置けば自動で優先

CLI 単体実行:

```bash
# サンプル WAV 生成
python generate_bgm.py --park land --duration 20 --out predictions_x/bgm_sample.wav
```

**視聴完了率を上げる効果**: BGM ありの動画は最初の3秒スキップ率が下がり (Meta調べで〜10%向上)、保存率も上昇する傾向。動画にミュートで触れて即離脱、を防ぎます。

## ⑤ 週次インサイトレポート — `scripts/ig_insights_report.py`

過去7日間の投稿のリーチ・保存・シェア・いいね・コメントを Graph API から取得して Markdown レポート化。

```bash
# 過去7日
python scripts/ig_insights_report.py

# 任意期間
python scripts/ig_insights_report.py --since 2026-04-01

# 出力先指定
python scripts/ig_insights_report.py --out reports/weekly.md --json-out reports/weekly.json
```

- 自動コミット先: `reports/instagram_weekly_YYYY-MM-DD.md`
- 投稿時に `instagram_post_log.csv` にメディアIDが記録される
- 改善ヒントを自動生成 (保存率/シェア率/投稿頻度)

---

## グロース戦略

### 数値KPI (90日目標)

| 指標 | 現状 | 30日後 | 60日後 | 90日後 |
|-----|------|-------|-------|-------|
| フォロワー | ~ | 500 | 2,000 | 5,000 |
| 1投稿あたり保存数 | ~ | 30 | 80 | 200 |
| 平均リーチ | ~ | 1,000 | 3,000 | 8,000 |

### コンテンツ施策の優先度

1. **保存される投稿を作る** = 旅行プランに使える情報密度
   - 答え合わせ・週間ランキングは強い保存フック
2. **シェアされる投稿を作る** = 「友達に教えたくなる驚き」
   - 「予測とのズレが面白い」「土日の差が衝撃」みたいな投稿
3. **ストーリーズで毎日露出**
   - フィードを見ない人にも「いつもいるアカウント」と認知させる
4. **リール検討 (今後の拡張)**
   - 「30秒で分かる明日のディズニー」「過去1ヶ月の混雑トレンド」
   - 動画化は matplotlib.animation + ffmpeg で自動化可能

### 非自動化のおすすめ施策

- **プロフィール最適化**
  - bio に「毎日20時更新」「保存して旅行プランに」を明記
  - ハイライトに「使い方 / 過去の的中例 / FAQ」
- **ハッシュタグ**
  - ニッチタグ (~10万件) を中心に。既に各スクリプトに同梱
- **コラボ・引用**
  - ディズニーブロガー・YouTuber に「明日の予報当たってましたよ」リプを送る
- **Threads / X 連携**
  - 同じ画像を Threads にもクロスポスト（プロフィール統一感）

---

## GitHub Actions 必要 Secrets

すべて `Settings → Secrets and variables → Actions` に登録:

| Secret 名 | 用途 |
|-----------|------|
| `INSTAGRAM_API_MODE` | `graph` を推奨 |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | IG Business アカウントID |
| `INSTAGRAM_ACCESS_TOKEN` | 長期Access Token (60日) |
| `FACEBOOK_APP_ID` / `FACEBOOK_APP_SECRET` | (Token更新用) |
| `IMGUR_CLIENT_ID` | 画像ホスティング (推奨) |

> Insights API は `instagram_manage_insights` スコープのトークンが必要です。

---

## トラブルシュート

- **画像ホスト失敗**: `post_via_instagram_graph.py` には Imgur / litterbox / 0x0.st / tmpfiles / catbox の **5段フォールバック** が組まれています
- **Insights が0**: 投稿後数時間〜1日でデータ反映。新規アカウントは権限再認証で改善することがある
- **トークン期限切れ**: 60日に1回、`scripts/ig_graph_setup.py` で再発行
