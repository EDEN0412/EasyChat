import pytest
from flask import url_for
from app import create_app, db
from app.models import User, Channel, Message
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(user)
        db.session.commit()
        return user.id

@pytest.fixture
def test_channel(app, test_user):
    """テスト用のチャンネルを作成"""
    with app.app_context():
        channel = Channel(
            id='test-channel-id',
            name='テストチャンネル',
            created_by=test_user,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(channel)
        db.session.commit()
        return channel.id

@pytest.fixture
def test_messages(app, test_user, test_channel):
    """テスト用のメッセージを作成"""
    with app.app_context():
        messages = [
            Message(
                id='test-message-1',
                content='これはテスト用のメッセージです',
                user_id=test_user,
                channel_id=test_channel,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            Message(
                id='test-message-2',
                content='テストキーワードを含むメッセージです',
                user_id=test_user,
                channel_id=test_channel,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            Message(
                id='test-message-3',
                content='別のテスト内容のメッセージです',
                user_id=test_user,
                channel_id=test_channel,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        ]
        for message in messages:
            db.session.add(message)
        db.session.commit()
        return [m.id for m in messages]

@pytest.fixture
def test_channels(app, test_user):
    """複数のテスト用チャンネルを作成"""
    with app.app_context():
        channels = [
            Channel(
                id='channel-1',
                name='開発チャンネル',
                created_by=test_user,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            Channel(
                id='channel-2',
                name='マーケティング',
                created_by=test_user,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            Channel(
                id='channel-3',
                name='一般チャット',
                created_by=test_user,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        ]
        for channel in channels:
            db.session.add(channel)
        db.session.commit()
        return [c.id for c in channels]

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

def test_search_messages_api(auth_client, test_user, test_channel, test_messages, app, api_headers):
    """メッセージ検索のAPIテスト"""
    with app.app_context():
        # キーワード「テスト」で検索
        response = auth_client.get(
            f'/chat/search?keyword=テスト&channel_id={test_channel}', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 「テスト」を含むメッセージが全て返されることを確認
        assert len(data['messages']) == 3
        
        # キーワード「キーワード」で検索
        response = auth_client.get(
            f'/chat/search?keyword=キーワード&channel_id={test_channel}', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 「キーワード」を含むメッセージが1つだけ返されることを確認
        assert len(data['messages']) == 1
        assert 'キーワード' in data['messages'][0]['content']
        
        # 存在しないキーワードで検索
        response = auth_client.get(
            f'/chat/search?keyword=存在しない&channel_id={test_channel}', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 結果が空であることを確認
        assert len(data['messages']) == 0
        
        # キーワードがない場合
        response = auth_client.get(
            f'/chat/search?channel_id={test_channel}', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 結果が空であることを確認
        assert len(data['messages']) == 0

def test_search_channels_api(auth_client, test_user, test_channels, app, api_headers):
    """チャンネル検索のAPIテスト"""
    with app.app_context():
        # キーワード「チャンネル」で検索
        response = auth_client.get(
            '/chat/channels/search?keyword=チャンネル', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 「チャンネル」を含むチャンネルが1つ返されることを確認
        assert len(data['channels']) == 1
        assert data['channels'][0]['name'] == '開発チャンネル'
        
        # キーワード「マーケティング」で検索
        response = auth_client.get(
            '/chat/channels/search?keyword=マーケティング', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 「マーケティング」を含むチャンネルが1つだけ返されることを確認
        assert len(data['channels']) == 1
        assert data['channels'][0]['name'] == 'マーケティング'
        
        # 存在しないキーワードで検索
        response = auth_client.get(
            '/chat/channels/search?keyword=存在しない', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 結果が空であることを確認
        assert len(data['channels']) == 0
        
        # キーワードがない場合は全てのチャンネルが返される
        response = auth_client.get(
            '/chat/channels/search', 
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 全てのチャンネルが返されることを確認
        assert len(data['channels']) == 3 