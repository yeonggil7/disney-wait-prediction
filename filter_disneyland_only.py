#!/usr/bin/env python3
"""
既存CSVファイルからディズニーランドアトラクションのみを抽出
ディズニーシーアトラクションを除外
"""

import pandas as pd
import os
import glob

def get_disneyland_attractions():
    """ディズニーランドアトラクション一覧（省略形）"""
    return {
        'オムニバス',
        'リバ鉄道',  # ウエスタンリバー鉄道
        'カリブの海賊',
        'ジャングル',  # ジャングルクルーズ
        'ツリハウス',
        '魅惑のチキルム',  # 魅惑のチキルーム
        'ビッグサンダ',  # ビッグサンダーマウンテン
        'Ｓギャラリ',  # シューティングギャラリー
        'ベア・シアタ',  # カントリーベアシアター
        'いかだ',  # トムソーヤ島いかだ
        'スプラッシュ',  # スプラッシュマウンテン
        'イッツ・ア・ス',  # イッツ・ア・スモールワールド
        'ホーンテッド',  # ホーンテッドマンション
        'プーさん',  # プーさんのハニーハント
        'ホール・オ・',  # ホール・オブ・フェイム？
        'スタージェ',  # スタージェット
        'スペマン',  # スペースマウンテン
        'バズ',  # バズ・ライトイヤーのアストロブラスター
        'モンスタ',  # モンスターズ・インク
        'ディズニー'  # ミート・ミッキー
    }

def get_full_attraction_names():
    """省略形から正式名称へのマッピング"""
    return {
        'オムニバス': 'オムニバス',
        'リバ鉄道': 'ウエスタンリバー鉄道',
        'カリブの海賊': 'カリブの海賊',
        'ジャングル': 'ジャングルクルーズ',
        'ツリハウス': 'ツリーハウス',
        '魅惑のチキルム': '魅惑のチキルーム',
        'ビッグサンダ': 'ビッグサンダーマウンテン',
        'Ｓギャラリ': 'シューティングギャラリー',
        'ベア・シアタ': 'カントリーベアシアター',
        'いかだ': 'トムソーヤ島いかだ',
        'スプラッシュ': 'スプラッシュマウンテン',
        'イッツ・ア・ス': 'イッツ・ア・スモールワールド',
        'ホーンテッド': 'ホーンテッドマンション',
        'プーさん': 'プーさんのハニーハント',
        'ホール・オ・': 'ホール・オブ・フェイム',
        'スタージェ': 'スタージェット',
        'スペマン': 'スペースマウンテン',
        'バズ': 'バズ・ライトイヤーのアストロブラスター',
        'モンスタ': 'モンスターズ・インク',
        'ディズニー': 'ミート・ミッキー'
    }

def filter_disneyland_only(input_file, output_file):
    """単一CSVファイルをディズニーランドのみにフィルタリング"""
    try:
        print(f"📝 処理中: {input_file}")
        
        # CSVファイル読み込み
        df = pd.read_csv(input_file)
        
        # ディズニーランドアトラクション
        disneyland_attractions = get_disneyland_attractions()
        full_names = get_full_attraction_names()
        
        # ディズニーランドアトラクションのみを抽出
        disneyland_df = df[df['Attraction'].isin(disneyland_attractions)].copy()
        
        # 正式名称に変換
        disneyland_df['AttractionFull'] = disneyland_df['Attraction'].map(full_names)
        disneyland_df['Attraction'] = disneyland_df['AttractionFull']
        disneyland_df.drop('AttractionFull', axis=1, inplace=True)
        
        # 統計情報
        original_count = len(df)
        disneyland_count = len(disneyland_df)
        disneysea_count = original_count - disneyland_count
        
        print(f"  📊 元データ: {original_count}件")
        print(f"  🏰 ディズニーランド: {disneyland_count}件")
        print(f"  🌊 除外データ: {disneysea_count}件")
        
        # 出力ファイルに保存
        disneyland_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"  💾 保存完了: {output_file}")
        
        return True, disneyland_count, disneysea_count
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False, 0, 0

def filter_all_january_files():
    """1月の全CSVファイルをフィルタリング"""
    print("🏰 ディズニーランド専用データフィルタリング開始")
    print("🔍 1月のCSVファイルを処理してディズニーシーアトラクションを除外")
    print("=" * 70)
    
    # data/ディレクトリの1月CSVファイルを検索
    input_pattern = "data/yosocal_202501*.csv"
    input_files = glob.glob(input_pattern)
    
    if not input_files:
        print("❌ 対象CSVファイルが見つかりません")
        print(f"   検索パターン: {input_pattern}")
        return
    
    print(f"📁 発見ファイル数: {len(input_files)}個")
    
    total_success = 0
    total_disneyland = 0
    total_disneysea = 0
    
    # 出力ディレクトリ作成
    os.makedirs('data/disneyland_only', exist_ok=True)
    
    for input_file in sorted(input_files):
        # 出力ファイル名生成
        base_name = os.path.basename(input_file)
        output_name = base_name.replace('yosocal_', 'disneyland_only_')
        output_file = os.path.join('data/disneyland_only', output_name)
        
        # フィルタリング実行
        success, dl_count, ds_count = filter_disneyland_only(input_file, output_file)
        
        if success:
            total_success += 1
            total_disneyland += dl_count
            total_disneysea += ds_count
        
        print()  # 空行
    
    # 結果サマリー
    print("=" * 70)
    print(f"🎉 フィルタリング処理完了！")
    print(f"✅ 成功ファイル数: {total_success}/{len(input_files)}")
    print(f"🏰 ディズニーランドデータ: {total_disneyland:,}件")
    print(f"🌊 除外データ: {total_disneysea:,}件")
    print(f"📁 出力ディレクトリ: data/disneyland_only/")
    print(f"📋 ディズニーランドアトラクション数: {len(get_disneyland_attractions())}個")

if __name__ == "__main__":
    filter_all_january_files() 