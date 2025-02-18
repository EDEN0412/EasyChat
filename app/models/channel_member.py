from datetime import datetime
from app import db

class ChannelMember(db.Model):
    __tablename__ = 'channel_members'

    channel_id = db.Column(db.String(255), db.ForeignKey('channels.id'), primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey('users.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_read_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ChannelMember {self.channel_id}:{self.user_id}>' 