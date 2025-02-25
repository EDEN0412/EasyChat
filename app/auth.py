import uuid
from datetime import datetime
import bcrypt
from flask import session
from app.models import User
from app import db
import traceback
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

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
    print(f"ユーザー作成を試みます...")
    
    try:
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
        
        # データベースに追加
        db.session.add(user)
        db.session.commit()
        print(f"ユーザー '{username}' を作成しました。ID: {user_id}")
        return user
    except SQLAlchemyError as e:
        print(f"SQLAlchemyエラー: {str(e)}")
        print(traceback.format_exc())
        
        # セッションをロールバック
        try:
            db.session.rollback()
        except Exception as rollback_error:
            print(f"ロールバックエラー: {str(rollback_error)}")
        
        # テーブルが存在しない場合は作成を試みる
        if "relation" in str(e) and "does not exist" in str(e):
            try:
                print("テーブルが存在しないため、作成を試みます...")
                with db.engine.connect() as conn:
                    conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id VARCHAR(255) PRIMARY KEY, username VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL)"))
                    conn.commit()
                print("usersテーブルを作成しました。再度ユーザー作成を試みてください。")
            except Exception as create_error:
                print(f"テーブル作成エラー: {str(create_error)}")
        
        return None
    except Exception as e:
        print(f"ユーザー作成エラー: {str(e)}")
        print(traceback.format_exc())
        
        try:
            db.session.rollback()
        except Exception as rollback_error:
            print(f"ロールバックエラー: {str(rollback_error)}")
        
        return None

def get_user_by_username(username):
    """ユーザー名からユーザーを取得する"""
    return User.query.filter_by(username=username).first()

def authenticate_user(username, password):
    """ユーザーを認証する"""
    user = get_user_by_username(username)
    if user and check_password(user.password_hash, password):
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