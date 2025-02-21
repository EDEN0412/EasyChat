from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app import db
from datetime import datetime, UTC

class Message(db.Model):
    """メッセージモデル"""
    __tablename__ = 'messages'

    id = Column(String(36), primary_key=True)  # UUIDを格納するために36文字の文字列に変更
    channel_id = Column(String(255), ForeignKey('channels.id'), nullable=False)
    user_id = Column(String(255), ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # リレーションシップ
    user = relationship('User', backref='messages')
    channel = relationship('Channel', backref='messages')
    reactions = relationship('Reaction', backref='message', cascade='all, delete-orphan')

class Reaction(db.Model):
    """リアクションモデル"""
    __tablename__ = 'reactions'

    message_id = Column(String(36), ForeignKey('messages.id'), primary_key=True)  # UUIDを格納するために36文字の文字列に変更
    user_id = Column(String(255), ForeignKey('users.id'), primary_key=True)
    emoji = Column(String(10), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # リレーションシップ
    user = relationship('User', backref='reactions') 