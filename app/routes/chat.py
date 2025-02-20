from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import Message, Channel, User, Reaction
from app import db, socketio
from datetime import datetime
from sqlalchemy import func
import uuid
from flask_login import login_required

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

def format_reactions(message):
    """メッセージのリアクションを集計してフォーマット"""
    reactions = db.session.query(
        Reaction.emoji,
        func.count(Reaction.user_id).label('count')
    ).filter_by(message_id=message.id).group_by(Reaction.emoji).all()
    
    return [{'emoji': r.emoji, 'count': r.count} for r in reactions]

def format_message(message):
    """メッセージをJSON形式にフォーマット"""
    return {
        'id': message.id,
        'content': message.content,
        'user_id': message.user_id,
        'username': message.author.username,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M'),
        'is_edited': message.is_edited,
        'reactions': format_reactions(message)
    }

@bp.route('/messages')
@bp.route('/messages/<channel_id>')
def messages(channel_id=None):
    # ログインチェック
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # 全チャンネルを取得
    channels = Channel.query.order_by(Channel.name).all()
    
    # チャンネルIDが指定されていない場合はデフォルトチャンネルを使用
    if channel_id is None:
        default_channel = get_or_create_default_channel()
        return redirect(url_for('chat.messages', channel_id=default_channel.id))
    
    # 現在のチャンネルを取得
    current_channel = Channel.query.get_or_404(channel_id)
    
    # チャンネルのメッセージを取得
    messages = Message.query.filter_by(channel_id=channel_id).order_by(Message.created_at.asc()).all()
    
    return render_template('chat/messages.html', 
                         messages=messages, 
                         channels=channels,
                         current_channel=current_channel)

@bp.route('/send', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    content = request.form.get('message')
    channel_id = request.form.get('channel_id')
    
    if not content:
        flash('メッセージを入力してください')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    # チャンネルの存在確認
    channel = Channel.query.get_or_404(channel_id)
    
    # メッセージを保存
    message = Message(
        user_id=session['user_id'],
        channel_id=channel_id,
        content=content,
        created_at=datetime.utcnow()
    )
    db.session.add(message)
    db.session.commit()
    
    # WebSocketでメッセージをブロードキャスト
    socketio.emit('new_message', format_message(message), room=channel_id)
    
    return redirect(url_for('chat.messages', channel_id=channel_id))

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

@bp.route('/messages/<int:message_id>/react', methods=['POST'])
def toggle_reaction(message_id):
    """リアクションの追加/削除"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    emoji = request.json.get('emoji')
    if not emoji:
        return jsonify({'error': 'Emoji is required'}), 400
    
    # メッセージの存在確認
    message = Message.query.get_or_404(message_id)
    
    # 既存のリアクションを確認
    existing_reaction = Reaction.query.filter_by(
        message_id=message_id,
        user_id=session['user_id'],
        emoji=emoji
    ).first()
    
    if existing_reaction:
        # リアクションを削除
        db.session.delete(existing_reaction)
    else:
        # リアクションを追加
        reaction = Reaction(
            message_id=message_id,
            user_id=session['user_id'],
            emoji=emoji
        )
        db.session.add(reaction)
    
    db.session.commit()
    
    # リアクションの更新をブロードキャスト
    message_data = format_message(message)
    socketio.emit('update_reactions', {
        'message_id': message_id,
        'reactions': message_data['reactions']
    })
    
    return jsonify(message_data)

@bp.route('/channels/create', methods=['POST'])
def create_channel():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    # 入力チェック
    if not name:
        flash('チャンネル名は必須です')
        return redirect(url_for('chat.messages'))
    
    # 同名チャンネルのチェック
    existing_channel = Channel.query.filter_by(name=name).first()
    if existing_channel:
        flash('同じ名前のチャンネルが既に存在します')
        return redirect(url_for('chat.messages'))
    
    # チャンネルの作成
    channel = Channel(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        created_by=session['user_id']
    )
    
    try:
        db.session.add(channel)
        db.session.commit()
        flash('チャンネルを作成しました')
        return redirect(url_for('chat.messages', channel_id=channel.id))
    except Exception as e:
        db.session.rollback()
        flash('チャンネルの作成に失敗しました')
        return redirect(url_for('chat.messages')) 