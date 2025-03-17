import pytest
from flask import url_for
from app import create_app, db
from app.models import User, Channel
from datetime import datetime, UTC
import uuid

@pytest.fixture
def app():
    """テスト用のアプリケーションインスタンスを作成"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()

@pytest.fixture
def client(app):
    """テスト用のクライアントを作成"""
    return app.test_client()

@pytest.fixture
def test_user(app):
    """テスト用のユーザーを作成"""
    with app.app_context():
        user = User(
            id='test-user-id',
            username='testuser',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(user)
        db.session.commit()
        return {'id': user.id, 'username': user.username}

@pytest.fixture
def auth_client(client, test_user):
    """認証済みのテストクライアント"""
    with client.session_transaction() as session:
        session['user_id'] = test_user['id']
        session['username'] = test_user['username']
    return client

@pytest.fixture
def api_headers():
    """APIリクエスト用のヘッダー"""
    return {'X-Requested-With': 'XMLHttpRequest'}

def test_404_error_api(client, api_headers):
    """404エラーページのAPIテスト"""
    # 存在しないページへのアクセス
    response = client.get('/nonexistent-page', headers=api_headers)
    assert response.status_code == 404
    assert response.is_json
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'ページが見つかりません' in json_data['error']

def test_403_error_api(client, api_headers):
    """403エラーページのAPIテスト"""
    # 未ログイン状態で保護されたページにアクセス
    response = client.get('/chat/messages', headers=api_headers)
    assert response.status_code == 403
    assert response.is_json
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'アクセス権限がありません' in json_data['error']

def test_validation_errors_api(client, api_headers):
    """バリデーションエラーのAPIテスト"""
    # ユーザー登録時の入力検証
    response = client.post('/register', data={
        'username': '',  # 空のユーザー名
        'password': 'password123',
        'password_confirm': 'password123'
    }, headers=api_headers)
    assert response.status_code == 400
    assert response.is_json
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'ユーザー名とパスワードは必須です' in json_data['error']

    # パスワード不一致
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'password123',
        'password_confirm': 'different_password'
    }, headers=api_headers)
    assert response.status_code == 400
    assert response.is_json
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'パスワードが一致しません' in json_data['error']

    # ログイン時の入力検証
    response = client.post('/login', data={
        'username': '',  # 空のユーザー名
        'password': ''   # 空のパスワード
    }, headers=api_headers)
    assert response.status_code == 400
    assert response.is_json
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'ユーザー名とパスワードは必須です' in json_data['error']

def test_channel_validation_errors_api(auth_client, api_headers):
    """チャンネル作成時のバリデーションエラーのAPIテスト"""
    # 空のチャンネル名でチャンネル作成
    response = auth_client.post('/chat/channels/create', data={
        'name': ''
    }, headers=api_headers, follow_redirects=True)
    assert response.status_code == 400
    assert response.is_json
    json_data = response.get_json()
    assert 'error' in json_data
    assert 'チャンネル名は必須です' in json_data['error']

def test_message_validation_errors_api(auth_client, test_user, app, api_headers):
    """メッセージ送信時のバリデーションエラーのAPIテスト"""
    with app.app_context():
        # テスト用のチャンネルを作成
        channel = Channel(
            id='test-channel-id',
            name='testchannel',
            created_by=test_user['id'],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(channel)
        db.session.commit()

        # 空のメッセージと画像なしで送信
        response = auth_client.post('/chat/send', data={
            'message': '',
            'channel_id': 'test-channel-id'
        }, headers=api_headers, follow_redirects=True)
        assert response.status_code == 400
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'メッセージまたは画像を入力してください' in json_data['error'] 