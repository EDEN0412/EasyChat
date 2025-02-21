import pytest
from flask import url_for
from flask_socketio import SocketIOTestClient
from app import create_app, db, socketio
from app.models import User, Channel, Message, Reaction
from datetime import datetime, UTC
import uuid
import json

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
def test_channel(app, test_user):
    """テスト用のチャンネルを作成"""
    with app.app_context():
        channel = Channel(
            id='test-channel-id',
            name='testchannel',
            description='Test Channel',
            created_by=test_user['id'],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(channel)
        db.session.commit()
        return {'id': channel.id, 'name': channel.name}

@pytest.fixture
def socket_client(app, test_user):
    """SocketIOのテストクライアントを作成"""
    with app.test_client() as client:
        with client.session_transaction() as session:
            session['user_id'] = test_user['id']
            session['username'] = test_user['username']
        socket_client = SocketIOTestClient(app, socketio)
        yield socket_client
        socket_client.disconnect()

def test_realtime_message(socket_client, test_channel, test_user, app):
    """リアルタイムメッセージ更新のテスト"""
    with app.app_context():
        # メッセージを作成
        message = Message(
            id=str(uuid.uuid4()),
            content='Test realtime message',
            channel_id=test_channel['id'],
            user_id=test_user['id'],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()

        # 新規メッセージのイベントをエミット
        socketio.emit('new_message', {
            'id': message.id,
            'content': message.content,
            'user_id': message.user_id,
            'username': test_user['username'],
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_edited': False
        })

        # クライアントがメッセージを受信することを確認
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'new_message'
        assert received[0]['args'][0]['content'] == 'Test realtime message'

def test_realtime_reaction(socket_client, test_channel, test_user, app):
    """リアルタイムリアクション更新のテスト"""
    with app.app_context():
        # メッセージを作成
        message = Message(
            id=str(uuid.uuid4()),
            content='Test reaction message',
            channel_id=test_channel['id'],
            user_id=test_user['id'],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
        db.session.add(message)
        db.session.commit()

        # リアクションを追加
        reaction = Reaction(
            message_id=message.id,
            user_id=test_user['id'],
            emoji='👍'
        )
        db.session.add(reaction)
        db.session.commit()

        # リアクション更新のイベントをエミット
        socketio.emit('update_reactions', {
            'message_id': message.id,
            'reactions': [{'emoji': '👍', 'count': 1}]
        })

        # クライアントがリアクション更新を受信することを確認
        received = socket_client.get_received()
        assert len(received) > 0
        assert received[0]['name'] == 'update_reactions'
        assert received[0]['args'][0]['message_id'] == message.id
        assert received[0]['args'][0]['reactions'][0]['emoji'] == '👍'
        assert received[0]['args'][0]['reactions'][0]['count'] == 1 