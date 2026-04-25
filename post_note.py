#!/usr/bin/env python3
"""
note 記事投稿 CLI

使い方:
    python post_note.py --list                       # 利用可能な記事一覧
    python post_note.py --article prediction --draft  # 下書き保存
    python post_note.py --article gw                  # 公開
    python post_note.py --article tds25 --tweet       # 公開 + X で宣伝
    python post_note.py --all --draft                 # 全記事を下書き保存
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from note_client import NoteClient
from note_articles import get_article, ALL_ARTICLE_KEYS


def post_single(client: NoteClient, key: str,
                draft_only: bool = False,
                tweet: bool = False) -> dict | None:
    """1記事を投稿"""
    print(f"\n{'='*60}")
    print(f"📄 記事: {key}")
    print(f"{'='*60}")

    try:
        title, md_body, hashtags = get_article(key)
    except ValueError as e:
        print(f"❌ {e}")
        return None

    html_body = NoteClient.markdown_to_html(md_body)

    print(f"   タイトル: {title}")
    print(f"   本文: {len(md_body)}文字")
    print(f"   ハッシュタグ: {hashtags}")
    print(f"   モード: {'下書き' if draft_only else '公開'}")

    try:
        result = client.post_article(
            title=title,
            body_html=html_body,
            hashtags=hashtags,
            draft_only=draft_only,
        )
    except Exception as e:
        print(f"❌ 投稿エラー: {e}")
        return None

    if tweet and not draft_only and result:
        _tweet_note_link(title, result.get("url", ""), hashtags)

    return result


def _tweet_note_link(title: str, url: str, hashtags: list[str]):
    """note 記事リンクを X で宣伝"""
    try:
        from post_via_xharness import post_to_twitter
        from daily_x_post import _twitter_len
    except ImportError:
        print("⚠️  X投稿モジュールが見つかりません。X連携をスキップ。")
        return

    tag_str = " ".join(f"#{h}" for h in hashtags[:3])
    tweet_text = f"📝 noteで記事を書きました！\n\n{title}\n\n{url}\n\n{tag_str}"

    tlen = _twitter_len(tweet_text)
    if tlen > 280:
        tweet_text = f"📝 note更新！\n\n{title}\n\n{url}\n\n{tag_str}"
        tlen = _twitter_len(tweet_text)
    if tlen > 280:
        tweet_text = f"📝 note更新！\n\n{url}\n\n{tag_str}"

    print(f"\n   🐦 X連携ツイート ({_twitter_len(tweet_text)}/280文字)")
    post_to_twitter(tweet_text)


def main():
    parser = argparse.ArgumentParser(
        description="note.com 記事投稿ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--article", "-a",
        choices=ALL_ARTICLE_KEYS,
        help="投稿する記事キー",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全記事を投稿",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="利用可能な記事一覧を表示",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="下書きとして保存（公開しない）",
    )
    parser.add_argument(
        "--tweet",
        action="store_true",
        help="投稿後に X で宣伝ツイート",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="note 認証を確認",
    )
    args = parser.parse_args()

    if args.list:
        print("📚 利用可能な記事:")
        for k in ALL_ARTICLE_KEYS:
            title, body, tags = get_article(k)
            lines = body.strip().split("\n")
            print(f"  [{k:<12}] {title}")
            print(f"               {len(lines)}行 / tags: {', '.join(tags[:4])}")
        return

    if args.check:
        client = NoteClient()
        try:
            client.get_me()
            print("✅ note 認証OK")
        except Exception as e:
            print(f"❌ 認証エラー: {e}")
        return

    if not args.article and not args.all:
        parser.print_help()
        return

    client = NoteClient()
    try:
        client.get_me()
    except Exception as e:
        print(f"❌ note認証に失敗しました: {e}")
        print("   NOTE_COOKIES を .env に設定してください。")
        print("   取得方法: ブラウザでnote.comにログイン → DevTools → ")
        print("   Application → Cookies → 全Cookie値をコピー")
        sys.exit(1)

    results = []
    keys = ALL_ARTICLE_KEYS if args.all else [args.article]

    for key in keys:
        result = post_single(client, key,
                             draft_only=args.draft,
                             tweet=args.tweet)
        if result:
            results.append((key, result))
        if len(keys) > 1:
            time.sleep(3)

    print(f"\n{'='*60}")
    print(f"📊 結果: {len(results)}/{len(keys)} 記事投稿完了")
    for key, r in results:
        status = r.get("status", "?")
        url = r.get("url", "")
        print(f"   [{key}] {status} → {url}")


if __name__ == "__main__":
    main()
