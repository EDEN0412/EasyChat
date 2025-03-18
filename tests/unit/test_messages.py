import pytest
from flask import url_for
from app import create_app, db
from app.models import User, Channel, Message, Reaction
from app.auth import create_user
from datetime import datetime, UTC
import uuid
import io
from PIL import Image
from flask_login import login_user

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
        # Flask-Loginのlogin_userを使用
        with client.session_transaction() as session:
            # 元のセッション情報を保持
            session['user_id'] = user.id
            session['username'] = user.username
        
        # クライアントでリクエストを作成してlogin_userを呼び出す
        with app.test_request_context():
            login_user(user)
            # テスト用のセッションにユーザーIDを設定
            from flask import session as app_session
            app_session['_user_id'] = user.id

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

def test_upload_image(auth_client, test_channel, app):
    """画像アップロード機能のテスト"""
    with app.app_context():
        # テスト用の画像を作成
        img = Image.new('RGB', (100, 100), color='red')
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        
        # 画像のみのメッセージを送信
        response = auth_client.post('/chat/send', data={
            'channel_id': test_channel,
            'image': (img_io, 'test_image.jpg')
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # 画像URLを含むメッセージがデータベースに保存されたことを確認
        message = Message.query.filter_by(content='').first()
        assert message is not None
        assert message.image_url is not None
        
        # 2回目のテスト用に新しい画像を作成
        img2 = Image.new('RGB', (100, 100), color='blue')
        img_io2 = io.BytesIO()
        img2.save(img_io2, 'JPEG')
        img_io2.seek(0)
        
        # テキストと画像の両方を含むメッセージを送信
        response = auth_client.post('/chat/send', data={
            'message': 'Image with text',
            'channel_id': test_channel,
            'image': (img_io2, 'test_image2.jpg')
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # テキストと画像URLの両方を含むメッセージがデータベースに保存されたことを確認
        message = Message.query.filter_by(content='Image with text').first()
        assert message is not None
        assert message.image_url is not None

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
        response = auth_client.post(f'/chat/messages/{message.id}/reaction',
                               data={'emoji': '👍'})
        assert response.status_code == 200

        # リアクションがデータベースに保存されたことを確認
        reaction = Reaction.query.filter_by(message_id=message.id, user_id=test_user).first()
        assert reaction is not None
        assert reaction.emoji == '👍'

        # 同じ絵文字を再度追加（削除されるはず）
        response = auth_client.post(f'/chat/messages/{message.id}/reaction',
                               data={'emoji': '👍'})
        assert response.status_code == 200

        # リアクションが削除されたことを確認
        reaction = Reaction.query.filter_by(message_id=message.id, user_id=test_user).first()
        assert reaction is None

        # 別の絵文字を追加
        response = auth_client.post(f'/chat/messages/{message.id}/reaction',
                               data={'emoji': '❤️'})
        assert response.status_code == 200

        # 新しいリアクションが保存されたことを確認
        reaction = Reaction.query.filter_by(message_id=message.id, user_id=test_user).first()
        assert reaction is not None
        assert reaction.emoji == '❤️'

        # 全てのリアクションを削除
        reactions = Reaction.query.filter_by(message_id=message.id).all()
        for reaction in reactions:
            db.session.delete(reaction)
        db.session.commit()

        # メッセージを削除
        db.session.delete(message)
        db.session.commit()

        # 削除されたメッセージにリアクションを追加しようとする
        response = auth_client.post(f'/chat/messages/{message.id}/reaction',
                               data={'emoji': '👍'})
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