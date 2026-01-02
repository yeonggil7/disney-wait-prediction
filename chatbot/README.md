# 🏰 ディズニーガイドBot v2.0

東京ディズニーリゾートについての質問に答えるAIチャットボットです。

## ✨ 新機能（v2.0）

### 1. 🤖 LLM連携（Claude API）
- Claude APIを使用した自然な対話
- ルールベースとのハイブリッド方式で高精度な回答
- 会話の文脈を理解したインテリジェントな応答

### 2. 📊 全アトラクション・レストラン情報
- ディズニーランド・シーの30以上のアトラクション
- 20以上のレストラン情報
- ファンタジースプリングス（2024年新エリア）対応

### 3. ⏰ リアルタイム待ち時間
- 予測データとの連携
- 時間帯・曜日に応じた待ち時間推定
- アトラクション別の詳細情報

### 4. 📸 隠れミッキー画像対応
- 画像付きヒント表示
- 難易度別の検索
- エリア別の隠れミッキー情報

### 5. 🎯 ユーザー学習・パーソナライズ
- 会話から好みを自動学習
- パーソナライズされたおすすめ
- スリル好み、キャラクター、食事の好みを記憶

## 🚀 セットアップ

```bash
cd chatbot

# 依存関係のインストール
pip install -r requirements.txt

# Claude APIを使う場合（オプション）
export ANTHROPIC_API_KEY="your-api-key"

# アプリケーションの起動
python app.py
```

ブラウザで http://localhost:5000 にアクセス

## 📁 プロジェクト構造

```
chatbot/
├── app.py                    # Webアプリケーション（Flask）
├── chatbot.py                # チャットボットのコアロジック
├── llm_engine.py             # Claude API連携
├── wait_time_service.py      # 待ち時間サービス
├── image_service.py          # 画像管理サービス
├── user_profile_service.py   # ユーザー学習サービス
├── requirements.txt          # 依存関係
├── data/
│   ├── parks.json            # パーク情報
│   ├── attractions_full.json # 全アトラクション情報
│   ├── restaurants.json      # レストラン情報
│   ├── app_guide.json        # アプリガイド
│   ├── tips.json             # Tips・コース
│   ├── hidden_mickeys.json   # 隠れミッキー
│   └── users/                # ユーザープロファイル
├── static/
│   └── images/
│       └── hidden_mickeys/   # 隠れミッキー画像
└── templates/
    └── index.html            # WebUI
```

## 🔌 API エンドポイント

| エンドポイント | 説明 |
|---------------|------|
| `POST /api/chat` | チャットメッセージを送信 |
| `GET /api/status` | システムステータス |
| `GET /api/attractions` | アトラクション一覧 |
| `GET /api/wait_times` | 待ち時間一覧 |
| `GET /api/wait_time/<name>` | 特定アトラクションの待ち時間 |
| `GET /api/hidden_mickeys` | 隠れミッキー情報 |
| `GET /api/user/profile` | ユーザープロファイル |
| `POST /api/user/preferences` | 好みを更新 |
| `GET /api/user/recommendations` | パーソナライズ推奨 |

## 💬 使い方の例

### アトラクション
- 「美女と野獣について教えて」
- 「トイマニの待ち時間は？」
- 「絶叫系でおすすめのアトラクションは？」

### レストラン
- 「シーでイタリアンが食べたい」
- 「レストラン予約の方法」
- 「子連れにおすすめのレストラン」

### 隠れミッキー
- 「隠れミッキーを教えて」
- 「ファンタジーランドの隠れミッキー」

### アプリ・予約
- 「スタンバイパスって何？」
- 「プレミアアクセスの使い方」

### パーソナライズ
- 「おすすめを教えて」（学習結果に基づく推奨）

## ⚙️ 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | Claude APIキー | No（なければルールベースで動作） |
| `FLASK_SECRET_KEY` | Flaskセッションキー | No |

## 📝 データの追加・編集

### アトラクションを追加

`data/attractions_full.json`に追加：

```json
{
  "id": "unique_id",
  "name": "アトラクション名",
  "park": "tdl または tds",
  "area": "エリアID",
  "type": "ライド",
  "description": "説明",
  "trivia": ["トリビア1", "トリビア2"],
  "tips": ["Tips1", "Tips2"],
  "thrill_level": 3,
  "height_restriction": null
}
```

### 隠れミッキー画像を追加

```python
from image_service import ImageService

service = ImageService()
service.add_image(
    file_path="path/to/image.jpg",
    category="hidden_mickey",
    location="ビッグサンダー・マウンテン待機列",
    description="歯車の形をした隠れミッキー",
    hint="3つの歯車を探してみて",
    difficulty="easy",
    park="tdl"
)
```

## 🔮 今後の拡張予定

- [ ] 音声入力対応
- [ ] LINE Bot連携
- [ ] ショー・パレード情報
- [ ] 季節イベント自動更新
- [ ] 多言語対応（英語・中国語）
