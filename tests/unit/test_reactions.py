import pytest
from flask import url_for, session
from app import create_app, db
from app.models import User, Message, Channel, Reaction
from app.auth import create_user
from datetime import datetime, UTC
import uuid
import json

@pytest.fixture
def app():
    """テスト用のアプリケーションインスタンスを作成"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # テスト用にCSRF保護を無効化
    
    with app.app_context():
        db.create_all()
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
        # 既存のユーザーを確認
        user = User.query.filter_by(id='test-user-id').first()
        if not user:
            # ユーザーが存在しない場合は作成
            user = User(
                id='test-user-id',
                username='testuser',
                password_hash='dummy_hash',
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            db.session.add(user)
            db.session.commit()
        return user.id  # IDを返す

@pytest.fixture
def test_channel(app, test_user):
    """テスト用のチャンネルを作成"""
    with app.app_context():
        # 既存のチャンネルを確認
        channel = Channel.query.filter_by(id='test-channel-id').first()
        if not channel:
            # チャンネルが存在しない場合は作成
            channel = Channel(
                id='test-channel-id',
                name='testchannel',
                created_by=test_user,  # test_userはID
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            db.session.add(channel)
            db.session.commit()
        return channel.id  # IDを返す

@pytest.fixture
def test_message(app, test_user, test_channel):
    """テスト用のメッセージを作成"""
    with app.app_context():
        # 既存のメッセージを確認
        message = Message.query.filter_by(id='test-message-id').first()
        if not message:
            # メッセージが存在しない場合は作成
            message = Message(
                id='test-message-id',
                content='Message for reactions',
                user_id=test_user,  # test_userはID
                channel_id=test_channel,  # test_channelはID
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            db.session.add(message)
            db.session.commit()
        return message.id  # IDを返す

def test_toggle_reaction(auth_client, test_message, app):
    """リアクション機能のトグル動作をテスト"""
    with app.app_context():
        message_id = test_message  # IDが渡されている
        user_id = 'test-user-id'
        
        # 絵文字リアクションを追加
        response = auth_client.post(f'/chat/messages/{message_id}/reaction', 
                                  data={'emoji': '👍'},
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        assert response.status_code == 200
        
        # リアクションが追加されたことを確認
        reaction = Reaction.query.filter_by(
            message_id=message_id,
            user_id=user_id,
            emoji='👍'
        ).first()
        assert reaction is not None
        
        # 同じ絵文字リアクションをトグルで削除
        response = auth_client.post(f'/chat/messages/{message_id}/reaction', 
                                  data={'emoji': '👍'},
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        assert response.status_code == 200
        
        # リアクションが削除されたことを確認
        reaction = Reaction.query.filter_by(
            message_id=message_id,
            user_id=user_id,
            emoji='👍'
        ).first()
        assert reaction is None

def test_replace_reaction(auth_client, test_message, app):
    """ユーザーが同じメッセージに別の絵文字リアクションを付けるとき、前のリアクションが削除されることをテスト"""
    with app.app_context():
        message_id = test_message  # IDが渡されている
        user_id = 'test-user-id'
        
        # 最初の絵文字リアクションを追加 (👍)
        response = auth_client.post(f'/chat/messages/{message_id}/reaction', 
                                  data={'emoji': '👍'},
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        assert response.status_code == 200
        
        # 別の絵文字リアクションを追加 (❤️)
        response = auth_client.post(f'/chat/messages/{message_id}/reaction', 
                                  data={'emoji': '❤️'},
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
        assert response.status_code == 200
        
        # 最初のリアクションが削除され、新しいリアクションだけが存在することを確認
        thumbs_up = Reaction.query.filter_by(
            message_id=message_id,
            user_id=user_id,
            emoji='👍'
        ).first()
        heart = Reaction.query.filter_by(
            message_id=message_id,
            user_id=user_id,
            emoji='❤️'
        ).first()
        
        assert thumbs_up is None
        assert heart is not None
        
        # ユーザーのリアクション数が1つだけであることを確認
        user_reactions = Reaction.query.filter_by(
            message_id=message_id,
            user_id=user_id
        ).all()
        assert len(user_reactions) == 1 