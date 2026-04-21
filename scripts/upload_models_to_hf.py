#!/usr/bin/env python3
"""
Disney 予測モデルを Hugging Face Hub の private リポジトリに一括アップロード。

事前に環境変数 (or .env) で HF_TOKEN / HF_MODEL_REPO を設定:
    HF_TOKEN=hf_xxx
    HF_MODEL_REPO=yeonggil777/disney-wait-models

使い方:
    python scripts/upload_models_to_hf.py
    python scripts/upload_models_to_hf.py --dirs models_v3 models_land_v3   # 一部だけ
"""

from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.absolute()
os.chdir(PROJECT_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / '.env')
except ImportError:
    pass

from huggingface_hub import HfApi, create_repo

DEFAULT_DIRS = ["models", "models_v2", "models_v3", "models_land_v3"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Disney models to HF Hub")
    parser.add_argument("--dirs", nargs="+", default=DEFAULT_DIRS,
                        help="アップロード対象のモデルディレクトリ")
    parser.add_argument("--repo", type=str,
                        default=os.environ.get("HF_MODEL_REPO"),
                        help="HF リポジトリ ID ({user}/{repo}) — 省略時 HF_MODEL_REPO env")
    parser.add_argument("--public", action="store_true",
                        help="public リポジトリで作る (デフォルト private)")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("❌ HF_TOKEN 環境変数が必要です")
        return 1
    if not args.repo:
        print("❌ HF_MODEL_REPO env または --repo の指定が必要です")
        return 1

    api = HfApi(token=token)

    print(f"📦 リポジトリ準備: {args.repo} (private={not args.public})")
    create_repo(
        repo_id=args.repo,
        token=token,
        private=not args.public,
        repo_type="model",
        exist_ok=True,
    )
    print(f"   ✓ リポジトリ OK: https://huggingface.co/{args.repo}")

    for d in args.dirs:
        local_path = PROJECT_DIR / d
        if not local_path.exists():
            print(f"  ⚠️  {d}: ローカルに存在しません — スキップ")
            continue
        size_mb = sum(f.stat().st_size for f in local_path.rglob("*") if f.is_file()) / 1024 / 1024
        print(f"\n📤 アップロード中: {d} ({size_mb:.1f} MB)")
        api.upload_folder(
            folder_path=str(local_path),
            repo_id=args.repo,
            repo_type="model",
            path_in_repo=d,
            commit_message=f"upload {d}",
            token=token,
        )
        print(f"   ✅ {d} アップロード完了")

    print(f"\n🎉 全アップロード完了: https://huggingface.co/{args.repo}/tree/main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
