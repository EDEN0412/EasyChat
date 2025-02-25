#!/bin/bash
# Renderデプロイ用ビルドスクリプト

# Pythonパッケージのインストール
pip install -r requirements.txt

# データベースのマイグレーション
python -m flask db upgrade 