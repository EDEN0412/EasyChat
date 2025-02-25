#!/bin/bash
# Renderデプロイ用ビルドスクリプト

# Pythonパッケージのインストール
pip install -r requirements.txt

# データベースのマイグレーション
echo "データベースマイグレーションを実行します..."
python -m flask db upgrade || {
  echo "マイグレーションに失敗しました。マイグレーションをリセットします..."
  
  # マイグレーションディレクトリを削除
  rm -rf migrations/
  
  # マイグレーションを初期化
  python -m flask db init
  
  # 既存のデータベーススキーマからマイグレーションを生成
  python -m flask db migrate -m "既存データベースからの初期マイグレーション"
  
  # マイグレーションを適用
  python -m flask db upgrade
}

echo "マイグレーション完了！" 