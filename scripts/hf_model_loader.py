"""
Hugging Face Hub からモデルを自動ダウンロードするヘルパー。

`ensure_model_dir(local_dir)` を呼ぶと:
  1. ローカル `local_dir` に必要ファイルが揃っていれば何もしない
  2. 揃ってなければ HF_MODEL_REPO の `local_dir/` フォルダから一式を DL

GitHub Actions ではモデルファイルを LFS / リポジトリに含めない代わりに、
predictor の `load_models()` 直前に呼ぶことでモデルを取得する。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

# 各 model_dir に最低限必要なファイル
REQUIRED_FILES = [
    "wait_time_models.joblib",
    "scaler.joblib",
    "feature_columns.joblib",
    "label_encoders.joblib",
]
OPTIONAL_FILES = ["model_config.joblib"]

PROJECT_DIR = Path(__file__).parent.parent.absolute()


def _all_present(local_dir: Path, files: Iterable[str]) -> bool:
    return all((local_dir / f).exists() and (local_dir / f).stat().st_size > 0
               for f in files)


def ensure_model_dir(local_dir: str) -> bool:
    """
    必要に応じて HF Hub から `local_dir` の中身を取得する。
    成功すれば True、HF が使えず取得失敗で False。

    対象ファイルが既に全部揃っていれば何もしない。
    """
    local_path = (PROJECT_DIR / local_dir).resolve()
    local_path.mkdir(parents=True, exist_ok=True)

    if _all_present(local_path, REQUIRED_FILES):
        return True

    repo_id = os.environ.get("HF_MODEL_REPO")
    token = os.environ.get("HF_TOKEN")
    if not repo_id:
        print(f"⚠️ {local_dir}: ローカルにモデルなし & HF_MODEL_REPO 未設定")
        return False

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print(f"⚠️ huggingface_hub が未インストール (pip install huggingface_hub)")
        return False

    print(f"📥 HF Hub からモデルDL中: {repo_id} → {local_dir}/")
    for fname in REQUIRED_FILES + OPTIONAL_FILES:
        target = local_path / fname
        if target.exists() and target.stat().st_size > 0:
            continue
        try:
            hf_hub_download(
                repo_id=repo_id,
                filename=f"{local_dir}/{fname}",
                local_dir=str(PROJECT_DIR),
                token=token,
                repo_type="model",
            )
            print(f"   ✓ {fname}")
        except Exception as e:
            if fname in OPTIONAL_FILES:
                print(f"   - {fname}: optional, skip ({e.__class__.__name__})")
                continue
            print(f"   ❌ {fname}: {e}")
            return False

    return _all_present(local_path, REQUIRED_FILES)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "models_v3"
    ok = ensure_model_dir(target)
    sys.exit(0 if ok else 1)
