from datetime import datetime
from app import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(255), primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーションシップ
    messages = db.relationship('Message', backref='author', lazy='dynamic')
    channels = db.relationship('Channel', secondary='channel_members', backref=db.backref('members', lazy='dynamic'))

    def __repr__(self):
        return f'<User {self.username}>' 