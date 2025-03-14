import uuid
from datetime import datetime
import bcrypt
from flask import session
from flask_login import login_user as flask_login_user, logout_user as flask_logout_user, current_user
from app.models import User
from app import db
import traceback
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

@contextmanager
def session_scope():
    """トランザクションを管理するコンテキストマネージャー"""
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    finally:
        db.session.remove()

def hash_password(password):
    """パスワードをハッシュ化する"""
    # パスワードをバイト列に変換
    password_bytes = password.encode('utf-8')
    # ソルトを生成してハッシュ化
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # ハッシュ化されたパスワードを文字列として返す
    return hashed.decode('utf-8')

def check_password(hashed_password, password):
    """パスワードが正しいかチェックする"""
    # ハッシュ化されたパスワードとプレーンテキストのパスワードを比較
    return bcrypt.checkpw(
        password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def create_user(username, password):
    """新しいユーザーを作成する"""
    print(f"ユーザー作成を試みます: {username}")
    
    # ユーザーIDを生成
    user_id = str(uuid.uuid4())
    # パスワードをハッシュ化
    password_hash = hash_password(password)
    # 現在時刻を取得
    now = datetime.utcnow()
    
    # ユーザーオブジェクトを作成
    user = User(
        id=user_id,
        username=username,
        password_hash=password_hash,
        created_at=now,
        updated_at=now
    )
    
    # データベースに保存
    # 新しいセッションでトランザクションを開始
    with db.engine.connect() as conn:
        with conn.begin():
            # 既存のユーザー名をチェック
            result = conn.execute(
                sa.text('SELECT id FROM users WHERE username = :username'),
                {'username': username}
            ).fetchone()
            
            if result:
                print("ユーザー名が既に使用されています")
                raise Exception(f"ユーザー名 '{username}' は既に使用されています")
            
            # ユーザーを作成
            conn.execute(
                sa.text('''
                    INSERT INTO users (id, username, password_hash, created_at, updated_at)
                    VALUES (:id, :username, :password_hash, :created_at, :updated_at)
                '''),
                {
                    'id': user_id,
                    'username': username,
                    'password_hash': password_hash,
                    'created_at': now,
                    'updated_at': now
                }
            )
    
    print(f"ユーザー '{username}' を作成しました。ID: {user_id}")
    return user

def get_user_by_username(username):
    """ユーザー名からユーザーを取得する"""
    try:
        return User.query.filter_by(username=username).first()
    except Exception:
        return None

def authenticate_user(username, password):
    """ユーザーを認証する"""
    try:
        # 直接SQLを使用してユーザーを取得
        with db.engine.connect() as conn:
            result = conn.execute(
                sa.text('SELECT * FROM users WHERE username = :username'),
                {'username': username}
            ).fetchone()
            
            if result and check_password(result.password_hash, password):
                # ユーザーオブジェクトを作成して返す
                user = User(
                    id=result.id,
                    username=result.username,
                    password_hash=result.password_hash,
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )
                return user
    except Exception as e:
        print(f"認証エラー: {str(e)}")
        print(traceback.format_exc())
    return None

def login_user(user):
    """ユーザーをログイン状態にする"""
    session['user_id'] = user.id
    session['username'] = user.username
    # Flask-Loginのログイン処理も実行
    flask_login_user(user)

def logout_user():
    """ユーザーをログアウト状態にする"""
    session.pop('user_id', None)
    session.pop('username', None)
    # Flask-Loginのログアウト処理も実行
    flask_logout_user()

def get_current_user():
    """現在のログインユーザーを取得する"""
    user_id = session.get('user_id')
    if user_id:
        try:
            # 直接SQLを使用してユーザーを取得
            with db.engine.connect() as conn:
                result = conn.execute(
                    sa.text('SELECT * FROM users WHERE id = :user_id'),
                    {'user_id': user_id}
                ).fetchone()
                
                if result:
                    # ユーザーオブジェクトを作成して返す
                    return User(
                        id=result.id,
                        username=result.username,
                        password_hash=result.password_hash,
                        created_at=result.created_at,
                        updated_at=result.updated_at
                    )
        except Exception as e:
            print(f"ユーザー取得エラー: {str(e)}")
            print(traceback.format_exc())
    return None 