#!/usr/bin/env python3
"""
スレッド（リプライチェーン）投稿スクリプト

深掘りコンテンツをスレッド形式で投稿し、
滞在時間・エンゲージメントを向上させる。
"""

import os
import sys
import random
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.absolute()
os.chdir(PROJECT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from post_via_xharness import post_thread, check_connection


def _twitter_len(text):
    WEIGHT1_RANGES = [
        (0x0000, 0x10FF),
        (0x2000, 0x200D),
        (0x2010, 0x201F),
        (0x2032, 0x2037),
    ]
    count = 0
    for ch in text:
        cp = ord(ch)
        w = 2
        for lo, hi in WEIGHT1_RANGES:
            if lo <= cp <= hi:
                w = 1
                break
        count += w
    return count


THREADS = {
    "fs_guide": [
        {"text": (
            "【スレッド】ファンタジースプリングス完全攻略\n\n"
            "AIデータで分析した「最も効率的な回り方」を公開します\n\n"
            "2025年4月にスタンバイパス廃止\n"
            "→ 誰でも自由に入れるようになりました\n\n"
            "でも待ち時間は相変わらず長い\n"
            "どう攻略するか? 以下スレッドで解説\n\n"
            "#ファンタジースプリングス #TDS"
        )},
        {"text": (
            "1/5 アナ雪の時間帯別待ち時間\n\n"
            "9時: 134分\n"
            "10時: 185分(1日で最長)\n"
            "13時: 145分\n"
            "17時: 108分\n"
            "19時: 55分\n"
            "20時: 10分\n\n"
            "結論: 19時以降が圧倒的に狙い目\n"
            "10時台と比べて130分の差"
        )},
        {"text": (
            "2/5 ラプンツェルは夜が正解\n\n"
            "待ち時間が短いだけじゃない\n"
            "ゴンドラから見るランタンは\n"
            "夜の方がずっと綺麗です\n\n"
            "19時台: 42分\n"
            "10時台: 133分\n\n"
            "演出面でも待ち時間面でも夜の勝ち"
        )},
        {"text": (
            "3/5 DPAの優先順位\n\n"
            "最優先: アナ雪(140分短縮)\n"
            "次点: ラプンツェル(100分短縮)\n"
            "余裕があれば: ピーターパン\n\n"
            "ティンカーベルはDPA対象外\n"
            "スタンバイのみで平均45分と短め\n\n"
            "DPAは入園直後にアプリで即購入"
        )},
        {"text": (
            "4/5 おすすめの回り方\n\n"
            "【午前】他エリアを回る\n"
            "ソアリン→トイマニ→センター\n\n"
            "【午後】DPA指定時間にアナ雪\n\n"
            "【18時〜】FSエリアへ移動\n"
            "ラプンツェル→ピーターパン\n"
            "→ティンカーベル\n\n"
            "これで1日に全アトラクション制覇可能"
        )},
        {"text": (
            "5/5 まとめ\n\n"
            "・FSは19時以降が最強\n"
            "・DPAはアナ雪を最優先\n"
            "・ラプンツェルは夜の演出が神\n"
            "・ティンカーベルは穴場\n\n"
            "AIの待ち時間予測は毎日20時に投稿中\n"
            "フォローしておけば行く前日にチェックできます\n\n"
            "#TDS #ディズニーシー"
        )},
    ],

    "beginner_guide": [
        {"text": (
            "【スレッド】ディズニー初心者が知るべき10のこと\n\n"
            "「初ディズニーで失敗したくない」\n"
            "という人向けに、AIデータと経験から\n"
            "最低限知っておくべきことをまとめます\n\n"
            "保存推奨です\n\n"
            "#ディズニー初心者 #TDR"
        )},
        {"text": (
            "1. チケットは事前購入必須\n\n"
            "当日券はほぼ完売\n"
            "公式サイトかアプリで事前に買う\n\n"
            "日によって値段が違う\n"
            "平日7900円〜休日10900円\n\n"
            "2. 公式アプリは絶対入れる\n\n"
            "DPA・プライオリティパス・\n"
            "モバイルオーダー全部アプリ必須"
        )},
        {"text": (
            "3. 開園1時間前に到着する\n\n"
            "AIデータによると\n"
            "開園30分前到着と開園時到着で\n"
            "最初のアトラクション待ち時間が\n"
            "約40分違います\n\n"
            "4. モバイルバッテリー必須\n\n"
            "アプリを1日中使うので\n"
            "スマホの電池が持ちません"
        )},
        {"text": (
            "5. ランチは11時前に\n\n"
            "12時台はどこも大行列\n"
            "モバイルオーダーで11時受取がベスト\n\n"
            "6. パレード中はチャンス\n\n"
            "みんなパレードを見るので\n"
            "アトラクションが30〜40%空きます\n"
            "パレードを見ないなら最高のタイミング"
        )},
        {"text": (
            "7. 夜は穴場\n\n"
            "20時以降は待ち時間が半分以下に\n"
            "閉園まで粘る人が勝ちます\n\n"
            "8. 火・水曜が最も空いてる\n\n"
            "AIの曜日分析で実証済み\n"
            "土曜の約半分の待ち時間\n\n"
            "有給取れるなら火水がおすすめ"
        )},
        {"text": (
            "9. 歩きやすい靴で行く\n\n"
            "1日で2万歩以上歩きます\n"
            "おしゃれより快適さを優先\n\n"
            "10. AI予測を前日にチェック\n\n"
            "毎日20時に翌日の混雑予測を投稿中\n"
            "行く前日にフォローしてチェック\n\n"
            "以上10個、保存して活用してください!\n"
            "#ディズニー #TDR"
        )},
    ],

    "rainy_day": [
        {"text": (
            "【スレッド】雨の日ディズニーが実は最高な理由\n\n"
            "「雨だから行くのやめようかな」\n\n"
            "ちょっと待ってください\n"
            "AIデータが証明する\n"
            "雨の日のメリットを解説します\n\n"
            "#ディズニー #雨の日ディズニー"
        )},
        {"text": (
            "メリット1: 待ち時間が激減\n\n"
            "雨の日は来園者が2〜3割減\n\n"
            "晴れ→雨の待ち時間変化:\n"
            "アナ雪: 140分→90分\n"
            "ソアリン: 100分→65分\n"
            "トイマニ: 85分→55分\n\n"
            "DPA買わなくても快適に回れる"
        )},
        {"text": (
            "メリット2: FSは全アトラクション屋内\n\n"
            "アナ雪もラプンツェルもピーターパンも\n"
            "全部屋内なので雨でも関係なし\n\n"
            "しかも待ち時間は短くなる\n"
            "雨の日こそFSに行くべきです\n\n"
            "メリット3: グリーティングが空く\n"
            "キャラクターにゆっくり会える"
        )},
        {"text": (
            "雨の日の持ち物\n\n"
            "必須: レインポンチョ(傘より便利)\n"
            "必須: 防水スマホケース\n"
            "必須: 替えの靴下\n"
            "推奨: 防水スニーカー\n"
            "推奨: タオル2〜3枚\n\n"
            "100均のポンチョでOK\n"
            "パーク内は1500円するので"
        )},
        {"text": (
            "結論: 雨ディズニーは「当たりの日」\n\n"
            "・待ち時間半減\n"
            "・屋内アトラクション充実\n"
            "・レストランも空いてる\n"
            "・お土産もゆっくり選べる\n\n"
            "準備さえすれば晴れより満足度高い\n\n"
            "AI予測で「雨だけど空いてる日」を\n"
            "チェックしてみてください\n"
            "#TDR #ディズニー攻略"
        )},
    ],

    "dpa_explained": [
        {"text": (
            "【スレッド】DPA・プライオリティパスの違い\n\n"
            "「DPAって何?」\n"
            "「プライオリティパスと何が違うの?」\n\n"
            "初心者の人が一番混乱するポイントを\n"
            "わかりやすく解説します\n\n"
            "#DPA #プライオリティパス #TDR"
        )},
        {"text": (
            "DPA(ディズニー・プレミアアクセス)\n\n"
            "・有料(1回2000円/人)\n"
            "・時間指定で待ち時間を短縮\n"
            "・対象: アナ雪、美女と野獣、ソアリン等\n"
            "・入園後アプリで購入\n\n"
            "要するに「お金で時間を買う」システム\n"
            "2000円で2時間の行列を回避できる"
        )},
        {"text": (
            "プライオリティパス\n\n"
            "・無料!\n"
            "・時間指定で待ち時間を短縮\n"
            "・対象: プーさん、バズ等(DPAより少ない)\n"
            "・入園後アプリで取得\n"
            "・取得後60分で次が取れる\n\n"
            "無料なので絶対使うべき\n"
            "午前中に人気枠は消えるので即取得"
        )},
        {"text": (
            "DPAとプライオリティパスの使い分け\n\n"
            "1. 入園→即DPA購入(アナ雪推奨)\n"
            "2. 同時にプライオリティパス取得\n"
            "3. 60分後に次のプライオリティパス\n"
            "4. DPA使用後に2つ目のDPA購入可\n\n"
            "併用することで1日の効率が2倍に\n\n"
            "詳しくはnoteにまとめました\n"
            "#ディズニー攻略"
        )},
    ],

    "weekly_data": [
        {"text": (
            "【スレッド】今週のAI分析レポート\n\n"
            "今週1週間の待ち時間データを分析\n"
            "来週行く人の参考になるはず\n\n"
            "以下、主要アトラクション別に\n"
            "傾向をお伝えします\n\n"
            "#TDR #ディズニー #待ち時間"
        )},
        {"text": (
            "【シー】今週の傾向\n\n"
            "・アナ雪は平日でも100分超えが定着\n"
            "・ソアリンは火水が比較的空き\n"
            "・トイマニは18時以降が狙い目\n"
            "・センターは天気に左右されやすい\n\n"
            "25周年効果で全体的に混雑傾向\n"
            "来週も同様の見込みです"
        )},
        {"text": (
            "【ランド】今週の傾向\n\n"
            "・美女と野獣は朝イチが最も効率的\n"
            "・モンスターズインクは午後やや空き\n"
            "・ビッグサンダーは終日安定\n"
            "・プーさんはプライオリティパス推奨\n\n"
            "ヴァネロペ効果でランドも混雑増加中"
        )},
        {"text": (
            "【来週の予測ポイント】\n\n"
            "・GW前で徐々に混雑度UP\n"
            "・天気が良い日は特に注意\n"
            "・火・水曜が狙い目\n"
            "・DPAは開園即購入を推奨\n\n"
            "毎日20時に翌日の詳細予測を投稿中\n"
            "フォローして前日チェックしてください\n\n"
            "#TDR #ディズニー攻略"
        )},
    ],
}


def main():
    parser = argparse.ArgumentParser(description="スレッド投稿")
    parser.add_argument("--thread", "-t", type=str,
                        help=f"スレッド名: {', '.join(THREADS.keys())}")
    parser.add_argument("--post", "-p", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", "-l", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("=== スレッド一覧 ===")
        for name, tweets in THREADS.items():
            print(f"  {name}: {len(tweets)}ツイート")
            for i, t in enumerate(tweets):
                tlen = _twitter_len(t["text"])
                ok = "OK" if tlen <= 280 else f"OVER({tlen})"
                print(f"    [{i}] {ok:>8} | {t['text'][:60].replace(chr(10), ' ')}")
        return 0

    if not args.thread:
        day = datetime.now().timetuple().tm_yday
        keys = list(THREADS.keys())
        args.thread = keys[day % len(keys)]
        print(f"💡 自動選択: {args.thread}")

    if args.thread not in THREADS:
        print(f"❌ 不明なスレッド: {args.thread}")
        print(f"   候補: {', '.join(THREADS.keys())}")
        return 1

    thread_data = THREADS[args.thread]

    print("=" * 60)
    print(f"🧵 スレッド投稿: {args.thread} ({len(thread_data)}ツイート)")
    print("=" * 60)

    for i, item in enumerate(thread_data):
        tlen = _twitter_len(item["text"])
        print(f"\n--- [{i+1}/{len(thread_data)}] ({tlen}/280) ---")
        print(item["text"])

    over = [i for i, t in enumerate(thread_data) if _twitter_len(t["text"]) > 280]
    if over:
        print(f"\n❌ 文字数オーバー: ツイート {over}")
        return 1

    if args.post and not args.dry_run:
        if not check_connection():
            print("❌ 接続失敗")
            return 1
        print("\n📤 スレッド投稿中...")
        ids = post_thread(thread_data)
        print(f"\n✅ {len(ids)}/{len(thread_data)} 投稿完了")
    else:
        print("\n💡 --post で投稿")

    return 0


if __name__ == "__main__":
    sys.exit(main())
