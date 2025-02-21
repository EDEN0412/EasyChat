import pytest
from flask import url_for, session
from app import create_app, db
from app.models import User
from app.auth import create_user

@pytest.fixture
def app():
    """テスト用のアプリケーションインスタンスを作成"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # テスト用にCSRF保護を無効化
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """テスト用のクライアントを作成"""
    return app.test_client()

@pytest.fixture
def test_user(app):
    """テスト用のユーザーを作成"""
    with app.app_context():
        user = create_user('testuser', 'password123')
        return user

def test_index_page(client):
    """トップページのテスト"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'EasyChat' in response.data

def test_login_page(client):
    """ログインページのテスト"""
    # GETリクエスト
    response = client.get('/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower()

    # 正常系：正しい認証情報でのPOSTリクエスト
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # 異常系：誤った認証情報でのPOSTリクエスト
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    })
    assert b'username' in response.data.lower()

def test_register_page(client):
    """新規登録ページのテスト"""
    # GETリクエスト
    response = client.get('/register')
    assert response.status_code == 200
    assert b'register' in response.data.lower()

    # 正常系：有効な情報でのPOSTリクエスト
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'newpass123',
        'password_confirm': 'newpass123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # 異常系：パスワード不一致
    response = client.post('/register', data={
        'username': 'newuser2',
        'password': 'pass123',
        'password_confirm': 'pass456'
    })
    assert b'password' in response.data.lower()

def test_protected_routes(client, test_user):
    """認証が必要なルートのテスト"""
    # 未ログイン時のアクセス
    response = client.get('/chat/messages', follow_redirects=True)
    assert response.status_code == 403  # Forbidden

    # ログイン
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # ログイン後のアクセス
    response = client.get('/chat/messages', follow_redirects=True)
    assert response.status_code == 200
    assert b'messages' in response.data.lower()

def test_logout(client, test_user):
    """ログアウト機能のテスト"""
    # まずログイン
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })

    # ログアウト
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower()

    # ログアウト後の保護されたページへのアクセス
    response = client.get('/chat/messages', follow_redirects=True)
    assert response.status_code == 403  # Forbidden 