import os
from app import create_app, db
from config import TestConfig

# テスト環境を設定
os.environ['FLASK_ENV'] = 'testing'

# テスト用アプリケーションを作成
app = create_app(TestConfig)

# アプリケーションコンテキスト内でテーブルを作成
with app.app_context():
    print("テストデータベースのテーブルを作成します...")
    db.create_all()
    print("テーブル作成完了！") 