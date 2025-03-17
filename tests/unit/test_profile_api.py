import pytest
from flask import url_for
from app import create_app, db
from app.models import User
from datetime import datetime, UTC
import json

@pytest.fixture
def app():
    """テスト用のアプリケーションインスタンスを作成"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        yield app
        db.session.rollback()

@pytest.fixture
def test_user(app):
    """テスト用のユーザーを作成"""
    with app.app_context():
        user = User(
            id='test-user-id',
            username='testuser',
            password_hash='dummy_hash',
            status_message='初期ステータスメッセージ',
            avatar_bg_color='#FF5733',
            avatar_text_color='#FFFFFF',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(user)
        db.session.commit()
        return user.id

@pytest.fixture
def another_user(app):
    """別のテスト用ユーザーを作成"""
    with app.app_context():
        user = User(
            id='another-user-id',
            username='anotheruser',
            password_hash='dummy_hash',
            status_message='別のユーザーのステータス',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(user)
        db.session.commit()
        return user.id

@pytest.fixture
def auth_client(client, test_user, app):
    """認証済みのテストクライアント"""
    with app.app_context():
        user = db.session.get(User, test_user)
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['username'] = user.username
            # フラスコログインシミュレーション
            session['_user_id'] = user.id
    return client

@pytest.fixture
def api_headers():
    """APIリクエスト用のヘッダー"""
    return {'X-Requested-With': 'XMLHttpRequest'}

def test_get_profile_api(auth_client, test_user, app, api_headers):
    """プロフィール取得のAPIテスト"""
    with app.app_context():
        # 自分のプロフィールを取得
        response = auth_client.get(
            '/profile/api/testuser', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # プロフィール情報が正しく返されることを確認
        assert data['username'] == 'testuser'
        assert data['status_message'] == '初期ステータスメッセージ'
        assert data['avatar_bg_color'] == '#FF5733'
        assert data['avatar_text_color'] == '#FFFFFF'
        
        # 存在しないユーザーのプロフィールを取得
        response = auth_client.get(
            '/profile/api/nonexistent', 
            headers=api_headers
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'ユーザーが見つかりません'

def test_update_status_message_api(auth_client, test_user, app, api_headers):
    """ステータスメッセージ更新のAPIテスト"""
    with app.app_context():
        # ステータスメッセージを更新
        response = auth_client.post(
            '/profile/api/update_status', 
            headers=api_headers,
            json={'status_message': '新しいステータスメッセージ'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['status_message'] == '新しいステータスメッセージ'
        
        # データベースに反映されていることを確認
        user = db.session.get(User, test_user)
        assert user.status_message == '新しいステータスメッセージ'
        
        # 空のステータスメッセージを更新
        response = auth_client.post(
            '/profile/api/update_status', 
            headers=api_headers,
            json={'status_message': ''}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['status_message'] == ''
        
        # データベースに反映されていることを確認
        user = db.session.get(User, test_user)
        assert user.status_message == ''

def test_update_avatar_colors_api(auth_client, test_user, app, api_headers):
    """アバターカラー更新のAPIテスト"""
    with app.app_context():
        # アバターの色を更新
        response = auth_client.post(
            '/profile/api/update_avatar_colors', 
            headers=api_headers,
            json={
                'avatar_bg_color': '#00FF00',
                'avatar_text_color': '#000000'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['avatar_bg_color'] == '#00FF00'
        assert data['avatar_text_color'] == '#000000'
        
        # データベースに反映されていることを確認
        user = db.session.get(User, test_user)
        assert user.avatar_bg_color == '#00FF00'
        assert user.avatar_text_color == '#000000'
        
        # バリデーションエラーの場合（不正な色形式）
        response = auth_client.post(
            '/profile/api/update_avatar_colors', 
            headers=api_headers,
            json={
                'avatar_bg_color': 'invalid-color',
                'avatar_text_color': '#000000'
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'error' in data 