from datetime import datetime
from flask_login import UserMixin
from app import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.String(255), primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    status_message = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーションシップ
    messages = db.relationship('Message', backref='author', lazy='dynamic')
    channels = db.relationship('Channel', backref=db.backref('created_by_user', lazy='joined'), primaryjoin="User.id==Channel.created_by", foreign_keys="Channel.created_by")

    def __repr__(self):
        return f'<User {self.username}>' 