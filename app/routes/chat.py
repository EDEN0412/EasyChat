from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from app.models import Message, Channel, User, Reaction
from app import db, socketio
from datetime import datetime, UTC
from sqlalchemy import func
import uuid
from functools import wraps
import re
import pytz

bp = Blueprint('chat', __name__)

# 東京タイムゾーンの定義
JST = pytz.timezone('Asia/Tokyo')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def get_or_create_default_channel():
    default_channel = Channel.query.filter_by(name='general').first()
    if not default_channel:
        default_channel = Channel(
            id=str(uuid.uuid4()),
            name='general',
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
    content = message.content
    # メンションをスパンに変換
    mentions = re.findall(r'@(\w+)', content)
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user:
            content = content.replace(
                f'@{username}',
                f'<span class="mention">@{username}</span>'
            )
    
    # UTCから東京時間に変換
    created_at_jst = message.created_at.replace(tzinfo=UTC).astimezone(JST)
    
    return {
        'id': message.id,
        'content': content,
        'raw_content': message.content,
        'user_id': message.user_id,
        'username': message.author.username,
        'created_at': created_at_jst.strftime('%Y年%m月%d日 %H:%M'),
        'is_edited': message.is_edited,
        'reactions': format_reactions(message)
    }

@bp.route('/messages')
@bp.route('/messages/<channel_id>')
@login_required
def messages(channel_id=None):
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
    
    # 各メッセージのコンテンツにメンションタグを適用
    for message in messages:
        message.display_content = format_mentions(message.content)
    
    # 現在のチャンネルに投稿したユーザーのリストを取得（重複なし）
    channel_users = db.session.query(User).join(Message).filter(
        Message.channel_id == channel_id
    ).distinct().all()
    
    users_data = [{'id': user.id, 'username': user.username} for user in channel_users]
    
    return render_template('chat/messages.html', 
                         messages=messages, 
                         channels=channels,
                         current_channel=current_channel,
                         users=users_data,
                         utc=UTC,
                         jst=JST)

def format_mentions(content):
    """メッセージコンテンツ内のメンションをHTMLタグに変換"""
    mentions = re.findall(r'@(\w+)', content)
    result = content
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user:
            result = result.replace(
                f'@{username}',
                f'<span class="mention">@{username}</span>'
            )
    return result

@bp.route('/send', methods=['POST'])
@login_required
def send_message():
    content = request.form.get('message')
    channel_id = request.form.get('channel_id')
    
    if not content:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'メッセージを入力してください'}), 400
        flash('メッセージを入力してください')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    # チャンネルの存在確認
    channel = Channel.query.get_or_404(channel_id)
    
    # メンションされたユーザーを検出
    mentioned_usernames = []
    mention_pattern = r'@(\w+)'
    mentioned_usernames = re.findall(mention_pattern, content)
    
    # メッセージを保存
    message = Message(
        id=str(uuid.uuid4()),
        user_id=session['user_id'],
        channel_id=channel_id,
        content=content,
        created_at=datetime.now(UTC)
    )
    db.session.add(message)
    db.session.commit()
    
    # メンション情報を付加
    formatted_message = format_message(message)
    formatted_message['mentions'] = mentioned_usernames
    
    # WebSocketでメッセージをブロードキャスト
    socketio.emit('new_message', formatted_message, room=channel_id)
    
    # AJAXリクエストの場合はJSONを返す
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(formatted_message)
    
    # 通常のフォーム送信の場合はリダイレクト
    return redirect(url_for('chat.messages', channel_id=channel_id))

@bp.route('/messages/<string:message_id>', methods=['PUT', 'POST'])
@login_required
def edit_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # 権限チェック
    if message.user_id != session['user_id']:
        return jsonify({'error': 'Permission denied'}), 403
    
    content = request.json.get('content') if request.is_json else request.form.get('content')
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    # 内容が変更されたかチェック
    content_changed = message.content != content
    
    if content_changed:
        message.content = content
        message.is_edited = True
        message.updated_at = datetime.now(UTC)
        db.session.commit()
        
        # メッセージにメンションタグを適用
        formatted_message = format_message(message)
        
        # WebSocketで編集をブロードキャスト
        socketio.emit('edit_message', formatted_message)
        
        # 内容が変更された場合のみフラッシュメッセージを表示
        flash('メッセージを編集しました', 'success')
    
    if request.is_json:
        return jsonify(formatted_message if content_changed else format_message(message))
    return redirect(url_for('chat.messages', channel_id=message.channel_id))

