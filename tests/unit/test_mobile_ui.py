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
    app.config['WTF_CSRF_ENABLED'] = False  # テスト用にCSRF保護を無効化
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()  # トランザクションをロールバック

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

def test_responsive_headers(client):
    """レスポンシブデザインのためのビューポートメタタグが正しく設定されているかテスト"""
    response = client.get('/')
    assert b'<meta name="viewport" content="width=device-width, initial-scale=1.0">' in response.data

def test_mobile_ui_elements(client, test_user):
    """モバイルUI要素が存在するかテスト"""
    # ログイン
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    # チャットページにアクセス（リダイレクトに従う）
    response = client.get('/chat/messages', follow_redirects=True)
    
    # ハンバーガーメニューボタンが存在するか
    assert b'<button class="menu-toggle" id="menuToggle">' in response.data
    
    # オーバーレイが存在するか
    assert b'<div class="overlay" id="overlay"></div>' in response.data
    
    # モバイル用チャンネルヘッダーが存在するか
    assert b'<div class="channel-header">' in response.data

def test_mobile_css_classes(client):
    """モバイル用CSSクラスが存在するかテスト"""
    response = client.get('/')
    
    # メディアクエリの存在確認
    assert b'@media (max-width: 767px)' in response.data
    
    # モバイル用スタイルの確認
    assert b'.sidebar.open' in response.data
    assert b'.overlay.active' in response.data
    assert b'.message-form' in response.data

def test_mobile_message_form(client, test_user):
    """モバイル環境でのメッセージ入力フォームテスト"""
    # ログイン
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    response = client.get('/chat/messages', follow_redirects=True)
    
    # 入力フォームの位置固定スタイル
    assert b'position: fixed' in response.data
    assert b'bottom: 0' in response.data
    
    # メッセージエリアのパディング
    assert b'padding-bottom: 70px' in response.data 