"""
トレンドダイジェスト JSON から「今日のホットなハッシュタグ」を自動抽出して
キャプションに差し込むためのヘルパー。

使い方 (各 post スクリプトから):
    from scripts.trend_hashtags import get_trend_hashtags
    extra = get_trend_hashtags(date='2026-04-21', max_n=5)
    caption = base_caption + " " + " ".join(extra)
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from datetime import datetime
from typing import List

PROJECT_DIR = Path(__file__).parent.parent.absolute()

# キーワード → ハッシュタグの対応辞書 (本文中のキーワードに反応)
# - 中タグ (10万-100万件想定) を中心に。固定タグと重複しないように。
KEYWORD_TO_TAG = [
    # 25周年 / アニバーサリー
    (["25周年", "アニバーサリー"], ["#tdr25周年", "#ジュビリー"]),
    (["ジュビリー", "ブルー"], ["#ジュビリーブルー"]),
    # 新エリア・新アトラク
    (["ファンタジースプリングス"], ["#ファンタジースプリングス"]),
    (["アナとエルサ", "フローズン"], ["#アナとエルサのフローズンジャーニー"]),
    (["ピーターパン"], ["#ピーターパンのネバーランドアドベンチャー"]),
    (["ラプンツェル"], ["#ラプンツェルのランタンフェスティバル"]),
    (["ファンタジースプリングス・ホテル", "ファンタジースプリングスホテル"],
        ["#ファンタジースプリングスホテル"]),
    # 既存大型アトラク
    (["ソアリン"], ["#ソアリン", "#ソアリンファンタスティックフライト"]),
    (["タワー・オブ・テラー", "タワーオブテラー"], ["#タワーオブテラー"]),
    (["美女と野獣"], ["#美女と野獣魔法のものがたり"]),
    (["ベイマックス"], ["#ベイマックスのハッピーライド"]),
    # イベント / シーズナル
    (["ハロウィン", "ハロウィーン"], ["#ディズニーハロウィーン", "#ディズニーハロウィン"]),
    (["クリスマス"], ["#ディズニークリスマス"]),
    (["イースター"], ["#ディズニーイースター"]),
    (["七夕", "Tanabata"], ["#ディズニー七夕"]),
    (["夏祭り", "夏まつり"], ["#ディズニー夏まつり"]),
    # 料金 / チケット
    (["値上げ", "料金", "改定"], ["#ディズニーチケット", "#tdr料金"]),
    (["駐車場"], ["#ディズニー駐車場"]),
    # フード / グッズ
    (["新メニュー", "限定メニュー", "フード"], ["#ディズニーフード", "#tdrグルメ"]),
    (["グッズ", "ぬいぐるみ", "限定発売"], ["#ディズニーグッズ"]),
    (["ポップコーン"], ["#ディズニーポップコーン"]),
    # ホテル
    (["ディズニーホテル"], ["#ディズニーホテル"]),
    # ショー / パレード
    (["パレード", "エレクトリカルパレード"], ["#エレクトリカルパレード"]),
    (["ファンタズミック"], ["#ファンタズミック"]),
    (["ビリーブ", "Believe"], ["#ビリーブシーオブドリームス"]),
    # トラブル
    (["休止", "運休", "中止"], ["#ディズニー速報"]),
]

# トピック → 補助ハッシュタグ (categorize_news の戻り値ベース)
TOPIC_TO_TAG = {
    "🎉 25周年・記念":        ["#tdr25周年"],
    "🏰 新エリア・新アトラク":  ["#ファンタジースプリングス"],
    "🎁 グッズ・フード":       ["#ディズニーフード", "#ディズニーグッズ"],
    "🎪 イベント・期間限定":    [],   # 中身を見て個別にマッチ
    "💰 料金・チケット":        ["#ディズニーチケット"],
    "⚠️ トラブル・運休":       ["#ディズニー速報"],
}


def _norm_tag(s: str) -> str:
    """ハッシュタグ表記の正規化 (前置 # がない場合は付与、空白除去)"""
    s = s.strip()
    if not s:
        return ""
    if not s.startswith("#"):
        s = "#" + s
    s = re.sub(r"\s+", "", s)
    return s


def _today_json_path(date: str | None = None) -> Path:
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    return PROJECT_DIR / "reports" / f"disney_trend_{date}.json"


def get_trend_hashtags(date: str | None = None, max_n: int = 5,
                       exclude: list[str] | None = None) -> List[str]:
    """
    今日のトレンド JSON からハッシュタグを抽出する。

    - JSON 無し / 空 → 空リスト (呼び出し側で graceful に通常タグだけ使う想定)
    - 重複は除去
    - exclude に含まれるタグはスキップ (既存タグと被らないように)
    - 最大 max_n 件まで

    Returns:
        ['#tdr25周年', '#ジュビリーブルー', ...]
    """
    json_path = _today_json_path(date)
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text(encoding='utf-8'))
    except Exception:
        return []

    google_news = data.get("google_news", []) or []
    extras = data.get("extra_feeds", []) or []
    all_news = google_news + extras
    if not all_news:
        return []

    # ニュース本文を結合して keyword マッチ
    corpus = " ".join((n.get("title", "") or "") for n in all_news)

    found = []
    seen = set()
    excl = {_norm_tag(t).lower() for t in (exclude or [])}

    for keywords, tags in KEYWORD_TO_TAG:
        if any(kw in corpus for kw in keywords):
            for t in tags:
                tt = _norm_tag(t)
                if tt and tt.lower() not in seen and tt.lower() not in excl:
                    seen.add(tt.lower())
                    found.append(tt)

    # トピック別の追加
    try:
        import sys
        sys.path.insert(0, str(PROJECT_DIR / 'scripts'))
        from generate_trend_digest import categorize_news
        cat = categorize_news(all_news)
        for topic, tags in TOPIC_TO_TAG.items():
            if topic in cat and len(cat[topic]) >= 2:
                for t in tags:
                    tt = _norm_tag(t)
                    if tt and tt.lower() not in seen and tt.lower() not in excl:
                        seen.add(tt.lower())
                        found.append(tt)
    except Exception:
        pass

    return found[:max_n]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="今日のトレンドハッシュタグを抽出")
    parser.add_argument("--date", type=str, default=None,
                        help="対象日 YYYY-MM-DD (デフォルト今日)")
    parser.add_argument("--max", type=int, default=5)
    args = parser.parse_args()
    tags = get_trend_hashtags(date=args.date, max_n=args.max)
    if tags:
        print(" ".join(tags))
    else:
        print("(no trending tags)")
