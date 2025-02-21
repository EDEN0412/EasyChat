import pytest
from flask import url_for
from app import create_app, db
from app.models import User, Channel, Message, Reaction
from app.auth import create_user
from datetime import datetime, UTC

@pytest.fixture
def app():
    """テスト用のアプリケーションインスタンスを作成"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
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
            description='Test Channel',
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
        user = User.query.get(test_user)  # test_userはID
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

def test_edit_message(auth_client, test_channel, test_user, app):
    """メッセージ編集のテスト"""
    with app.app_context():
        # メッセージを作成
        message = Message(
            channel_id=test_channel,
            user_id=test_user,
            content='Original message',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # 正常系：メッセージを編集
        response = auth_client.post(f'/chat/messages/{message.id}/edit', data={
            'content': 'Edited message'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # 編集されたメッセージを確認
        edited_message = Message.query.get(message.id)
        assert edited_message.content == 'Edited message'
        assert edited_message.is_edited is True
        
        # 異常系：他のユーザーのメッセージを編集
        other_user = User(
            id='other-user-id',
            username='otheruser',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_user)
        other_message = Message(
            channel_id=test_channel,
            user_id=other_user.id,
            content='Other user message',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_message)
        db.session.commit()
        
        response = auth_client.post(f'/chat/messages/{other_message.id}/edit', data={
            'content': 'Try to edit'
        }, follow_redirects=True)
        assert b'edit' in response.data.lower()

def test_delete_message(auth_client, test_channel, test_user, app):
    """メッセージ削除のテスト"""
    with app.app_context():
        # メッセージを作成
        message = Message(
            channel_id=test_channel,
            user_id=test_user,
            content='Message to delete',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()
        
        # 正常系：メッセージを削除
        response = auth_client.post(f'/chat/messages/{message.id}/delete', follow_redirects=True)
        assert response.status_code == 200
        
        # メッセージが削除されたことを確認
        deleted_message = Message.query.get(message.id)
        assert deleted_message is None
        
        # 異常系：他のユーザーのメッセージを削除
        other_user = User(
            id='other-user-id',
            username='otheruser',
            password_hash='dummy_hash',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_user)
        other_message = Message(
            channel_id=test_channel,
            user_id=other_user.id,
            content='Other user message',
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(other_message)
        db.session.commit()
        
        response = auth_client.post(f'/chat/messages/{other_message.id}/delete', follow_redirects=True)
        assert b'delete' in response.data.lower()

def test_message_reactions(auth_client, test_channel, test_user, app):
    """メッセージリアクションのテスト"""
    with app.app_context():
        # メッセージを作成
        message = Message(
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
        
        # 同じリアクションを再度追加（削除されることを確認）
        response = auth_client.post(f'/chat/messages/{message.id}/react',
                               json={'emoji': '👍'},
                               content_type='application/json')
        assert response.status_code == 200
        
        # リアクションが削除されたことを確認
        reaction = Reaction.query.filter_by(
            message_id=message.id,
            user_id=test_user,
            emoji='👍'
        ).first()
        assert reaction is None
        
        # 異常系：無効な絵文字
        response = auth_client.post(f'/chat/messages/{message.id}/react',
                               json={'emoji': ''},
                               content_type='application/json')
        assert response.status_code == 400 