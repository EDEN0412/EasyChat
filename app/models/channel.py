from datetime import datetime, UTC
from app import db

class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.String(255), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # リレーションシップ
    messages = db.relationship('Message', backref='channel', lazy='dynamic')

    def __repr__(self):
        return f'<Channel {self.name}>' 