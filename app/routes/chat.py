from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import Message, Channel, User
from app import db, socketio
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

def format_message(message):
    """メッセージをJSON形式にフォーマット"""
    return {
        'id': message.id,
        'content': message.content,
        'user_id': message.user_id,
        'username': message.author.username,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
        'is_edited': message.is_edited
    }

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
    
    # WebSocketでメッセージをブロードキャスト
    socketio.emit('new_message', format_message(message))
    
    return redirect(url_for('chat.messages'))

@bp.route('/messages/<int:message_id>/edit', methods=['POST'])
def edit_message(message_id):
    # ログインチェック
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    message = Message.query.get_or_404(message_id)
    
    # 権限チェック
    if message.user_id != session['user_id']:
        flash('他のユーザーのメッセージは編集できません')
        return redirect(url_for('chat.messages'))
    
    content = request.form.get('content')
    if not content:
        flash('メッセージを入力してください')
        return redirect(url_for('chat.messages'))
    
    message.content = content
    message.is_edited = True
    message.updated_at = datetime.utcnow()
    db.session.commit()
    
    # WebSocketで編集をブロードキャスト
    socketio.emit('edit_message', format_message(message))
    
    return redirect(url_for('chat.messages'))

@bp.route('/messages/<int:message_id>/delete', methods=['POST'])
def delete_message(message_id):
    # ログインチェック
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    message = Message.query.get_or_404(message_id)
    
    # 権限チェック
    if message.user_id != session['user_id']:
        flash('他のユーザーのメッセージは削除できません')
        return redirect(url_for('chat.messages'))
    
    db.session.delete(message)
    db.session.commit()
    
    # WebSocketで削除をブロードキャスト
    socketio.emit('delete_message', {'message_id': message_id})
    
    return redirect(url_for('chat.messages')) 