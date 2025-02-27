import pytest
from app import create_app, db
from app.models import User
from app.auth import create_user, authenticate_user, hash_password

@pytest.fixture
def app():
    """テスト用のアプリケーションインスタンスを作成"""
    app = create_app()
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()  # トランザクションをロールバック

@pytest.fixture
def client(app):
    """テスト用のクライアントを作成"""
    return app.test_client()

def test_user_registration(app):
    """ユーザー登録のテスト"""
    with app.app_context():
        # 正常系：有効なユーザー名とパスワード
        user = create_user('testuser', 'password123')
        assert user.username == 'testuser'
        assert user.password_hash != 'password123'  # パスワードがハッシュ化されていることを確認
        
        # 異常系：既存ユーザー名
        with pytest.raises(Exception):
            create_user('testuser', 'password456')

def test_user_authentication(app):
    """ユーザー認証のテスト"""
    with app.app_context():
        # ユーザーを作成
        create_user('testuser', 'password123')
        
        # 正常系：正しい認証情報
        user = authenticate_user('testuser', 'password123')
        assert user is not None
        assert user.username == 'testuser'
        
        # 異常系：存在しないユーザー
        user = authenticate_user('nonexistent', 'password123')
        assert user is None
        
        # 異常系：誤ったパスワード
        user = authenticate_user('testuser', 'wrongpassword')
        assert user is None

def test_password_hashing(app):
    """パスワードハッシュ化のテスト"""
    with app.app_context():
        # 同じパスワードでも異なるハッシュ値が生成されることを確認
        hash1 = hash_password('password123')
        hash2 = hash_password('password123')
        assert hash1 != hash2
        
        # ハッシュ値がパスワードと一致しないことを確認
        assert hash1 != 'password123' 