@bp.route('/messages/<string:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # 権限チェック
    if message.user_id != session['user_id']:
        flash('他のユーザーのメッセージは削除できません')
        return redirect(url_for('chat.messages', channel_id=message.channel_id))
    
    channel_id = message.channel_id
    
    # 関連するリアクションを先に削除
    Reaction.query.filter_by(message_id=message_id).delete()
    
    # メッセージを削除
    db.session.delete(message)
    db.session.commit()
    
    # WebSocketで削除をブロードキャスト
    socketio.emit('delete_message', {'message_id': message_id})
    
    flash('メッセージを削除しました')
    return redirect(url_for('chat.messages', channel_id=channel_id))

@bp.route('/messages/<string:message_id>', methods=['DELETE'])
@login_required
def delete_message_api(message_id):
    message = Message.query.get_or_404(message_id)
    
    # 権限チェック
    if message.user_id != session['user_id']:
        return jsonify({'error': 'Permission denied'}), 403
    
    channel_id = message.channel_id
    
    # 関連するリアクションを先に削除
    Reaction.query.filter_by(message_id=message_id).delete()
    
    # メッセージを削除
    db.session.delete(message)
    db.session.commit()
    
    # WebSocketで削除をブロードキャスト
    socketio.emit('delete_message', {'message_id': message_id})
    
    return jsonify({'message': 'Message deleted successfully'})

@bp.route('/messages/<string:message_id>/react', methods=['POST'])
@login_required
def toggle_reaction(message_id):
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
@login_required
def create_channel():
    name = request.form.get('name')
    print(f"チャンネル作成リクエスト: name={name}")
    
    # 入力チェック
    if not name:
        print("エラー: チャンネル名が空です")
        flash('チャンネル名は必須です')
        return redirect(url_for('chat.messages'))
    
    # 同名チャンネルのチェック
    existing_channel = Channel.query.filter_by(name=name).first()
    if existing_channel:
        print(f"エラー: 同名のチャンネルが存在します: {name}")
        flash('同じ名前のチャンネルが既に存在します')
        return redirect(url_for('chat.messages'))
    
    # チャンネルの作成
    try:
        channel = Channel(
            id=str(uuid.uuid4()),
            name=name,
            created_by=session['user_id']
        )
        db.session.add(channel)
        db.session.commit()
        print(f"チャンネル作成成功: id={channel.id}, name={channel.name}")
        flash('チャンネルを作成しました')
        return redirect(url_for('chat.messages', channel_id=channel.id))
    except Exception as e:
        db.session.rollback()
        print(f"エラー: チャンネル作成に失敗: {str(e)}")
        flash('チャンネルの作成に失敗しました')
        return redirect(url_for('chat.messages'))

@bp.route('/channels/<string:channel_id>/delete', methods=['POST'])
@login_required
def delete_channel(channel_id):
    # チャンネルの取得
    channel = Channel.query.get_or_404(channel_id)
    
    # 自分が作成者かどうかチェック
    if channel.created_by != session.get('user_id'):
        flash('自分が作成したチャンネルのみ削除できます', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    # デフォルトチャンネルは削除できないようにする
    default_channel = get_or_create_default_channel()
    if channel.id == default_channel.id:
        flash('デフォルトチャンネルは削除できません', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    try:
        # チャンネルに関連するメッセージを削除
        Message.query.filter_by(channel_id=channel.id).delete()
        
        # チャンネルを削除
        db.session.delete(channel)
        db.session.commit()
        
        flash('チャンネルを削除しました', 'success')
        return redirect(url_for('chat.messages', channel_id=default_channel.id))
    except Exception as e:
        db.session.rollback()
        flash('チャンネルの削除に失敗しました', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id)) 