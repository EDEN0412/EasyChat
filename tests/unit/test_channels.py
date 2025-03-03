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

def test_channel_creation_flash_messages(auth_client, test_user, app):
    """チャンネル作成時のフラッシュメッセージをテスト"""
    with app.app_context():
        # 正常系：チャンネル作成成功
        response = auth_client.post('/chat/channels/create', data={
            'name': 'new-channel'
        }, follow_redirects=True)
        assert 'チャンネルを作成しました' in response.get_data(as_text=True)
        
        # 異常系：同名チャンネル作成
        response = auth_client.post('/chat/channels/create', data={
            'name': 'new-channel'
        }, follow_redirects=True)
        assert '同じ名前のチャンネルが既に存在します' in response.get_data(as_text=True)
        
        # 異常系：空名チャンネル作成
        response = auth_client.post('/chat/channels/create', data={
            'name': ''
        }, follow_redirects=True)
        assert 'チャンネル名は必須です' in response.get_data(as_text=True) 

def test_delete_channel(auth_client, test_user, app):
    """チャンネル削除機能のテスト"""
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
        
        # デフォルトチャンネルを作成（チャンネル削除後のリダイレクト先）
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
        response = auth_client.post(f'/chat/channels/{own_channel.id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert 'チャンネルを削除しました' in response.get_data(as_text=True)
        
        # チャンネルが実際に削除されたか確認
        deleted_channel = Channel.query.filter_by(id=own_channel.id).first()
        assert deleted_channel is None
        
        # 異常系：他のユーザーが作成したチャンネルを削除しようとする
        response = auth_client.post(f'/chat/channels/{other_channel.id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert '自分が作成したチャンネルのみ削除できます' in response.get_data(as_text=True)
        
        # チャンネルが削除されていないことを確認
        not_deleted_channel = Channel.query.filter_by(id=other_channel.id).first()
        assert not_deleted_channel is not None
        
        # 異常系：デフォルトチャンネルを削除しようとする
        response = auth_client.post(f'/chat/channels/{default_channel.id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert 'デフォルトチャンネルは削除できません' in response.get_data(as_text=True)
        
        # デフォルトチャンネルが削除されていないことを確認
        default_not_deleted = Channel.query.filter_by(id=default_channel.id).first()
        assert default_not_deleted is not None 