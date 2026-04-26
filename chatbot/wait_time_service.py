"""
待ち時間サービス - リアルタイム/予測待ち時間の取得
"""
import os
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
import urllib.request
import urllib.error


@dataclass
class WaitTimeInfo:
    """待ち時間情報"""
    attraction_id: str
    attraction_name: str
    wait_minutes: int
    is_operating: bool
    is_realtime: bool  # True=リアルタイム, False=予測
    last_updated: datetime
    source: str


class WaitTimeService:
    """待ち時間サービス"""
    
    # アトラクションID→名前のマッピング（主要なもの）
    ATTRACTION_NAMES = {
        # ディズニーランド
        "tdl_beauty_beast": "美女と野獣\"魔法のものがたり\"",
        "tdl_big_thunder": "ビッグサンダー・マウンテン",
        "tdl_space_mountain": "スペース・マウンテン",
        "tdl_splash_mountain": "スプラッシュ・マウンテン",
        "tdl_haunted_mansion": "ホーンテッドマンション",
        "tdl_pirates": "カリブの海賊",
        "tdl_pooh": "プーさんのハニーハント",
        "tdl_baymax": "ベイマックスのハッピーライド",
        "tdl_buzz": "バズ・ライトイヤーのアストロブラスター",
        "tdl_monsters": "モンスターズ・インク\"ライド&ゴーシーク!\"",
        # ディズニーシー
        "tds_tower_terror": "タワー・オブ・テラー",
        "tds_toy_story": "トイ・ストーリー・マニア！",
        "tds_soaring": "ソアリン:ファンタスティック・フライト",
        "tds_center_earth": "センター・オブ・ジ・アース",
        "tds_indiana": "インディ・ジョーンズ・アドベンチャー",
        "tds_raging": "レイジングスピリッツ",
        "tds_nemo": "ニモ&フレンズ・シーライダー",
        "tds_anna_elsa": "アナとエルサのフローズンジャーニー",
        "tds_rapunzel": "ラプンツェルのランタンフェスティバル",
        "tds_peter_pan": "ピーターパンのネバーランドアドベンチャー",
    }
    
    def __init__(self, prediction_dir: str = None):
        """
        Args:
            prediction_dir: 待ち時間予測CSVがあるディレクトリ
        """
        if prediction_dir:
            self.prediction_dir = Path(prediction_dir)
        else:
            # デフォルトは親ディレクトリのpredictions
            self.prediction_dir = Path(__file__).parent.parent / "predictions"
        
        self.cache = {}
        self.cache_time = None
        self.cache_duration = timedelta(minutes=5)  # 5分間キャッシュ
    
    def get_wait_times(self, park: str = None) -> List[WaitTimeInfo]:
        """
        待ち時間を取得
        
        Args:
            park: "tdl" または "tds"（Noneなら両方）
        """
        # キャッシュチェック
        if self.cache and self.cache_time and datetime.now() - self.cache_time < self.cache_duration:
            return self._filter_by_park(list(self.cache.values()), park)
        
        wait_times = []
        
        # 1. まず予測データを試す
        prediction_data = self._get_prediction_data()
        if prediction_data:
            wait_times = prediction_data
        
        # 2. 予測データがない場合はデフォルト値を使用
        if not wait_times:
            wait_times = self._get_default_wait_times()
        
        # キャッシュに保存
        self.cache = {wt.attraction_id: wt for wt in wait_times}
        self.cache_time = datetime.now()
        
        return self._filter_by_park(wait_times, park)
    
    def get_wait_time(self, attraction_name: str) -> Optional[WaitTimeInfo]:
        """
        特定のアトラクションの待ち時間を取得
        
        Args:
            attraction_name: アトラクション名（部分一致可）
        """
        wait_times = self.get_wait_times()
        name_lower = attraction_name.lower().replace(" ", "").replace("・", "")
        
        for wt in wait_times:
            if name_lower in wt.attraction_name.lower().replace(" ", "").replace("・", ""):
                return wt
        
        return None
    
    def _get_prediction_data(self) -> List[WaitTimeInfo]:
        """予測データを取得"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 日付別フォルダを探す
        prediction_paths = [
            self.prediction_dir / today / f"prediction_{today}.csv",
            self.prediction_dir / f"prediction_{today}.csv",
        ]
        
        for path in prediction_paths:
            if path.exists():
                return self._parse_prediction_csv(path)
        
        return []
    
    def _parse_prediction_csv(self, csv_path: Path) -> List[WaitTimeInfo]:
        """予測CSVをパース"""
        wait_times = []
        current_hour = datetime.now().hour
        
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 現在時刻に近い行を探す
                    time_str = row.get("time", row.get("時間", ""))
                    if not time_str:
                        continue
                    
                    try:
                        hour = int(time_str.split(":")[0])
                        if hour != current_hour:
                            continue
                    except (ValueError, IndexError):
                        continue
                    
                    # アトラクション名と待ち時間を取得
                    for col_name, value in row.items():
                        if col_name in ["time", "時間", "date", "日付"]:
                            continue
                        
                        try:
                            wait_minutes = int(float(value))
                            wait_times.append(WaitTimeInfo(
                                attraction_id=self._name_to_id(col_name),
                                attraction_name=col_name,
                                wait_minutes=wait_minutes,
                                is_operating=wait_minutes > 0,
                                is_realtime=False,
                                last_updated=datetime.now(),
                                source="prediction"
                            ))
                        except (ValueError, TypeError):
                            continue
        except Exception as e:
            print(f"Error parsing prediction CSV: {e}")
        
        return wait_times
    
    def _name_to_id(self, name: str) -> str:
        """名前からIDを生成"""
        # 既知のマッピングを逆引き
        for id_, n in self.ATTRACTION_NAMES.items():
            if name in n or n in name:
                return id_
        
        # 見つからない場合は名前からIDを生成
        return name.lower().replace(" ", "_").replace("・", "_")
    
    def _get_default_wait_times(self) -> List[WaitTimeInfo]:
        """デフォルトの待ち時間（平均値）"""
        now = datetime.now()
        hour = now.hour
        is_weekend = now.weekday() >= 5
        
        # 時間帯による係数
        if 9 <= hour < 11:
            time_factor = 0.8  # 朝は少なめ
        elif 11 <= hour < 14:
            time_factor = 1.2  # 昼は多め
        elif 14 <= hour < 17:
            time_factor = 1.0  # 午後は普通
        else:
            time_factor = 0.7  # 夕方以降は少なめ
        
        # 休日係数
        weekend_factor = 1.3 if is_weekend else 1.0
        
        # 基準待ち時間
        base_times = {
            "tdl_beauty_beast": 70,
            "tdl_big_thunder": 50,
            "tdl_space_mountain": 55,
            "tdl_splash_mountain": 60,
            "tdl_haunted_mansion": 25,
            "tdl_pirates": 20,
            "tdl_pooh": 55,
            "tdl_baymax": 60,
            "tdl_buzz": 40,
            "tdl_monsters": 45,
            "tds_tower_terror": 75,
            "tds_toy_story": 80,
            "tds_soaring": 70,
            "tds_center_earth": 60,
            "tds_indiana": 55,
            "tds_raging": 45,
            "tds_nemo": 40,
            "tds_anna_elsa": 120,
            "tds_rapunzel": 100,
            "tds_peter_pan": 110,
        }
        
        wait_times = []
        for id_, base_time in base_times.items():
            calculated_time = int(base_time * time_factor * weekend_factor)
            wait_times.append(WaitTimeInfo(
                attraction_id=id_,
                attraction_name=self.ATTRACTION_NAMES.get(id_, id_),
                wait_minutes=calculated_time,
                is_operating=True,
                is_realtime=False,
                last_updated=now,
                source="estimate"
            ))
        
        return wait_times
    
    def _filter_by_park(self, wait_times: List[WaitTimeInfo], park: str = None) -> List[WaitTimeInfo]:
        """パークでフィルタリング"""
        if not park:
            return wait_times
        
        return [wt for wt in wait_times if wt.attraction_id.startswith(park)]
    
    def format_wait_times_summary(self, park: str = None) -> str:
        """待ち時間のサマリーをフォーマット"""
        wait_times = self.get_wait_times(park)
        
        if not wait_times:
            return "現在、待ち時間情報を取得できません。"
        
        # 待ち時間でソート
        wait_times.sort(key=lambda x: x.wait_minutes, reverse=True)
        
        now = datetime.now()
        msg = f"⏰ **待ち時間情報** ({now.strftime('%H:%M')}更新)\n\n"
        
        # パーク別に分類
        tdl_times = [wt for wt in wait_times if wt.attraction_id.startswith("tdl")]
        tds_times = [wt for wt in wait_times if wt.attraction_id.startswith("tds")]
        
        if tdl_times and (not park or park == "tdl"):
            msg += "**🏰 ディズニーランド**\n"
            for wt in tdl_times[:5]:
                status = "🔴" if wt.wait_minutes >= 60 else "🟡" if wt.wait_minutes >= 30 else "🟢"
                msg += f"{status} {wt.attraction_name}: {wt.wait_minutes}分\n"
            msg += "\n"
        
        if tds_times and (not park or park == "tds"):
            msg += "**🌊 ディズニーシー**\n"
            for wt in tds_times[:5]:
                status = "🔴" if wt.wait_minutes >= 60 else "🟡" if wt.wait_minutes >= 30 else "🟢"
                msg += f"{status} {wt.attraction_name}: {wt.wait_minutes}分\n"
        
        source = wait_times[0].source if wait_times else "unknown"
        if source == "prediction":
            msg += "\n_※予測データに基づく待ち時間です_"
        elif source == "estimate":
            msg += "\n_※推定値です。実際の待ち時間は異なる場合があります_"
        
        return msg


# テスト用
if __name__ == "__main__":
    service = WaitTimeService()
    
    print("=== 待ち時間サービステスト ===\n")
    
    # 全体の待ち時間
    print(service.format_wait_times_summary())
    
    # 特定アトラクション
    print("\n=== 特定アトラクション ===")
    wt = service.get_wait_time("トイストーリー")
    if wt:
        print(f"{wt.attraction_name}: {wt.wait_minutes}分 (source: {wt.source})")




