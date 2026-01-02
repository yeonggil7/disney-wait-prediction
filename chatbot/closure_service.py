"""
休止情報取得サービス - 公式サイトからアトラクション休止情報を取得
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import urllib.request
import urllib.error
from html.parser import HTMLParser


@dataclass
class ClosureInfo:
    """休止情報"""
    attraction_name: str
    park: str  # "tdl" or "tds"
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD or "未定"
    reason: str  # "refurbishment", "seasonal", "weather", "other"
    note: str = ""


class ClosureHTMLParser(HTMLParser):
    """公式サイトのHTMLをパースして休止情報を抽出"""
    
    def __init__(self):
        super().__init__()
        self.closures = []
        self.in_closure_section = False
        self.current_data = []
    
    def handle_data(self, data):
        if self.in_closure_section:
            self.current_data.append(data.strip())


class ClosureService:
    """休止情報サービス"""
    
    # 公式サイトのURL（休止情報ページ）
    CLOSURE_URLS = {
        "tdl": "https://www.tokyodisneyresort.jp/tdl/monthly/stop.html",
        "tds": "https://www.tokyodisneyresort.jp/tds/monthly/stop.html",
    }
    
    # キャッシュファイルのパス
    CACHE_FILE = "closure_cache.json"
    
    # 手動管理の休止情報ファイル
    MANUAL_FILE = "closures.json"
    
    # キャッシュの有効期限（時間）
    CACHE_DURATION_HOURS = 6
    
    def __init__(self, data_dir: str = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent / "data"
        
        self.cache_file = self.data_dir / self.CACHE_FILE
        self.manual_file = self.data_dir / self.MANUAL_FILE
        self.closures: List[ClosureInfo] = []
        self.last_updated: Optional[datetime] = None
        
        # まず手動管理ファイルを読み込む
        self._load_manual_closures()
        
        # キャッシュも読み込む（追加で）
        self._load_cache()
    
    def _load_manual_closures(self):
        """手動管理の休止情報ファイルを読み込む"""
        if self.manual_file.exists():
            try:
                with open(self.manual_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                manual_closures = [
                    ClosureInfo(**c) for c in data.get("closures", [])
                ]
                
                # 今日の日付でフィルタリング
                today = datetime.now().strftime("%Y-%m-%d")
                active_closures = []
                for c in manual_closures:
                    if c.start_date <= today and (c.end_date == "未定" or c.end_date >= today):
                        active_closures.append(c)
                
                self.closures = active_closures
                self.last_updated = datetime.now()
                print(f"✅ 手動休止情報読み込み: {len(active_closures)}件 (全{len(manual_closures)}件)")
            except Exception as e:
                print(f"⚠️ 手動休止情報読み込みエラー: {e}")
    
    def _load_cache(self):
        """キャッシュファイルから休止情報を読み込む（追加）"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                cached_closures = [
                    ClosureInfo(**c) for c in data.get("closures", [])
                ]
                
                # 既存の休止情報に追加（重複を避ける）
                existing_names = {c.attraction_name for c in self.closures}
                for c in cached_closures:
                    if c.attraction_name not in existing_names:
                        self.closures.append(c)
                
                if cached_closures:
                    print(f"✅ キャッシュ休止情報追加: {len(cached_closures)}件")
            except Exception as e:
                print(f"⚠️ 休止情報キャッシュ読み込みエラー: {e}")
    
    def _save_cache(self):
        """休止情報をキャッシュファイルに保存"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "closures": [asdict(c) for c in self.closures]
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 休止情報キャッシュ保存: {len(self.closures)}件")
        except Exception as e:
            print(f"⚠️ 休止情報キャッシュ保存エラー: {e}")
    
    def is_cache_valid(self) -> bool:
        """キャッシュが有効かどうか"""
        if not self.last_updated:
            return False
        
        elapsed = datetime.now() - self.last_updated
        return elapsed < timedelta(hours=self.CACHE_DURATION_HOURS)
    
    def fetch_closures(self, force: bool = False) -> List[ClosureInfo]:
        """
        休止情報を取得（手動管理ファイル優先）
        
        Args:
            force: Trueの場合、公式サイトからも取得を試みる
        """
        # 手動管理ファイルを再読み込み
        self._load_manual_closures()
        
        # キャッシュが有効な場合はそれを使う
        if not force and self.is_cache_valid() and self.closures:
            print(f"📦 休止情報使用: {len(self.closures)}件")
            return self.closures
        
        # 強制更新の場合のみ公式サイトから取得を試みる
        if force:
            print("🔄 公式サイトから休止情報を取得中...")
            
            online_closures = []
            for park, url in self.CLOSURE_URLS.items():
                try:
                    closures = self._fetch_from_url(park, url)
                    online_closures.extend(closures)
                except Exception as e:
                    print(f"⚠️ {park}の休止情報取得エラー: {e}")
            
            # 公式サイトから取得できた場合は追加
            if online_closures:
                existing_names = {c.attraction_name for c in self.closures}
                for c in online_closures:
                    if c.attraction_name not in existing_names:
                        self.closures.append(c)
                
                self.last_updated = datetime.now()
                self._save_cache()
        
        print(f"✅ 休止情報: {len(self.closures)}件")
        return self.closures
    
    def _fetch_from_url(self, park: str, url: str) -> List[ClosureInfo]:
        """URLから休止情報を取得"""
        closures = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; DisneyBot/1.0)"
            }
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8")
            
            # HTMLから休止情報を抽出（簡易的なパース）
            closures = self._parse_closure_html(park, html)
            
        except urllib.error.URLError as e:
            print(f"⚠️ URL接続エラー ({park}): {e}")
        except Exception as e:
            print(f"⚠️ 取得エラー ({park}): {e}")
        
        return closures
    
    def _parse_closure_html(self, park: str, html: str) -> List[ClosureInfo]:
        """HTMLから休止情報をパース（東京ディズニーリゾート公式サイト対応）"""
        closures = []
        
        # カテゴリを判定するための現在のセクション
        current_category = "attraction"
        
        # アコーディオンブロックを検出
        accordion_pattern = r'<div class="accordionTitle">([^<]+)</div>.*?<div class="accordionDetail">(.*?)</div>\s*<div class="accordionClose">'
        accordion_matches = re.findall(accordion_pattern, html, re.DOTALL)
        
        for category_name, content in accordion_matches:
            # カテゴリを判定
            if "アトラクション" in category_name:
                category = "attraction"
            elif "パレード" in category_name or "ショー" in category_name:
                category = "show"
            elif "レストラン" in category_name:
                category = "restaurant"
            elif "ショップ" in category_name:
                category = "shop"
            else:
                category = "other"
            
            # 各アイテムをパース
            # <p class="heading3">施設名</p> と 日付情報を取得
            item_pattern = r'<p class="heading3">([^<]+)</p>\s*<p>\s*(\d{4}/\d{1,2}/\d{1,2})\s*(?:-\s*(\d{4}/\d{1,2}/\d{1,2}|未定))?\s*</p>'
            items = re.findall(item_pattern, content, re.DOTALL)
            
            for item in items:
                try:
                    name = item[0].strip()
                    start_date = self._convert_date_format(item[1])
                    end_date = self._convert_date_format(item[2]) if item[2] else "未定"
                    
                    closures.append(ClosureInfo(
                        attraction_name=name,
                        park=park,
                        start_date=start_date,
                        end_date=end_date,
                        reason="refurbishment" if category in ["attraction", "restaurant", "shop"] else "seasonal",
                        note=f"カテゴリ: {category_name.strip()}"
                    ))
                except Exception as e:
                    print(f"  パースエラー: {e}")
                    continue
        
        # アコーディオンが見つからない場合のフォールバック
        if not closures:
            # 簡易パターン
            simple_pattern = r'<p class="heading3">([^<]+)</p>\s*<p>\s*(\d{4}/\d{1,2}/\d{1,2})\s*-?\s*(\d{4}/\d{1,2}/\d{1,2}|未定)?'
            matches = re.findall(simple_pattern, html, re.DOTALL)
            
            for match in matches:
                try:
                    name = match[0].strip()
                    start_date = self._convert_date_format(match[1])
                    end_date = self._convert_date_format(match[2]) if match[2] else "未定"
                    
                    closures.append(ClosureInfo(
                        attraction_name=name,
                        park=park,
                        start_date=start_date,
                        end_date=end_date,
                        reason="refurbishment"
                    ))
                except Exception:
                    continue
        
        return closures
    
    def _convert_date_format(self, date_str: str) -> str:
        """日付フォーマットを変換（2025/1/6 -> 2025-01-06）"""
        if not date_str or date_str == "未定":
            return "未定"
        
        date_str = date_str.strip()
        
        # YYYY/M/D形式
        match = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        return date_str
    
    def _parse_date(self, date_str: str) -> str:
        """日付文字列をYYYY-MM-DD形式に変換"""
        # "2025年1月6日" -> "2025-01-06"
        match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        return date_str
    
    def _get_manual_closures(self) -> List[ClosureInfo]:
        """
        手動で管理する休止情報
        公式サイトからの取得が難しい場合や、既知の休止情報を補完
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 2025年の既知の休止情報
        known_closures = [
            # ディズニーランド
            ClosureInfo(
                attraction_name="スプラッシュ・マウンテン",
                park="tdl",
                start_date="2024-10-01",
                end_date="2025-09-30",
                reason="refurbishment",
                note="ティアナのバイユーアドベンチャーへリニューアル"
            ),
            # 定期点検などの休止情報があれば追加
        ]
        
        # 期間内の休止のみ返す
        valid_closures = []
        for c in known_closures:
            if c.end_date == "未定" or c.end_date >= today:
                if c.start_date <= today:
                    valid_closures.append(c)
        
        return valid_closures
    
    def get_closures(self, date: str = None) -> List[ClosureInfo]:
        """
        指定日の休止情報を取得
        
        Args:
            date: YYYY-MM-DD形式の日付、Noneなら今日
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 最新の情報を取得
        all_closures = self.fetch_closures()
        
        # 指定日に休止中のもののみフィルタ
        active_closures = []
        for c in all_closures:
            start = c.start_date
            end = c.end_date
            
            if start <= date and (end == "未定" or end >= date):
                active_closures.append(c)
        
        return active_closures
    
    def get_closed_attractions(self, park: str = None, date: str = None) -> List[str]:
        """
        休止中のアトラクション名のリストを取得
        
        Args:
            park: "tdl" or "tds"、Noneなら両方
            date: YYYY-MM-DD形式
        """
        closures = self.get_closures(date)
        
        closed = []
        for c in closures:
            if park is None or c.park == park:
                closed.append(c.attraction_name)
        
        return closed
    
    def is_closed(self, attraction_name: str, date: str = None) -> bool:
        """
        特定のアトラクションが休止中かどうか
        
        Args:
            attraction_name: アトラクション名（部分一致）
            date: YYYY-MM-DD形式
        """
        closed = self.get_closed_attractions(date=date)
        
        name_lower = attraction_name.lower().replace(" ", "").replace("・", "")
        
        for c in closed:
            c_lower = c.lower().replace(" ", "").replace("・", "")
            if name_lower in c_lower or c_lower in name_lower:
                return True
        
        return False
    
    def format_closures(self, park: str = None, date: str = None) -> str:
        """休止情報をテキストでフォーマット"""
        closures = self.get_closures(date)
        
        if park:
            closures = [c for c in closures if c.park == park]
        
        if not closures:
            return "現在、休止中のアトラクションはありません。"
        
        msg = "🔧 **休止中のアトラクション**\n\n"
        
        # パーク別にグループ化
        tdl_closures = [c for c in closures if c.park == "tdl"]
        tds_closures = [c for c in closures if c.park == "tds"]
        
        if tdl_closures and (not park or park == "tdl"):
            msg += "**🏰 ディズニーランド**\n"
            for c in tdl_closures:
                end_display = c.end_date if c.end_date != "未定" else "再開時期未定"
                msg += f"・{c.attraction_name}\n"
                msg += f"  期間: {c.start_date} ～ {end_display}\n"
                if c.note:
                    msg += f"  💡 {c.note}\n"
            msg += "\n"
        
        if tds_closures and (not park or park == "tds"):
            msg += "**🌊 ディズニーシー**\n"
            for c in tds_closures:
                end_display = c.end_date if c.end_date != "未定" else "再開時期未定"
                msg += f"・{c.attraction_name}\n"
                msg += f"  期間: {c.start_date} ～ {end_display}\n"
                if c.note:
                    msg += f"  💡 {c.note}\n"
        
        return msg
    
    def update_from_json(self, closures_data: List[Dict]):
        """
        JSONデータから休止情報を更新（手動更新用）
        
        Args:
            closures_data: [{"attraction_name": "...", "park": "tdl", ...}, ...]
        """
        self.closures = [ClosureInfo(**c) for c in closures_data]
        self.last_updated = datetime.now()
        self._save_cache()
        print(f"✅ 休止情報を手動更新: {len(self.closures)}件")


# テスト用
if __name__ == "__main__":
    service = ClosureService()
    
    print("=== 休止情報サービステスト ===\n")
    
    # 休止情報を取得
    closures = service.fetch_closures()
    
    print("\n" + service.format_closures())
    
    # 特定アトラクションの休止チェック
    print("\n=== 休止チェック ===")
    test_attractions = ["スプラッシュ", "ソアリン", "美女と野獣"]
    for name in test_attractions:
        is_closed = service.is_closed(name)
        status = "❌ 休止中" if is_closed else "✅ 運営中"
        print(f"{name}: {status}")

