import pytest
from flask import url_for
from app import create_app, db
from app.models import User, Channel, Message, Reaction
from datetime import datetime, UTC
import uuid
import io
from PIL import Image

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
        return user.id

@pytest.fixture
def test_channel(app, test_user):
    """テスト用のチャンネルを作成"""
    with app.app_context():
        channel = Channel(
            id='test-channel-id',
            name='testchannel',
            created_by=test_user,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(channel)
        db.session.commit()
        return channel.id

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

def test_send_message_api(auth_client, test_channel, app, api_headers):
    """メッセージ送信のAPIテスト"""
    with app.app_context():
        # テキストメッセージを送信
        response = auth_client.post('/chat/send', data={
            'message': 'テストメッセージ',
            'channel_id': test_channel
        }, headers=api_headers, follow_redirects=True)
        
        assert response.status_code == 200
        assert response.is_json
        
        # メッセージがデータベースに保存されたことを確認
        message = Message.query.filter_by(content='テストメッセージ').first()
        assert message is not None
        assert message.user_id == 'test-user-id'
        assert message.channel_id == test_channel

def test_upload_image_api(auth_client, test_channel, app, api_headers):
    """画像アップロードのAPIテスト"""
    with app.app_context():
        # 画像を作成
        img = Image.new('RGB', (100, 100), color='red')
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        
        # 画像付きメッセージを送信
        response = auth_client.post('/chat/send', 
                                   data={
                                       'channel_id': test_channel,
                                       'image': (img_io, 'test_image.jpg')
                                   },
                                   headers=api_headers,
                                   content_type='multipart/form-data',
                                   follow_redirects=True)
        
        assert response.status_code == 200
        assert response.is_json
        
        # 画像がアップロードされたことを確認
        message = Message.query.filter_by(content='').first()
        assert message is not None
        assert message.image_url is not None
        assert 'test_image.jpg' in message.image_url
        
        # テキストと画像の両方を含むメッセージを送信
        img2 = Image.new('RGB', (100, 100), color='blue')
        img_io2 = io.BytesIO()
        img2.save(img_io2, 'JPEG')
        img_io2.seek(0)
        
        response = auth_client.post('/chat/send', 
                                   data={
                                       'message': 'テキストと画像',
                                       'channel_id': test_channel,
                                       'image': (img_io2, 'test_image2.jpg')
                                   },
                                   headers=api_headers,
                                   content_type='multipart/form-data',
                                   follow_redirects=True)
        
        assert response.status_code == 200
        assert response.is_json
        
        # メッセージがデータベースに保存されたことを確認
        message = Message.query.filter_by(content='テキストと画像').first()
        assert message is not None
        assert message.image_url is not None
        assert message.user_id == 'test-user-id'
        assert message.channel_id == test_channel

def test_edit_message_api(auth_client, test_user, test_channel, app, api_headers):
    """メッセージ編集のAPIテスト"""
    with app.app_context():
        # テスト用のメッセージを作成
        message = Message(
            id='test-message-id',
            content='元のメッセージ',
            user_id=test_user,
            channel_id=test_channel,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # メッセージを編集
        response = auth_client.post(f'/chat/messages/{message.id}/edit', data={
            'content': '編集後のメッセージ'
        }, headers=api_headers, follow_redirects=True)
        
        assert response.status_code == 200
        assert response.is_json
        
        # メッセージが編集されたことを確認
        edited_message = Message.query.get(message.id)
        assert edited_message.content == '編集後のメッセージ'
        assert edited_message.is_edited == True

def test_edit_message_unauthorized_api(auth_client, app, api_headers):
    """他ユーザーのメッセージ編集時の認証チェックのAPIテスト"""
    with app.app_context():
        # 別のユーザーを作成
        other_user = User(
            id='other-user-id',
            username='other_user',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_user)
        
        # チャンネルを作成
        channel = Channel(
            id='test-channel-id',
            name='テストチャンネル',
            created_by=other_user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(channel)
        
        # 他のユーザーのメッセージを作成
        message = Message(
            id='other-message-id',
            content='他のユーザーのメッセージ',
            user_id=other_user.id,
            channel_id=channel.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # 他のユーザーのメッセージを編集しようとする
        response = auth_client.post(f'/chat/messages/{message.id}/edit', data={
            'content': '編集しようとする'
        }, headers=api_headers, follow_redirects=True)
        
        assert response.status_code == 403
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert '自分のメッセージのみ編集できます' in json_data['error']
        
        # メッセージが編集されていないことを確認
        not_edited_message = Message.query.get(message.id)
        assert not_edited_message.content == '他のユーザーのメッセージ'
        assert not_edited_message.is_edited == False

def test_delete_message_api(auth_client, test_user, test_channel, app, api_headers):
    """メッセージ削除のAPIテスト"""
    with app.app_context():
        # テスト用のメッセージを作成
        message = Message(
            id='test-message-id',
            content='削除するメッセージ',
            user_id=test_user,
            channel_id=test_channel,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # メッセージを削除
        response = auth_client.post(f'/chat/messages/{message.id}/delete', 
                                    headers=api_headers, 
                                    follow_redirects=True)
        
        assert response.status_code == 200
        assert response.is_json
        
        # メッセージが削除されたことを確認
        deleted_message = Message.query.get(message.id)
        assert deleted_message is None

def test_delete_message_unauthorized_api(auth_client, app, api_headers):
    """他ユーザーのメッセージ削除時の認証チェックのAPIテスト"""
    with app.app_context():
        # 別のユーザーを作成
        other_user = User(
            id='other-user-id',
            username='other_user',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_user)
        db.session.commit()
        
        # チャンネルを作成
        channel = Channel(
            id='test-channel-id',
            name='テストチャンネル',
            created_by=other_user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(channel)
        db.session.commit()
        
        # 他のユーザーのメッセージを作成
        message = Message(
            id='other-message-id',
            content='他のユーザーのメッセージ',
            user_id=other_user.id,
            channel_id=channel.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # 他のユーザーのメッセージを削除しようとする
        response = auth_client.post(f'/chat/messages/{message.id}/delete', 
                                    headers=api_headers, 
                                    follow_redirects=True)
        
        assert response.status_code == 403
        assert response.is_json
        json_data = response.get_json()
        assert 'error' in json_data
        assert '自分のメッセージのみ削除できます' in json_data['error']
        
        # メッセージが削除されていないことを確認
        not_deleted_message = Message.query.get(message.id)
        assert not_deleted_message is not None
        assert not_deleted_message.content == '他のユーザーのメッセージ'

def test_message_reactions_api(auth_client, test_channel, test_user, app, api_headers):
    """メッセージリアクション機能のAPIテスト"""
    with app.app_context():
        # テスト用のメッセージを作成
        message = Message(
            id='test-message-id',
            content='リアクションテスト用メッセージ',
            user_id=test_user,
            channel_id=test_channel,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # リアクションを追加
        response = auth_client.post(f'/chat/messages/{message.id}/reaction', data={
            'emoji': '👍'
        }, headers=api_headers)
        
        assert response.status_code == 200
        assert response.is_json
        
        # リアクションが追加されたことを確認
        reaction = Reaction.query.filter_by(message_id=message.id, emoji='👍').first()
        assert reaction is not None
        assert reaction.user_id == test_user
        
        # 同じリアクションを削除
        response = auth_client.post(f'/chat/messages/{message.id}/reaction', data={
            'emoji': '👍'
        }, headers=api_headers)
        
        assert response.status_code == 200
        assert response.is_json
        
        # リアクションが削除されたことを確認
        deleted_reaction = Reaction.query.filter_by(message_id=message.id, emoji='👍').first()
        assert deleted_reaction is None
        
        # 別のリアクションを追加
        response = auth_client.post(f'/chat/messages/{message.id}/reaction', data={
            'emoji': '❤️'
        }, headers=api_headers)
        
        assert response.status_code == 200
        assert response.is_json
        
        # 新しいリアクションが追加されたことを確認
        new_reaction = Reaction.query.filter_by(message_id=message.id, emoji='❤️').first()
        assert new_reaction is not None
        assert new_reaction.user_id == test_user

def test_message_mentions_api(auth_client, test_channel, test_user, app, api_headers):
    """メンション機能のAPIテスト"""
    with app.app_context():
        # テスト用の別ユーザーを作成
        mentioned_user = User(
            id='mentioned-user-id',
            username='mentioneduser',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(mentioned_user)
        db.session.commit()
        
        # メンション付きメッセージを送信
        response = auth_client.post('/chat/send', data={
            'message': 'Hello @mentioneduser!',
            'channel_id': test_channel
        }, headers=api_headers, follow_redirects=True)
        
        assert response.status_code == 200
        assert response.is_json
        
        # メッセージがデータベースに保存されたことを確認
        message = Message.query.filter_by(content='Hello @mentioneduser!').first()
        assert message is not None
        assert message.user_id == test_user
        assert message.channel_id == test_channel 