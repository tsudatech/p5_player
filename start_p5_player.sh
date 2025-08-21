#!/bin/bash

# p5_player起動スクリプト
# デスクトップから実行するためのシェルスクリプト

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# プロジェクトディレクトリに移動
cd "$SCRIPT_DIR"

# Python仮想環境が存在するかチェック
if [ -d "venv" ]; then
    echo "仮想環境をアクティベート中..."
    source venv/bin/activate
else
    echo "仮想環境が見つかりません。作成しますか？ (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "仮想環境を作成中..."
        python3 -m venv venv
        source venv/bin/activate
        echo "依存関係をインストール中..."
        pip install -r requirements.txt
    else
        echo "仮想環境なしで実行します..."
    fi
fi

# 必要な依存関係をチェック
if [ -f "requirements.txt" ]; then
    echo "依存関係をチェック中..."
    pip install -r requirements.txt
fi

# p5_playerを起動
echo "p5_playerを起動中..."
python p5_player.py

# エラーが発生した場合の処理
if [ $? -ne 0 ]; then
    echo "エラーが発生しました。Enterキーを押して終了してください。"
    read -r
fi 