import pytest
from app import create_app, db
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    PROPAGATE_EXCEPTIONS = False
    SERVER_NAME = 'localhost'
    SOCKETIO_ENABLED = False

@pytest.fixture
def app():
    """テスト用のアプリケーションを作成"""
    app = create_app(TestConfig)
    app.config['TESTING'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

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