"""
画像サービス - 隠れミッキーなどの画像管理
"""
import os
import json
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ImageInfo:
    """画像情報"""
    id: str
    filename: str
    original_name: str
    category: str  # hidden_mickey, attraction, restaurant, etc.
    location: str  # エリアや場所
    description: str
    hint: str
    difficulty: str  # easy, medium, hard
    park: str  # tdl, tds
    uploaded_at: str
    tags: List[str]


class ImageService:
    """画像管理サービス"""
    
    def __init__(self, static_dir: str = None, data_dir: str = None):
        if static_dir:
            self.static_dir = Path(static_dir)
        else:
            self.static_dir = Path(__file__).parent / "static"
        
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent / "data"
        
        self.images_dir = self.static_dir / "images"
        self.hidden_mickey_dir = self.images_dir / "hidden_mickeys"
        
        # ディレクトリを作成
        self.hidden_mickey_dir.mkdir(parents=True, exist_ok=True)
        
        # 画像メタデータ
        self.metadata_file = self.data_dir / "image_metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, ImageInfo]:
        """メタデータを読み込む"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        k: ImageInfo(**v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"Error loading image metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """メタデータを保存"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(
                    {k: asdict(v) for k, v in self.metadata.items()},
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            print(f"Error saving image metadata: {e}")
    
    def add_image(self, 
                  file_path: str, 
                  category: str,
                  location: str,
                  description: str,
                  hint: str = "",
                  difficulty: str = "medium",
                  park: str = "",
                  tags: List[str] = None) -> Optional[ImageInfo]:
        """
        画像を追加
        
        Args:
            file_path: 元の画像ファイルパス
            category: カテゴリ（hidden_mickey, attraction, etc.）
            location: 場所
            description: 説明
            hint: ヒント
            difficulty: 難易度
            park: パーク（tdl/tds）
            tags: タグ
        """
        source_path = Path(file_path)
        if not source_path.exists():
            print(f"File not found: {file_path}")
            return None
        
        # IDを生成
        image_id = str(uuid.uuid4())[:8]
        
        # ファイル名を生成
        ext = source_path.suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            print(f"Unsupported image format: {ext}")
            return None
        
        new_filename = f"{image_id}{ext}"
        
        # カテゴリ別のディレクトリ
        if category == "hidden_mickey":
            dest_dir = self.hidden_mickey_dir
        else:
            dest_dir = self.images_dir / category
            dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / new_filename
        
        # ファイルをコピー
        shutil.copy2(source_path, dest_path)
        
        # メタデータを作成
        info = ImageInfo(
            id=image_id,
            filename=new_filename,
            original_name=source_path.name,
            category=category,
            location=location,
            description=description,
            hint=hint,
            difficulty=difficulty,
            park=park,
            uploaded_at=datetime.now().isoformat(),
            tags=tags or []
        )
        
        self.metadata[image_id] = info
        self._save_metadata()
        
        return info
    
    def get_image(self, image_id: str) -> Optional[ImageInfo]:
        """画像情報を取得"""
        return self.metadata.get(image_id)
    
    def get_image_url(self, image_id: str) -> Optional[str]:
        """画像のURLを取得"""
        info = self.metadata.get(image_id)
        if info:
            if info.category == "hidden_mickey":
                return f"/static/images/hidden_mickeys/{info.filename}"
            else:
                return f"/static/images/{info.category}/{info.filename}"
        return None
    
    def get_images_by_category(self, category: str) -> List[ImageInfo]:
        """カテゴリ別に画像を取得"""
        return [
            info for info in self.metadata.values()
            if info.category == category
        ]
    
    def get_images_by_location(self, location: str) -> List[ImageInfo]:
        """場所別に画像を取得"""
        location_lower = location.lower()
        return [
            info for info in self.metadata.values()
            if location_lower in info.location.lower()
        ]
    
    def get_hidden_mickey_images(self, park: str = None, area: str = None) -> List[ImageInfo]:
        """隠れミッキー画像を取得"""
        images = self.get_images_by_category("hidden_mickey")
        
        if park:
            images = [img for img in images if img.park == park]
        
        if area:
            area_lower = area.lower()
            images = [img for img in images if area_lower in img.location.lower()]
        
        return images
    
    def search_images(self, query: str) -> List[ImageInfo]:
        """画像を検索"""
        query_lower = query.lower()
        results = []
        
        for info in self.metadata.values():
            score = 0
            
            if query_lower in info.location.lower():
                score += 3
            if query_lower in info.description.lower():
                score += 2
            if any(query_lower in tag.lower() for tag in info.tags):
                score += 2
            if query_lower in info.hint.lower():
                score += 1
            
            if score > 0:
                results.append((score, info))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results]
    
    def delete_image(self, image_id: str) -> bool:
        """画像を削除"""
        info = self.metadata.get(image_id)
        if not info:
            return False
        
        # ファイルを削除
        if info.category == "hidden_mickey":
            file_path = self.hidden_mickey_dir / info.filename
        else:
            file_path = self.images_dir / info.category / info.filename
        
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Error deleting file: {e}")
        
        # メタデータから削除
        del self.metadata[image_id]
        self._save_metadata()
        
        return True
    
    def get_placeholder_hint_images(self) -> List[Dict]:
        """プレースホルダー画像のヒント情報（画像がない場合のテキストヒント）"""
        # 実際の画像がない場合のテキストベースのヒント
        return [
            {
                "id": "ph_1",
                "location": "ビッグサンダー・マウンテン待機列",
                "hint": "歯車が3つ並んでいる場所を探してみてください。壁の上部に注目！",
                "difficulty": "easy",
                "park": "tdl",
                "has_image": False
            },
            {
                "id": "ph_2",
                "location": "ホーンテッドマンションのダイニングルーム",
                "hint": "テーブルの上のお皿の配置を見てください。3つの丸い形が...",
                "difficulty": "medium",
                "park": "tdl",
                "has_image": False
            },
            {
                "id": "ph_3",
                "location": "トイ・ストーリー・マニア！待機列",
                "hint": "クレヨンで描かれた太陽の中にミッキーの形が隠れています",
                "difficulty": "easy",
                "park": "tds",
                "has_image": False
            },
            {
                "id": "ph_4",
                "location": "センター・オブ・ジ・アース待機列",
                "hint": "ネモ船長の研究室にある実験器具の配置を注意深く見ると...",
                "difficulty": "hard",
                "park": "tds",
                "has_image": False
            },
            {
                "id": "ph_5",
                "location": "ソアリン:ファンタスティック・フライト",
                "hint": "博物館内の地図の中に隠されています。海や大陸の形を見て",
                "difficulty": "medium",
                "park": "tds",
                "has_image": False
            }
        ]


# テスト用
if __name__ == "__main__":
    service = ImageService()
    
    print("=== 画像サービステスト ===")
    print(f"メタデータ数: {len(service.metadata)}")
    
    # プレースホルダーヒント
    print("\n=== プレースホルダーヒント ===")
    for hint in service.get_placeholder_hint_images():
        print(f"・{hint['location']}: {hint['hint'][:30]}...")




