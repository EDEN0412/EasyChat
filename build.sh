#!/bin/bash
# Renderデプロイ用ビルドスクリプト

# Pythonパッケージのインストール
pip install -r requirements.txt

# データベースの状態を確認
echo "データベースの状態を確認します..."
python - << EOF
from app import create_app, db
from app.models import User, Channel, Message, Reaction
import sqlalchemy as sa

app = create_app()
with app.app_context():
    # エンジンを取得
    engine = db.get_engine()
    
    # テーブルが存在するか確認
    inspector = sa.inspect(engine)
    tables = inspector.get_table_names()
    print(f"既存のテーブル: {tables}")
    
    # usersテーブルが存在しない場合は、マイグレーションをリセット
    if 'users' not in tables:
        print("usersテーブルが存在しません。マイグレーションをリセットします。")
        db.create_all()
        print("テーブルを直接作成しました。")
EOF

# データベースのマイグレーション
echo "データベースマイグレーションを実行します..."
python -m flask db init || echo "マイグレーションはすでに初期化されています"
python -m flask db migrate -m "既存データベースからの初期マイグレーション" || echo "マイグレーションの生成に失敗しました"
python -m flask db upgrade || echo "マイグレーションの適用に失敗しました"

# マイグレーションが失敗した場合のフォールバック
echo "テーブルの存在を再確認します..."
python - << EOF
from app import create_app, db
from app.models import User, Channel, Message, Reaction
import sqlalchemy as sa

app = create_app()
with app.app_context():
    # エンジンを取得
    engine = db.get_engine()
    
    # テーブルが存在するか確認
    inspector = sa.inspect(engine)
    tables = inspector.get_table_names()
    print(f"マイグレーション後のテーブル: {tables}")
    
    # usersテーブルが存在しない場合は、直接作成
    if 'users' not in tables:
        print("マイグレーション後もusersテーブルが存在しません。直接作成します。")
        db.create_all()
        print("テーブルを直接作成しました。")
EOF

echo "マイグレーション完了！" 