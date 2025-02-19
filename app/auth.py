import uuid
import bcrypt
from flask import session
from app.models import User
from app import db

def generate_password_hash(password):
    """パスワードをハッシュ化する"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password_hash(password, password_hash):
    """パスワードとハッシュを比較する"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def create_user(username, password):
    """新しいユーザーを作成する"""
    # ユーザーIDを生成
    user_id = str(uuid.uuid4())
    
    # パスワードをハッシュ化
    password_hash = generate_password_hash(password)
    
    # ユーザーを作成
    user = User(
        id=user_id,
        username=username,
        password_hash=password_hash
    )
    
    db.session.add(user)
    db.session.commit()
    
    return user

def authenticate_user(username, password):
    """ユーザーを認証する"""
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(password, user.password_hash):
        return user
    return None

def login_user(user):
    """ユーザーをログインさせる"""
    session['user_id'] = user.id
    session['username'] = user.username

def logout_user():
    """ユーザーをログアウトさせる"""
    session.pop('user_id', None)
    session.pop('username', None)

def get_current_user():
    """現在のログインユーザーを取得する"""
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None 