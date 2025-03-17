import pytest
from flask import url_for, json
from app import create_app, db
from app.models import User, Channel, Message
from app.auth import create_user
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

def test_send_message_api(auth_client, test_channel, app):
    """メッセージ送信APIのテスト - JSON形式"""
    with app.app_context():
        # ヘッダーにXMLHttpRequestを設定してJSONレスポンスを強制
        headers = {
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # 正常系：有効なメッセージを送信
        response = auth_client.post('/chat/send', 
            data={
                'message': 'Hello, API Test!',
                'channel_id': test_channel
            }, 
            headers=headers,
            follow_redirects=True
        )
        
        # ステータスコードが成功を示すことを確認
        assert response.status_code in (200, 201)
        
        # データベースにメッセージが保存されたことを確認
        message = Message.query.filter_by(content='Hello, API Test!').first()
        assert message is not None
        assert message.channel_id == test_channel
        assert message.user_id == 'test-user-id'

def test_message_validation_api(auth_client, test_channel, app):
    """メッセージバリデーションAPIのテスト - JSON形式"""
    with app.app_context():
        # ヘッダーにXMLHttpRequestを設定してJSONレスポンスを強制
        headers = {
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # 異常系：空のメッセージ
        response = auth_client.post('/chat/send', 
            data={
                'message': '',
                'channel_id': test_channel
            }, 
            headers=headers,
            follow_redirects=True
        )
        
        # エラーレスポンスを確認
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data 

def test_upload_image_api(auth_client, test_channel, app):
    """画像アップロードAPIのテスト - JSON形式"""
    with app.app_context():
        # ヘッダーにXMLHttpRequestを設定してJSONレスポンスを強制
        headers = {
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # テスト用の画像を作成
        img = Image.new('RGB', (100, 100), color='red')
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        
        # 画像のみのメッセージを送信
        data = {
            'channel_id': test_channel,
            'image': (img_io, 'test_image.jpg')
        }
        response = auth_client.post('/chat/send', 
            data=data,
            headers=headers,
            follow_redirects=True,
            content_type='multipart/form-data'
        )
        
        # ステータスコードが成功を示すことを確認
        assert response.status_code in (200, 201)
        
        # データベースに画像URLを含むメッセージが保存されたことを確認
        message = Message.query.filter_by(content='').first()
        assert message is not None
        assert message.image_url is not None
        assert message.channel_id == test_channel
        assert message.user_id == 'test-user-id'
        
        # 2回目のテスト用に新しい画像を作成
        img2 = Image.new('RGB', (100, 100), color='blue')
        img_io2 = io.BytesIO()
        img2.save(img_io2, 'JPEG')
        img_io2.seek(0)
        
        # テキストと画像の両方を含むメッセージを送信
        data2 = {
            'message': 'Image with text',
            'channel_id': test_channel,
            'image': (img_io2, 'test_image2.jpg')
        }
        response = auth_client.post('/chat/send', 
            data=data2,
            headers=headers,
            follow_redirects=True,
            content_type='multipart/form-data'
        )
        
        # ステータスコードが成功を示すことを確認
        assert response.status_code in (200, 201)
        
        # データベースにテキストと画像URLの両方を含むメッセージが保存されたことを確認
        message = Message.query.filter_by(content='Image with text').first()
        assert message is not None
        assert message.image_url is not None
        assert message.channel_id == test_channel
        assert message.user_id == 'test-user-id' 