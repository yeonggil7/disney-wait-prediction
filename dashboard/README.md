# 公開ダッシュボード (Linktree 代替)

Instagram bio に貼るための GitHub Pages 公開ダッシュボード。

## 構成

- `index.html` ── 1枚もの SPA (依存ライブラリなし)
- `app.js`     ── `data/latest.json` を読んで描画
- `data/latest.json` ── `scripts/build_dashboard_data.py` が毎日 22:00 JST に更新

## デプロイ

`.github/workflows/dashboard_build.yml` が自動で:
1. JSON ビルド
2. `git commit` → `git push`
3. GitHub Pages にデプロイ (`actions/deploy-pages@v4`)

## 初回セットアップ (1回のみ)

1. GitHub repo の Settings → Pages → Source = `GitHub Actions` を選択
2. workflow を 1度手動実行 (`Actions` → `Build & Deploy Dashboard` → `Run`)
3. デプロイ完了後、`https://<GITHUB_USERNAME>.github.io/<REPO_NAME>/` が公開URL
4. Instagram bio の URL をこれに差し替え

## ローカル確認

```sh
python scripts/build_dashboard_data.py --date 2026-04-22
cd dashboard && python -m http.server 8000
# → http://localhost:8000/
```

## カスタマイズ

- `app.js` の `linkRow(...)` を増減すれば Linktree 風リンク集を追加可能
- `index.html` の CSS をいじれば配色・レイアウトが変わる
