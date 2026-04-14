#!/usr/bin/env python3
"""
TDR 1日プラン X自動投稿スクリプト
- 毎日のおすすめプランを生成してXに投稿
- 画像付き投稿対応
"""

import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import numpy as np

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meirio', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']

from generate_daily_plan import generate_efficient_plan, format_plan_for_x, SEA_SHORT_NAMES, LAND_SHORT_NAMES
from post_via_xharness import post_to_twitter

load_dotenv()


# ========================================
# 画像生成
# ========================================

def generate_plan_image(result, output_dir="outputs"):
    """プランを視覚的なタイムライン画像として生成"""
    if result is None:
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    park = result['park']
    date_str = result['date']
    plan = result['plan']
    
    park_name = "ディズニーシー" if park == 'sea' else "ディズニーランド"
    short_names = SEA_SHORT_NAMES if park == 'sea' else LAND_SHORT_NAMES
    bg_color = '#1a1a2e' if park == 'sea' else '#2d1b4e'
    accent_color = '#00d4ff' if park == 'sea' else '#ff69b4'
    
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_names = ['月', '火', '水', '木', '金', '土', '日']
    day_name = day_names[dt.weekday()]
    
    # 図のサイズ設定
    fig, ax = plt.subplots(figsize=(8, 10), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    
    # タイトル
    title = f"🎢 {park_name} 回り方ガイド"
    subtitle = f"{dt.month}/{dt.day}({day_name}) AIおすすめプラン"
    
    ax.text(0.5, 0.98, title, transform=ax.transAxes, fontsize=22, fontweight='bold',
            color='white', ha='center', va='top')
    ax.text(0.5, 0.93, subtitle, transform=ax.transAxes, fontsize=14,
            color='#aaaaaa', ha='center', va='top')
    
    # タイムラインを描画
    num_items = len(plan)
    y_positions = np.linspace(0.85, 0.1, num_items)
    
    for i, (item, y_pos) in enumerate(zip(plan, y_positions)):
        time_str = item['time']
        attraction = item['attraction']
        wait = item['wait']
        action = item['action']
        
        # アイコンと色を決定
        if '🏃' in action:
            icon = '🏃'
            box_color = '#ff6b6b'
            text_color = 'white'
        elif '🍽️' in action:
            icon = '🍽️'
            box_color = '#4ecdc4'
            text_color = 'white'
        elif '🌙' in action:
            icon = '🌙'
            box_color = '#9b59b6'
            text_color = 'white'
        else:
            icon = '▶️'
            box_color = accent_color
            text_color = 'white'
        
        # 短縮名を使用
        if attraction in short_names:
            display_name = short_names[attraction]
        else:
            display_name = attraction[:10]
        
        # 時間ラベル
        ax.text(0.08, y_pos, time_str, transform=ax.transAxes, fontsize=14,
                color=accent_color, fontweight='bold', ha='left', va='center',
                family='monospace')
        
        # 接続線
        if i < num_items - 1:
            ax.plot([0.14, 0.14], [y_pos - 0.01, y_positions[i+1] + 0.01],
                   transform=ax.transAxes, color='#555555', linewidth=2,
                   linestyle='--', alpha=0.7)
        
        # ドット
        circle = plt.Circle((0.14, y_pos), 0.015, transform=ax.transAxes,
                            color=box_color, zorder=5)
        ax.add_patch(circle)
        
        # アトラクション名ボックス
        bbox = dict(boxstyle='round,pad=0.5', facecolor=box_color, alpha=0.8,
                   edgecolor='none')
        
        if wait > 0:
            text = f"{display_name} ({wait}分待ち)"
        else:
            text = display_name
        
        ax.text(0.2, y_pos, text, transform=ax.transAxes, fontsize=13,
                color=text_color, fontweight='bold', ha='left', va='center',
                bbox=bbox)
        
        # ヒントがあれば表示
        if item.get('tip'):
            ax.text(0.2, y_pos - 0.025, f"💡 {item['tip']}", transform=ax.transAxes,
                   fontsize=9, color='#ffcc00', ha='left', va='top')
    
    # サマリー情報
    total_wait = result['total_wait']
    attractions_count = result['attractions_count']
    
    summary = f"🎢 {attractions_count}アトラクション制覇  ⏱️ 合計待ち時間: 約{total_wait}分"
    ax.text(0.5, 0.03, summary, transform=ax.transAxes, fontsize=12,
            color='white', ha='center', va='bottom',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#333333', alpha=0.9))
    
    # 休止中アトラクション
    if result['closures']:
        closed_list = ', '.join([short_names.get(n, n[:6]) for n in result['closures'].keys()][:3])
        ax.text(0.5, 0.005, f"❌ 休止中: {closed_list}", transform=ax.transAxes,
               fontsize=9, color='#ff6b6b', ha='center', va='bottom')
    
    # 軸を非表示
    ax.axis('off')
    
    # 保存
    filename = f"plan_{park}_{date_str}.png"
    output_path = os.path.join(output_dir, filename)
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=bg_color, edgecolor='none')
    plt.close()
    
    print(f"📸 画像保存: {output_path}")
    return output_path


# ========================================
# X投稿
# ========================================

def post_to_x(text: str, image_path: str = None, max_retries: int = 3) -> bool:
    """post_via_xharness 経由で投稿"""
    images = [image_path] if image_path and os.path.exists(image_path) else None
    return post_to_twitter(text, images, max_retries)


# ========================================
# メイン処理
# ========================================

def main():
    parser = argparse.ArgumentParser(description='TDR 1日プラン X自動投稿')
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    parser.add_argument('--date', '-d', type=str, default=tomorrow,
                       help=f'対象日 (デフォルト: {tomorrow})')
    parser.add_argument('--park', '-p', type=str, default='both',
                       choices=['sea', 'land', 'both'],
                       help='パーク (デフォルト: both)')
    parser.add_argument('--post', action='store_true',
                       help='実際にXに投稿する')
    parser.add_argument('--dry-run', action='store_true',
                       help='投稿せずにプレビューのみ')
    parser.add_argument('--output-dir', '-o', type=str, default='outputs',
                       help='出力ディレクトリ')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎢 TDR 1日プラン X自動投稿")
    print("=" * 60)
    print(f"📅 対象日: {args.date}")
    print(f"🎡 パーク: {args.park}")
    print(f"📤 投稿: {'する' if args.post and not args.dry_run else 'しない (プレビュー)'}")
    print("=" * 60)
    
    parks = ['sea', 'land'] if args.park == 'both' else [args.park]
    
    for park in parks:
        print(f"\n{'🌊' if park == 'sea' else '🏰'} {park.upper()} プラン生成...")
        
        # プラン生成
        result = generate_efficient_plan(park, args.date)
        
        if result is None:
            print(f"❌ {park} プラン生成失敗")
            continue
        
        # X投稿用テキスト
        tweet_text = format_plan_for_x(result)
        
        # 画像生成
        image_path = generate_plan_image(result, args.output_dir)
        
        print("\n" + "-" * 50)
        print("📱 X投稿内容:")
        print("-" * 50)
        print(tweet_text)
        print("-" * 50)
        print(f"📝 文字数: {len(tweet_text)}/280")
        print(f"🖼️ 画像: {image_path}")
        
        # 投稿
        if args.post and not args.dry_run:
            print("\n📤 Xに投稿中...")
            success = post_to_x(tweet_text, image_path)
            if success:
                print("✅ 投稿完了!")
            else:
                print("❌ 投稿失敗")
            
            # 連続投稿の間隔
            if park == 'sea' and len(parks) > 1:
                print("⏳ 30秒待機...")
                time.sleep(30)
        else:
            print("\n💡 --post オプションで実際に投稿できます")
    
    print("\n" + "=" * 60)
    print("✅ 完了!")


if __name__ == "__main__":
    main()
