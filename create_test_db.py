import os
from app import create_app, db
from config import TestConfig

# テスト環境を設定
os.environ['FLASK_ENV'] = 'testing'

# 環境変数からデータベース名を取得（デフォルトはtest_chatapp）
test_db = os.environ.get('MYSQL_DATABASE', 'test_chatapp')
print(f"使用するテストデータベース: {test_db}")

# TestConfigを拡張してデータベース名を上書き
class CustomTestConfig(TestConfig):
    SQLALCHEMY_DATABASE_URI = f"mysql://{os.environ.get('MYSQL_USER', 'chatapp_user')}:{os.environ.get('MYSQL_PASSWORD', '')}@{os.environ.get('MYSQL_HOST', 'localhost')}:{os.environ.get('MYSQL_PORT', '3306')}/{test_db}"

# テスト用アプリケーションを作成
app = create_app(CustomTestConfig)

# アプリケーションコンテキスト内でテーブルを作成
with app.app_context():
    print("テストデータベースのテーブルを作成します...")
    db.create_all()
    print("テーブル作成完了！") 