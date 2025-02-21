import pytest
from flask import url_for
from app import create_app, db
from app.models import User, Channel
from datetime import datetime, UTC

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
    return client

def test_create_channel(auth_client, test_user, app):
    """チャンネル作成のテスト"""
    with app.app_context():
        # 正常系：有効な名前でチャンネルを作成
        response = auth_client.post('/chat/channels/create', data={
            'name': 'test-channel'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # チャンネルが作成されたことを確認
        channel = Channel.query.filter_by(name='test-channel').first()
        assert channel is not None
        assert channel.name == 'test-channel'
        assert channel.created_by == test_user
        
        # 異常系：同じ名前のチャンネルを作成
        response = auth_client.post('/chat/channels/create', data={
            'name': 'test-channel'
        }, follow_redirects=True)
        assert 'チャンネル名は必須です' not in response.get_data(as_text=True)
        assert '同じ名前のチャンネルが既に存在します' in response.get_data(as_text=True)
        
        # 異常系：空の名前でチャンネル作成
        response = auth_client.post('/chat/channels/create', data={
            'name': ''
        }, follow_redirects=True)
        assert 'チャンネル名は必須です' in response.get_data(as_text=True)

def test_channel_listing(auth_client, test_user, app):
    """チャンネル一覧表示のテスト"""
    with app.app_context():
        # テスト用のチャンネルを作成
        channels = [
            Channel(
                id=f'test-channel-{i}',
                name=f'channel-{i}',
                created_by=test_user,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ) for i in range(3)
        ]
        for channel in channels:
            db.session.add(channel)
        db.session.commit()
        
        # デフォルトチャンネルを作成
        default_channel = Channel(
            id='default-channel',
            name='general',
            created_by=test_user,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(default_channel)
        db.session.commit()
        
        # チャンネル一覧を取得（デフォルトチャンネルにリダイレクトされる）
        response = auth_client.get('/chat/messages', follow_redirects=True)
        assert response.status_code == 200
        
        # 全てのチャンネルが表示されていることを確認
        response_text = response.get_data(as_text=True)
        for channel in channels:
            assert channel.name in response_text 