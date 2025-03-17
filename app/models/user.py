from datetime import datetime, UTC
from flask_login import UserMixin
from app import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.String(255), primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    status_message = db.Column(db.String(255), nullable=True)
    avatar_bg_color = db.Column(db.String(20), nullable=True, default='#1d9bf0')  # デフォルトの背景色
    avatar_text_color = db.Column(db.String(20), nullable=True, default='#ffffff')  # デフォルトのテキスト色
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # リレーションシップ
    messages = db.relationship('Message', backref='author', lazy='dynamic')
    channels = db.relationship('Channel', backref=db.backref('created_by_user', lazy='joined'), primaryjoin="User.id==Channel.created_by", foreign_keys="Channel.created_by")

    def __repr__(self):
        return f'<User {self.username}>' 