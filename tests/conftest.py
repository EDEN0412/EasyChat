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
    
    # 環境変数からデータベース名を取得（環境変数が設定されていればそれを優先）
    test_db = os.environ.get('MYSQL_DATABASE')
    if test_db:
        print(f"[pytest_configure] 環境変数から取得したデータベース: {test_db}")
    else:
        test_db = os.getenv('MYSQL_DATABASE')
        print(f"[pytest_configure] .env.testから取得したデータベース: {test_db}")
    
    print(f"[pytest_configure] MYSQL_USER: {os.getenv('MYSQL_USER')}")
    print(f"[pytest_configure] MYSQL_HOST: {os.getenv('MYSQL_HOST')}")
    print(f"[pytest_configure] MYSQL_PORT: {os.getenv('MYSQL_PORT')}")

class CustomTestConfig(TestConfig):
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        # 環境変数からデータベース名を取得
        test_db = os.environ.get('MYSQL_DATABASE', os.getenv('MYSQL_DATABASE'))
        return f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD', '')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{test_db}"

@pytest.fixture(scope='session')
def app():
    """テスト用のアプリケーションを作成"""
    # テスト環境であることを明示的に設定
    os.environ['FLASK_ENV'] = 'testing'
    
    # CustomTestConfigを使用してアプリケーションを作成
    app = create_app(CustomTestConfig())
    
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

@pytest.fixture
def auth_client(client, app):
    """認証済みのテストクライアント"""
    from flask_login import login_user
    from app.models.user import User
    
    # テスト用ユーザーを作成
    with app.app_context():
        # まず既存のユーザーを確認
        user = User.query.filter_by(username='testuser').first()
        if not user:
            # ユーザーが存在しない場合は作成
            user = User(
                id='test-user-id',
                username='testuser',
                password_hash='dummy_hash'
            )
            db.session.add(user)
            db.session.commit()
        
        # ユーザーをログイン状態にする
        with client.session_transaction() as session:
            session['user_id'] = user.id
            
        # Flask-Loginでログイン
        with app.test_request_context():
            login_user(user)
            client.get('/')  # セッションを確立するための呼び出し
            
    return client 