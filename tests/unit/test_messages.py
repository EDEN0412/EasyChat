import pytest
from flask import url_for
from app import create_app, db
from app.models import User, Channel, Message, Reaction
from app.auth import create_user
from datetime import datetime, UTC
import uuid

@pytest.fixture
def app():
    """テスト用のアプリケーションインスタンスを作成"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
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
        user = User(
            id='test-user-id',
            username='testuser',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(user)
        db.session.commit()
        return user.id  # IDのみを返す

@pytest.fixture
def test_channel(app, test_user):
    """テスト用のチャンネルを作成"""
    with app.app_context():
        channel = Channel(
            id='test-channel-id',
            name='testchannel',
            created_by=test_user,  # test_userはIDのみ
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(channel)
        db.session.commit()
        return channel.id  # IDのみを返す

@pytest.fixture
def auth_client(client, test_user, app):
    """認証済みのテストクライアント"""
    with app.app_context():
        user = db.session.get(User, test_user)  # test_userはID
        with client.session_transaction() as session:
            session['user_id'] = user.id
            session['username'] = user.username
    return client

def test_send_message(auth_client, test_channel, app):
    """メッセージ送信のテスト"""
    with app.app_context():
        # 正常系：有効なメッセージを送信
        response = auth_client.post('/chat/send', data={
            'message': 'Hello, World!',
            'channel_id': test_channel
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # メッセージがデータベースに保存されたことを確認
        message = Message.query.filter_by(content='Hello, World!').first()
        assert message is not None
        assert message.content == 'Hello, World!'
        
        # 異常系：空のメッセージ
        response = auth_client.post('/chat/send', data={
            'message': '',
            'channel_id': test_channel
        }, follow_redirects=True)
        assert b'message' in response.data.lower()

def test_edit_message(auth_client, test_user, test_channel, app):
    """メッセージ編集のテスト"""
    with app.app_context():
        # テスト用メッセージを作成
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
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert 'メッセージを編集しました' in response.get_data(as_text=True)
        
        # メッセージが更新されたか確認
        updated_message = Message.query.get(message.id)
        assert updated_message.content == '編集後のメッセージ'
        assert updated_message.is_edited == True

def test_edit_message_unauthorized(auth_client, app):
    """他のユーザーのメッセージを編集しようとしたときのテスト"""
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
        
        # 他のユーザーのメッセージを編集しようとする
        response = auth_client.post(f'/chat/messages/{message.id}/edit', data={
            'content': '編集しようとしたメッセージ'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '自分のメッセージのみ編集できます' in response.get_data(as_text=True)
        
        # メッセージが編集されていないことを確認
        unchanged_message = Message.query.get(message.id)
        assert unchanged_message.content == '他のユーザーのメッセージ'

def test_delete_message(auth_client, test_user, test_channel, app):
    """メッセージ削除のテスト"""
    with app.app_context():
        # テスト用メッセージを作成
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
        response = auth_client.post(f'/chat/messages/{message.id}/delete', follow_redirects=True)
        
        assert response.status_code == 200
        assert 'メッセージを削除しました' in response.get_data(as_text=True)
        
        # メッセージが削除されたか確認
        deleted_message = Message.query.get(message.id)
        assert deleted_message is None

def test_delete_message_unauthorized(auth_client, app):
    """他のユーザーのメッセージを削除しようとしたときのテスト"""
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
        response = auth_client.post(f'/chat/messages/{message.id}/delete', follow_redirects=True)
        
        assert response.status_code == 200
        assert '自分のメッセージのみ削除できます' in response.get_data(as_text=True)
        
        # メッセージが削除されていないことを確認
        unchanged_message = Message.query.get(message.id)
        assert unchanged_message is not None
        assert unchanged_message.content == '他のユーザーのメッセージ'

def test_message_reactions(auth_client, test_channel, test_user, app):
    """メッセージリアクションのテスト"""
    with app.app_context():
        # メッセージを作成
        message = Message(
            id=str(uuid.uuid4()),
            channel_id=test_channel,
            user_id=test_user,
            content='Message for reactions',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # 正常系：リアクションを追加
        response = auth_client.post(f'/chat/messages/{message.id}/react', 
                               json={'emoji': '👍'},
                               content_type='application/json')
        assert response.status_code == 200
        
        # リアクションが追加されたことを確認
        reaction = Reaction.query.filter_by(
            message_id=message.id,
            user_id=test_user,
            emoji='👍'
        ).first()
        assert reaction is not None
        
        # メッセージを削除
        message_id = message.id
        response = auth_client.delete(f'/chat/messages/{message_id}')
        assert response.status_code == 200
        
        # メッセージとリアクションが削除されたことを確認
        deleted_message = Message.query.get(message_id)
        assert deleted_message is None
        
        deleted_reaction = Reaction.query.filter_by(
            message_id=message_id,
            user_id=test_user,
            emoji='👍'
        ).first()
        assert deleted_reaction is None
        
        # 削除されたメッセージへのリアクション追加は404エラーになることを確認
        response = auth_client.post(f'/chat/messages/{message_id}/react',
                               json={'emoji': '👍'},
                               content_type='application/json')
        assert response.status_code == 404

def test_message_mentions(auth_client, test_channel, test_user, app):
    """メンション機能のテスト"""
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
        }, follow_redirects=True)
        assert response.status_code == 200

        # メッセージが保存されたことを確認
        message = Message.query.filter_by(content='Hello @mentioneduser!').first()
        assert message is not None

        # メッセージ表示時にメンションがリンクに変換されることを確認
        response = auth_client.get(f'/chat/messages/{test_channel}')
        assert response.status_code == 200
        assert '@mentioneduser' in response.get_data(as_text=True)

        # 存在しないユーザーへのメンション
        response = auth_client.post('/chat/send', data={
            'message': 'Hello @nonexistentuser!',
            'channel_id': test_channel
        }, follow_redirects=True)
        assert response.status_code == 200

        # 複数のメンションを含むメッセージ
        response = auth_client.post('/chat/send', data={
            'message': 'Hello @mentioneduser and @testuser!',
            'channel_id': test_channel
        }, follow_redirects=True)
        assert response.status_code == 200
        message = Message.query.filter_by(content='Hello @mentioneduser and @testuser!').first()
        assert message is not None 