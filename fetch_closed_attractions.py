#!/usr/bin/env python3
"""
東京ディズニーリゾート公式サイトから休止中アトラクションを取得
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
from pathlib import Path

# ディズニーランド休止情報URL
TDL_STOP_URL = "https://www.tokyodisneyresort.jp/tdl/monthly/stop.html"
# ディズニーシー休止情報URL
TDS_STOP_URL = "https://www.tokyodisneyresort.jp/tds/monthly/stop.html"
TDL_DAILY_URL = "https://www.tokyodisneyresort.jp/tdl/daily/calendar.html"
TDS_DAILY_URL = "https://www.tokyodisneyresort.jp/tds/daily/calendar.html"


def fetch_daily_closed_attractions(url, park_name="", debug=False):
    """公式の当日パーク情報ページからアトラクション休止情報を取得"""
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
    except requests.RequestException as e:
        print(f"⚠️ {park_name} 当日休止情報の取得に失敗: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    lines = [line.strip() for line in soup.get_text('\n', strip=True).splitlines() if line.strip()]

    closed = []
    in_closed_section = False
    in_attraction_section = False

    for line in lines:
        if line == '休止情報':
            in_closed_section = True
            in_attraction_section = False
            continue

        if not in_closed_section:
            continue

        if line in {'今日の待ち時間/施設の運営状況', 'アプリのサービス'}:
            break

        if line == 'アトラクション':
            in_attraction_section = True
            continue

        if not in_attraction_section:
            continue

        if line == '閉じる':
            break

        if '休止を予定しているものはありません' in line:
            break

        if line in {'パレード/ショー', 'キャラクターグリーティング', 'ショップ', 'レストラン', 'サービス施設'}:
            break

        if line and line not in closed:
            closed.append(line)

    if debug:
        print(f"🔍 {park_name} 当日休止情報: {closed}")

    return closed


def load_override_closed_attractions(park='sea', target_date=None):
    """公式取得に失敗した場合の日付別オーバーライドを読む"""
    if target_date is None:
        target_date = datetime.now().strftime('%Y-%m-%d')
    elif isinstance(target_date, datetime):
        target_date = target_date.strftime('%Y-%m-%d')

    park_key = 'tds' if park == 'sea' else 'tdl'
    candidates = [
        Path('chatbot/data/attraction_status_overrides.json'),
        Path('data/official_attraction_status_overrides.json'),
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            with path.open(encoding='utf-8') as f:
                data = json.load(f)
            day = data.get(str(target_date), {})
            values = day.get(park_key)
            if values is not None:
                print(f"🚧 公式休止情報オーバーライド使用: {path} {target_date} {park_key}")
                return values
        except Exception as e:
            print(f"⚠️ 休止情報オーバーライド読み込み失敗: {path}: {e}")

    return None


def fetch_closed_attractions(url, park_name="", target_date=None, debug=False):
    """
    公式サイトから休止中アトラクション一覧を取得
    
    Args:
        url: 休止情報ページのURL
        park_name: パーク名（表示用）
        target_date: 対象日付（datetime or str 'YYYY-MM-DD'）。Noneの場合は今日
        debug: デバッグ出力を有効にするか
    
    Returns:
        list: 休止中アトラクション名のリスト
    """
    if target_date is None:
        target_date = datetime.now()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d')
    
    # 時間を除去して日付のみで比較
    target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if debug:
        print(f"🔍 対象日: {target_date.strftime('%Y-%m-%d')}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        closed_attractions = []
        
        # アトラクションリンクを探す（テーブル構造ではない場合に対応）
        links = soup.find_all('a')
        attraction_links = [l for l in links if '/attraction/' in l.get('href', '')]
        
        for link in attraction_links:
            # リンクのテキストからアトラクション名と開始日を抽出
            raw_text = link.get_text().replace('\n', '').replace('\t', '').strip()
            
            # アトラクション名と日付を分離（名前YYYY/M/D形式）
            match = re.match(r'(.+?)(\d{4}/\d{1,2}/\d{1,2})', raw_text)
            if not match:
                continue
            
            attraction_name = match.group(1).strip()
            start_date_str = match.group(2)
            
            # 開始日をパース
            try:
                start_parts = start_date_str.split('/')
                start_date = datetime(int(start_parts[0]), int(start_parts[1]), int(start_parts[2]))
            except (ValueError, IndexError):
                continue
            
            # 親要素から終了日を探す
            parent = link.parent
            end_date = None
            
            if parent:
                parent_text = parent.get_text().replace('\n', ' ').replace('\t', ' ')
                
                # 終了日を探す（親要素内のすべての日付を取得）
                all_dates = re.findall(r'(\d{4})/(\d{1,2})/(\d{1,2})', parent_text)
                
                if len(all_dates) >= 2:
                    # 2番目の日付が終了日
                    try:
                        end_date = datetime(int(all_dates[1][0]), int(all_dates[1][1]), int(all_dates[1][2]))
                    except ValueError:
                        pass
                
                # 「未定」の場合は終了日を遠い未来に設定
                if '未定' in parent_text:
                    end_date = datetime(2099, 12, 31)
            
            # 対象日が休止期間内かチェック
            is_closed_today = False
            
            if end_date:
                # 開始日〜終了日の範囲内
                is_closed_today = start_date <= target_date <= end_date
            else:
                # 終了日がない場合（通常はないが念のため）
                is_closed_today = start_date <= target_date
            
            if debug:
                status = "✓ 休止中" if is_closed_today else "✗ 営業中"
                end_str = end_date.strftime('%Y-%m-%d') if end_date else "不明"
                print(f"  {attraction_name}: {start_date.strftime('%Y-%m-%d')} 〜 {end_str} {status}")
            
            if is_closed_today and attraction_name not in closed_attractions:
                closed_attractions.append(attraction_name)
        
        return closed_attractions
        
    except requests.RequestException as e:
        print(f"⚠️ {park_name} 休止情報の取得に失敗: {e}")
        return []
    except Exception as e:
        print(f"⚠️ {park_name} 休止情報の解析に失敗: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_closed_attractions_land(target_date=None):
    """ディズニーランドの休止中アトラクションを取得"""
    daily_closed = fetch_daily_closed_attractions(TDL_DAILY_URL, "ディズニーランド")
    if daily_closed:
        return daily_closed
    override = load_override_closed_attractions('land', target_date)
    if override is not None:
        return override
    return fetch_closed_attractions(TDL_STOP_URL, "ディズニーランド", target_date)


def get_closed_attractions_sea(target_date=None):
    """ディズニーシーの休止中アトラクションを取得"""
    daily_closed = fetch_daily_closed_attractions(TDS_DAILY_URL, "ディズニーシー")
    if daily_closed:
        return daily_closed
    override = load_override_closed_attractions('sea', target_date)
    if override is not None:
        return override
    return fetch_closed_attractions(TDS_STOP_URL, "ディズニーシー", target_date)


def normalize_attraction_name(name, attraction_list):
    """
    スクレイプしたアトラクション名を予測システムの名前に正規化
    
    Args:
        name: スクレイプしたアトラクション名
        attraction_list: 予測システムで使用しているアトラクション名リスト
    
    Returns:
        str or None: マッチしたアトラクション名、またはNone
    """
    # 完全一致
    if name in attraction_list:
        return name
    
    # 特殊なマッピング（公式サイト名 → 予測システム名）
    name_mapping = {
        # ディズニーシー
        'ソアリン：ファンタスティック・フライト': 'ソアリン',
        'アナとエルサのフローズンジャーニー': 'アナとエルサ',
        'ラプンツェルのランタンフェスティバル': 'ラプンツェル',
        'ピーターパンのネバーランドアドベンチャー': 'ピーターパン',
        'フェアリー・ティンカーベルのビジーバギー': 'ティンカーベル',
        'トイ・ストーリー・マニア！': 'トイストーリーマニア',
        'タワー・オブ・テラー': 'タワーオブテラー',
        'センター・オブ・ジ・アース': 'センターオブジアース',
        'インディ・ジョーンズ®・アドベンチャー：クリスタルスカルの魔宮': 'インディージョーンズクリスタルスカルの謎',
        'インディ・ジョーンズ・アドベンチャー：クリスタルスカルの魔宮': 'インディージョーンズクリスタルスカルの謎',
        'レイジングスピリッツ': 'レイジングスピリッツ',
        '海底2万マイル': '海底二万マイル',
        'ニモ&フレンズ・シーライダー': 'ニモandフレンズシーライダー',
        'タートル・トーク': 'タートル・トーク',
        'マジックランプシアター': 'マジックランプシアター',
        'シンドバッド・ストーリーブック・ヴォヤッジ': 'シンドバッド',
        'ヴェネツィアン・ゴンドラ': 'ゴンドラ',
        'アクアトピア': 'アクアトピア',
        'ジャスミンのフライングカーペット': 'ジャスミン',
        'フランダーのフライングフィッシュコースター': 'フランダー',
        'スカットルのスクーター': 'スカットルのスクーター',
        'ジャンピン・ジェリーフィッシュ': 'ジャンピン',
        'ワールプール': 'ワールプール',
        'キャラバンカルーセル': 'カルーセル',
        'マーメイドラグーンシアター': 'マーメイドラグーン',
        'ディズニーシー・エレクトリックレールウェイ': 'エレクトリックレールウェイアメリカンウォーターフロント発',
        'ブローフィッシュ・バルーンレース': 'バルーンレース',
        
        # ディズニーランド
        'スペース・マウンテン': 'スペースマウンテン',
        'ビッグサンダー・マウンテン': 'ビッグサンダーマウンテン',
        'スプラッシュ・マウンテン': 'スプラッシュマウンテン',
        'プーさんのハニーハント': 'プーさんのハニーハント',
        'バズ・ライトイヤーのアストロブラスター': 'バズ・ライトイヤーのアストロブラスター',
        'モンスターズ・インク"ライド＆ゴーシーク！"': 'モンスターズ・インク"ライド＆ゴーシーク！"',
        'モンスターズ・インク“ライド＆ゴーシーク！”': 'モンスターズ・インク',
        'ホーンテッドマンション': 'ホーンテッドマンション',
        'カリブの海賊': 'カリブの海賊',
        'ピーターパン空の旅': 'ピーターパン空の旅',
        'イッツ・ア・スモールワールド': 'イッツ・ア・スモールワールド',
        '美女と野獣"魔法のものがたり"': '美女と野獣"魔法のものがたり"',
        '美女と野獣“魔法のものがたり”': '美女と野獣の物語',
        'ベイマックスのハッピーライド': 'ベイマックスのハッピーライド',
        'スター・ツアーズ:ザ・アドベンチャーズ・コンティニュー': 'スター・ツアーズ',
        'ジャングルクルーズ：ワイルドライフ・エクスペディション': 'ジャングルクルーズ',
        '空飛ぶダンボ': '空飛ぶダンボ',
        'ピノキオの冒険旅行': 'ピノキオの冒険旅行',
        'ミッキーのフィルハーマジック': 'ミッキーのフィルハーマジック',
        'ロジャーラビットのカートゥーンスピン': 'ロジャーラビットのカートゥーンスピン',
        '蒸気船マークトウェイン号': '蒸気船マークトウェイン号',
        'ミッキーの家とミート・ミッキー': 'ミート・ミッキー',
    }
    
    # マッピング辞書で検索
    if name in name_mapping:
        mapped = name_mapping[name]
        if attraction_list is None or mapped in attraction_list:
            return mapped
    
    # 部分一致（スクレイプ名が予測名を含む or 予測名がスクレイプ名を含む）
    if attraction_list:
        for attr in attraction_list:
            # 完全な部分一致
            if name in attr or attr in name:
                return attr
            # 句読点を除去して比較
            clean_name = re.sub(r'[・：""®]', '', name)
            clean_attr = re.sub(r'[・：""®]', '', attr)
            if clean_name in clean_attr or clean_attr in clean_name:
                return attr
    
    return None


def get_matched_closed_attractions(park='sea', attraction_list=None, target_date=None):
    """
    休止中アトラクションを取得し、予測システムの名前にマッチさせる
    
    Args:
        park: 'sea' または 'land'
        attraction_list: 予測システムで使用しているアトラクション名リスト
    
    Returns:
        list: マッチした休止中アトラクション名のリスト
    """
    if park == 'sea':
        raw_closed = get_closed_attractions_sea(target_date)
    else:
        raw_closed = get_closed_attractions_land(target_date)
    
    if not attraction_list:
        return raw_closed
    
    matched = []
    unmatched = []
    
    for name in raw_closed:
        normalized = normalize_attraction_name(name, attraction_list)
        if normalized:
            matched.append(normalized)
        else:
            unmatched.append(name)
    
    if unmatched:
        print(f"⚠️ マッチしなかった休止中アトラクション: {unmatched}")
    
    return list(set(matched))


def main():
    """テスト実行"""
    import argparse
    
    parser = argparse.ArgumentParser(description='休止中アトラクション情報を取得')
    parser.add_argument('--date', '-d', type=str, help='対象日付 (YYYY-MM-DD)')
    parser.add_argument('--debug', action='store_true', help='デバッグ出力を有効化')
    args = parser.parse_args()
    
    target_date = args.date if args.date else datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print("🏰 東京ディズニーリゾート 休止中アトラクション情報")
    print(f"📅 対象日: {target_date}")
    print(f"📅 取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    print("\n🎢 ディズニーランド 休止中アトラクション:")
    print("-" * 40)
    land_closed = fetch_closed_attractions(TDL_STOP_URL, "ディズニーランド", target_date, debug=args.debug)
    if land_closed:
        for i, name in enumerate(land_closed, 1):
            print(f"  {i}. {name}")
    else:
        print("  (休止中のアトラクションはありません)")
    
    print(f"\n🌊 ディズニーシー 休止中アトラクション:")
    print("-" * 40)
    sea_closed = fetch_closed_attractions(TDS_STOP_URL, "ディズニーシー", target_date, debug=args.debug)
    if sea_closed:
        for i, name in enumerate(sea_closed, 1):
            print(f"  {i}. {name}")
    else:
        print("  (休止中のアトラクションはありません)")
    
    print("\n" + "=" * 60)
    print("✅ 取得完了")
    
    # Pythonリスト形式で出力
    print("\n📋 CLIファイルにコピー用:")
    print("\n# ディズニーランド")
    print(f"CLOSED_ATTRACTIONS_LAND = {land_closed}")
    print("\n# ディズニーシー")
    print(f"CLOSED_ATTRACTIONS_SEA = {sea_closed}")


if __name__ == "__main__":
    main()
