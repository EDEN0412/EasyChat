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

@pytest.fixture
def api_headers():
    """APIリクエスト用のヘッダー"""
    return {'X-Requested-With': 'XMLHttpRequest'}

def test_create_channel_api(auth_client, test_user, app, api_headers):
    """チャンネル作成のAPIテスト"""
    with app.app_context():
        # 正常系：有効な名前でチャンネルを作成
        response = auth_client.post('/chat/channels/create', data={
            'name': 'test-channel'
        }, headers=api_headers, follow_redirects=True)
        assert response.status_code == 200
        assert response.is_json
        
        # チャンネルが作成されたことを確認
        channel = Channel.query.filter_by(name='test-channel').first()
        assert channel is not None
        assert channel.name == 'test-channel'
        assert channel.created_by == test_user
        
        # 異常系：同じ名前のチャンネルを作成
        response = auth_client.post('/chat/channels/create', data={
            'name': 'test-channel'
        }, headers=api_headers, follow_redirects=True)
        assert response.status_code == 400
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert '同じ名前のチャンネルが既に存在します' in json_data['error']
        
        # 異常系：空の名前でチャンネル作成
        response = auth_client.post('/chat/channels/create', data={
            'name': ''
        }, headers=api_headers, follow_redirects=True)
        assert response.status_code == 400
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'チャンネル名は必須です' in json_data['error']

def test_channel_listing_api(auth_client, test_user, app, api_headers):
    """チャンネル一覧表示のAPIテスト"""
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
        
        # チャンネル一覧を取得
        response = auth_client.get('/chat/messages', headers=api_headers)
        assert response.status_code == 200
        assert response.is_json
        
        json_data = response.get_json()
        assert 'channels' in json_data
        channel_names = [ch['name'] for ch in json_data['channels']]
        
        # 全てのチャンネルが含まれていることを確認
        for channel in channels:
            assert channel.name in channel_names
        assert 'general' in channel_names

def test_delete_channel_api(auth_client, test_user, app, api_headers):
    """チャンネル削除機能のAPIテスト"""
    with app.app_context():
        # テスト用のチャンネルを作成（自分が作成者）
        own_channel = Channel(
            id='own-channel-id',
            name='my-channel',
            created_by=test_user,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(own_channel)
        
        # 他のユーザーが作成したチャンネル
        another_user = User(
            id='another-user-id',
            username='another',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(another_user)
        db.session.commit()
        
        other_channel = Channel(
            id='other-channel-id',
            name='other-channel',
            created_by=another_user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_channel)
        
        # デフォルトチャンネルを作成
        default_channel = Channel(
            id='default-channel-id',
            name='general',
            created_by=test_user,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(default_channel)
        db.session.commit()
        
        # 正常系：自分が作成したチャンネルを削除
        response = auth_client.post(f'/chat/channels/{own_channel.id}/delete', 
                                    headers=api_headers, 
                                    follow_redirects=True)
        assert response.status_code == 200
        assert response.is_json
        
        # チャンネルが実際に削除されたか確認
        deleted_channel = Channel.query.filter_by(id=own_channel.id).first()
        assert deleted_channel is None
        
        # 異常系：他のユーザーが作成したチャンネルを削除しようとする
        response = auth_client.post(f'/chat/channels/{other_channel.id}/delete', 
                                    headers=api_headers, 
                                    follow_redirects=True)
        assert response.status_code == 403
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert '自分が作成したチャンネルのみ削除できます' in json_data['error']
        
        # チャンネルが削除されていないことを確認
        not_deleted_channel = Channel.query.filter_by(id=other_channel.id).first()
        assert not_deleted_channel is not None
        
        # 異常系：デフォルトチャンネルを削除しようとする
        response = auth_client.post(f'/chat/channels/{default_channel.id}/delete', 
                                    headers=api_headers, 
                                    follow_redirects=True)
        assert response.status_code == 400
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert 'デフォルトチャンネルは削除できません' in json_data['error']
        
        # デフォルトチャンネルが削除されていないことを確認
        default_not_deleted = Channel.query.filter_by(id=default_channel.id).first()
        assert default_not_deleted is not None

def test_edit_channel_api(auth_client, test_user, app, api_headers):
    """チャンネル名編集機能のAPIテスト"""
    with app.app_context():
        # テスト用のチャンネルを作成（自分が作成者）
        own_channel = Channel(
            id='own-channel-id',
            name='my-channel',
            created_by=test_user,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(own_channel)
        
        # 他のユーザーが作成したチャンネル
        another_user = User(
            id='another-user-id',
            username='another',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(another_user)
        db.session.commit()
        
        other_channel = Channel(
            id='other-channel-id',
            name='other-channel',
            created_by=another_user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_channel)
        
        # 既存のチャンネル（名前重複チェック用）
        existing_channel = Channel(
            id='existing-channel-id',
            name='existing-channel',
            created_by=test_user,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(existing_channel)
        db.session.commit()
        
        # 正常系：自分のチャンネル名を編集
        response = auth_client.post(f'/chat/channels/{own_channel.id}/edit', 
                                    data={'name': 'edited-channel'}, 
                                    headers=api_headers, 
                                    follow_redirects=True)
        assert response.status_code == 200
        assert response.is_json
        
        # チャンネル名が変更されたことを確認
        edited_channel = Channel.query.filter_by(id=own_channel.id).first()
        assert edited_channel is not None
        assert edited_channel.name == 'edited-channel'
        
        # 異常系：他のユーザーのチャンネル名を編集しようとする
        response = auth_client.post(f'/chat/channels/{other_channel.id}/edit', 
                                    data={'name': 'try-edit-other'}, 
                                    headers=api_headers, 
                                    follow_redirects=True)
        assert response.status_code == 403
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert '自分が作成したチャンネルのみ編集できます' in json_data['error']
        
        # チャンネル名が変更されていないことを確認
        not_edited_channel = Channel.query.filter_by(id=other_channel.id).first()
        assert not_edited_channel.name == 'other-channel'
        
        # 異常系：既存の名前に変更しようとする
        response = auth_client.post(f'/chat/channels/{own_channel.id}/edit', 
                                    data={'name': 'existing-channel'}, 
                                    headers=api_headers, 
                                    follow_redirects=True)
        assert response.status_code == 400
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert '同じ名前のチャンネルが既に存在します' in json_data['error'] 