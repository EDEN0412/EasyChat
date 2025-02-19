from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Message, Channel
from app import db
from datetime import datetime
import uuid

bp = Blueprint('chat', __name__)

def get_or_create_default_channel():
    default_channel = Channel.query.filter_by(name='general').first()
    if not default_channel:
        default_channel = Channel(
            id=str(uuid.uuid4()),
            name='general',
            description='General discussion channel',
            created_by=session['user_id']
        )
        db.session.add(default_channel)
        db.session.commit()
    return default_channel

@bp.route('/messages')
def messages():
    # ログインチェック
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # デフォルトチャンネルの取得または作成
    default_channel = get_or_create_default_channel()
    
    # メッセージ一覧を取得
    messages = Message.query.filter_by(channel_id=default_channel.id).order_by(Message.created_at.asc()).all()
    return render_template('chat/messages.html', messages=messages)

@bp.route('/send', methods=['POST'])
def send_message():
    # ログインチェック
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    content = request.form.get('message')
    if not content:
        flash('メッセージを入力してください')
        return redirect(url_for('chat.messages'))
    
    # デフォルトチャンネルの取得
    default_channel = get_or_create_default_channel()
    
    # メッセージを保存
    message = Message(
        user_id=session['user_id'],
        channel_id=default_channel.id,
        content=content,
        created_at=datetime.utcnow()
    )
    db.session.add(message)
    db.session.commit()
    
    return redirect(url_for('chat.messages')) 