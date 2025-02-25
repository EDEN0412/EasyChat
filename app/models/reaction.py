from datetime import datetime
from app import db

class Reaction(db.Model):
    __tablename__ = 'reactions'

    message_id = db.Column(db.String(36), db.ForeignKey('messages.id'), primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users.id'), primary_key=True)
    emoji = db.Column(db.String(10), primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Reaction {self.emoji}>' 