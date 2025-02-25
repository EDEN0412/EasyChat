import pytest
from app import create_app, db
from config import TestConfig
import os
import sys
from dotenv import load_dotenv

def pytest_configure(config):
    """テスト開始前の設定"""
    # テスト環境であることを明示的に設定
    os.environ['FLASK_ENV'] = 'testing'
    
    # .env.testファイルを明示的に読み込む
    load_dotenv('.env.test', override=True)
    print(f"[pytest_configure] Using test database: {os.getenv('MYSQL_DATABASE')}")
    print(f"[pytest_configure] MYSQL_USER: {os.getenv('MYSQL_USER')}")
    print(f"[pytest_configure] MYSQL_HOST: {os.getenv('MYSQL_HOST')}")
    print(f"[pytest_configure] MYSQL_PORT: {os.getenv('MYSQL_PORT')}")

@pytest.fixture(scope='session')
def app():
    """テスト用のアプリケーションを作成"""
    # テスト環境であることを明示的に設定
    os.environ['FLASK_ENV'] = 'testing'
    
    # TestConfigを使用してアプリケーションを作成
    app = create_app(TestConfig)
    
    # 使用されるデータベースURIを確認
    print(f"[app fixture] Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"[app fixture] TESTING: {app.config['TESTING']}")
    
    with app.app_context():
        # テスト用データベースの初期化
        db.drop_all()  # 既存のテーブルを削除
        db.create_all()  # テーブルを再作成
        
        # テーブルが作成されたことを確認
        tables = db.engine.table_names()
        print(f"[app fixture] Created tables: {tables}")
        
        yield app
        db.session.remove()

@pytest.fixture
def client(app):
    """テスト用のクライアントを作成"""
    return app.test_client()

@pytest.fixture(autouse=True)
def setup_test_transaction():
    """各テストの前にトランザクションを開始し、テスト後にロールバックする"""
    # テーブルをクリーンアップ
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()

    try:
        yield
    finally:
        db.session.rollback()
        db.session.remove() 