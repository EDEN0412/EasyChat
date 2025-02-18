from datetime import datetime
from app import db

class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.String(255), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーションシップ
    messages = db.relationship('Message', backref='channel', lazy='dynamic')

    def __repr__(self):
        return f'<Channel {self.name}>' 