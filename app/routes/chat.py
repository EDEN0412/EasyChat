from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, current_app, send_from_directory
from app.models import Message, Channel, User, Reaction
from app import db, socketio
from datetime import datetime, UTC
from sqlalchemy import func
import uuid
from functools import wraps
import re
import pytz
import os
import tempfile
from werkzeug.utils import secure_filename
import traceback

bp = Blueprint('chat', __name__, url_prefix='/chat')

# 東京タイムゾーンの定義
JST = pytz.timezone('Asia/Tokyo')

# 許可されるファイル拡張子
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 画像保存用の一時ディレクトリ
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'easychat_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """ファイルが許可された拡張子か確認する"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# アップロードフォルダの設定
def setup_upload_folder():
    """アップロードフォルダが存在することを確認"""
    # 一時ディレクトリを使用
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    current_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    return True

# リクエスト前の処理
@bp.before_app_request
def before_request():
    """リクエスト前の処理"""
    # アップロードフォルダの確認
    if 'UPLOAD_FOLDER' not in current_app.config:
        setup_upload_folder()

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
        'avatar_bg_color': message.author.avatar_bg_color,
        'avatar_text_color': message.author.avatar_text_color,
        'created_at': created_at_jst.strftime('%Y年%m月%d日 %H:%M'),
        'is_edited': message.is_edited,
        'image_url': message.image_url,
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
        # AJAXリクエストの場合はリダイレクトせずにJSONでチャンネル一覧を返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            channels_data = [{
                'id': ch.id,
                'name': ch.name,
                'created_by': ch.created_by,
                'created_at': ch.created_at.isoformat() if ch.created_at else None,
                'updated_at': ch.updated_at.isoformat() if ch.updated_at else None
            } for ch in channels]
            
            return jsonify({
                'status': 'success',
                'channels': channels_data,
                'default_channel_id': default_channel.id
            })
        
        return redirect(url_for('chat.messages', channel_id=default_channel.id))
    
    # 現在のチャンネルを取得
    current_channel = Channel.query.get_or_404(channel_id)
    
    # チャンネルのメッセージを取得
    messages = Message.query.filter_by(channel_id=channel_id).order_by(Message.created_at.asc()).all()
    
    # 各メッセージの処理
    for message in messages:
        # メンションタグを適用
        message.display_content = format_mentions(message.content)
    
    # 現在のチャンネルに投稿したユーザーのリストを取得（重複なし）
    channel_users = db.session.query(User).join(Message).filter(
        Message.channel_id == channel_id
    ).distinct().all()
    
    users_data = [{'id': user.id, 'username': user.username} for user in channel_users]
    
    # AJAXリクエストの場合はJSONレスポンスを返す
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        channels_data = [{
            'id': ch.id,
            'name': ch.name,
            'created_by': ch.created_by,
            'created_at': ch.created_at.isoformat() if ch.created_at else None,
            'updated_at': ch.updated_at.isoformat() if ch.updated_at else None
        } for ch in channels]
        
        messages_data = [format_message(msg) for msg in messages]
        
        return jsonify({
            'status': 'success',
            'current_channel': {
                'id': current_channel.id,
                'name': current_channel.name,
                'created_by': current_channel.created_by,
                'created_at': current_channel.created_at.isoformat() if current_channel.created_at else None,
                'updated_at': current_channel.updated_at.isoformat() if current_channel.updated_at else None
            },
            'channels': channels_data,
            'messages': messages_data,
            'users': users_data
        })
    
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
    """メッセージを送信"""
    try:
        # デバッグ情報
        print("=" * 50)
        print("リクエストデータ:")
        print(f"フォームデータ: {request.form}")
        print(f"ファイル: {request.files}")
        print(f"ヘッダー: {request.headers}")
        
        # チャンネルIDの取得
        channel_id = request.form.get('channel_id')
        print(f"チャンネルID: {channel_id}")
        
        if not channel_id:
            error_msg = 'チャンネルIDが指定されていません'
            print(f"エラー: {error_msg}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('chat.messages'))
        
        # メッセージ内容と画像の取得
        content = request.form.get('message', '').strip()
        image_file = request.files.get('image')
        print(f"メッセージ内容: {content}")
        print(f"画像ファイル: {image_file.filename if image_file else None}")
        
        # メッセージも画像も空の場合はエラー
        if not content and (not image_file or not image_file.filename):
            error_msg = 'メッセージまたは画像を入力してください'
            print(f"エラー: {error_msg}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('chat.messages', channel_id=channel_id))
        
        # 画像処理
        image_url = None
        if image_file and image_file.filename:
            try:
                # 画像形式チェック
                if not allowed_file(image_file.filename):
                    error_msg = '許可されていないファイル形式です'
                    print(f"エラー: {error_msg} (ファイル名: {image_file.filename})")
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('chat.messages', channel_id=channel_id))
                
                # アップロードディレクトリのチェック
                upload_folder = current_app.config.get('UPLOAD_FOLDER', UPLOAD_FOLDER)
                os.makedirs(upload_folder, exist_ok=True)
                print(f"アップロードディレクトリ: {upload_folder}")
                
                # 画像保存
                filename = secure_filename(image_file.filename)
                random_filename = f"{uuid.uuid4().hex}_{filename}"
                image_path = os.path.join(upload_folder, random_filename)
                print(f"画像保存先: {image_path}")
                
                image_file.save(image_path)
                print(f"画像保存成功: {os.path.exists(image_path)}")
                
                # 画像配信用のルートを作成
                image_url = url_for('chat.get_uploaded_image', filename=random_filename)
                print(f"画像URL: {image_url}")
                
            except Exception as e:
                error_msg = f'画像アップロードエラー: {str(e)}'
                print(f"例外: {error_msg}")
                print(traceback.format_exc())
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': error_msg}), 500
                flash(error_msg, 'error')
                return redirect(url_for('chat.messages', channel_id=channel_id))
        
        # メッセージ作成
        message = Message(
            id=str(uuid.uuid4()),
            content=content,
            user_id=session.get('user_id'),
            channel_id=channel_id,
            image_url=image_url
        )
        
        # メンション処理
        mentioned_usernames = []
        if content:
            for match in re.finditer(r'@(\w+)', content):
                username = match.group(1)
                user = User.query.filter_by(username=username).first()
                if user:
                    mentioned_usernames.append(username)
        
        # データベースに保存
        try:
            db.session.add(message)
            db.session.commit()
            print(f"メッセージをDBに保存: ID={message.id}")
        except Exception as e:
            error_msg = f'データベース保存エラー: {str(e)}'
            print(f"例外: {error_msg}")
            print(traceback.format_exc())
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 500
            flash(error_msg, 'error')
            return redirect(url_for('chat.messages', channel_id=channel_id))
        
        # メッセージフォーマット
        formatted_message = format_message(message)
        formatted_message['mentions'] = mentioned_usernames
        formatted_message['channel_id'] = channel_id  # channel_idを明示的に追加
        
        # WebSocketでブロードキャスト
        try:
            socketio.emit('new_message', formatted_message, room=channel_id)
            print(f"WebSocketでメッセージを送信: room={channel_id}")
        except Exception as e:
            print(f"WebSocket送信エラー: {str(e)}")
            print(traceback.format_exc())
            # WebSocketエラーは無視して処理を続行
        
        # AJAXリクエストの場合はJSONを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            response_data = {
                'status': 'success',
                'message': 'メッセージを送信しました',
                'data': formatted_message
            }
            print(f"JSONレスポンス: {response_data}")
            return jsonify(response_data)
        
        print("リダイレクトレスポンス")
        flash('メッセージを送信しました', 'success')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    except Exception as e:
        # エラーログ
        error_msg = f"メッセージ送信エラー: {str(e)}"
        print(f"予期しない例外: {error_msg}")
        print(traceback.format_exc())
        current_app.logger.error(error_msg)
        
        # AJAXリクエストの場合はJSONでエラー返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': error_msg}), 500
        
        flash(error_msg, 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id if channel_id else None))

@bp.route('/messages/<string:message_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_message(message_id):
    """メッセージを編集する"""
    content = request.form.get('content', '').strip()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'GET':
        # GET リクエストの場合、編集フォームを表示
        message = Message.query.get(message_id)
        if not message:
            if is_ajax:
                return jsonify({'error': 'メッセージが見つかりません'}), 404
            flash('メッセージが見つかりません', 'error')
            return redirect(url_for('chat.messages'))
        
        if message.user_id != session['user_id']:
            if is_ajax:
                return jsonify({'error': '自分のメッセージのみ編集できます'}), 403
            flash('自分のメッセージのみ編集できます', 'error')
            return redirect(url_for('chat.messages'))
            
        # メッセージの編集ページを返す（必要に応じて実装）
        return redirect(url_for('chat.messages', channel_id=message.channel_id))
    
    # POSTリクエストの処理
    if not content:
        if is_ajax:
            return jsonify({'error': 'メッセージを入力してください'}), 400
        flash('メッセージを入力してください', 'error')
        return redirect(url_for('chat.messages'))
    
    message = Message.query.get(message_id)
    if not message:
        if is_ajax:
            return jsonify({'error': 'メッセージが見つかりません'}), 404
        flash('メッセージが見つかりません', 'error')
        return redirect(url_for('chat.messages'))
    
    if message.user_id != session['user_id']:
        if is_ajax:
            return jsonify({'error': '自分のメッセージのみ編集できます'}), 403
        flash('自分のメッセージのみ編集できます', 'error')
        return redirect(url_for('chat.messages'))
    
    # 内容に変更があるか確認
    content_changed = message.content != content
    
    if content_changed:
        message.content = content
        message.is_edited = True
        message.updated_at = datetime.now(UTC)
        db.session.commit()
        
        # WebSocketで編集済みメッセージを送信
        socketio.emit('message_edited', {
            'message_id': message.id,
            'content': message.content,
            'is_edited': message.is_edited
        }, room=message.channel_id)
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': 'メッセージを編集しました',
                'content': message.content,
                'is_edited': message.is_edited
            })
        flash('メッセージを編集しました', 'success')
    else:
        if is_ajax:
            return jsonify({'success': True, 'message': '変更はありませんでした'})
    
    return redirect(url_for('chat.messages', channel_id=message.channel_id))

@bp.route('/messages/<string:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    """メッセージを削除する"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        message = Message.query.get(message_id)
        
        if not message:
            if is_ajax:
                return jsonify({'error': 'メッセージが見つかりません'}), 404
            flash('メッセージが見つかりません', 'error')
            return redirect(url_for('chat.messages'))
        
        if message.user_id != session['user_id']:
            if is_ajax:
                return jsonify({'error': '自分のメッセージのみ削除できます'}), 403
            flash('自分のメッセージのみ削除できます', 'error')
            return redirect(url_for('chat.messages'))
        
        channel_id = message.channel_id
        
        # 関連するリアクションを先に削除
        try:
            Reaction.query.filter_by(message_id=message_id).delete()
        except Exception as e:
            print(f"リアクション削除エラー: {str(e)}")
        
        db.session.delete(message)
        db.session.commit()
        
        # WebSocketでメッセージ削除を通知
        socketio.emit('message_deleted', {
            'message_id': message_id
        }, room=channel_id)
        
        if is_ajax:
            return jsonify({'success': True, 'message': 'メッセージを削除しました'})
        
        flash('メッセージを削除しました', 'success')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    except Exception as e:
        print(f"メッセージ削除エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if is_ajax:
            return jsonify({'error': 'メッセージの削除中にエラーが発生しました'}), 500
            
        flash('メッセージの削除中にエラーが発生しました', 'error')
        return redirect(url_for('chat.messages'))

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
    socketio.emit('message_deleted', {
        'message_id': message_id
    }, room=channel_id)
    
    return jsonify({'message': 'Message deleted successfully'})

@bp.route('/messages/<string:message_id>/react', methods=['POST'])
@login_required
def toggle_reaction(message_id):
    # JSONとフォームデータの両方からemojiを取得
    emoji = None
    if request.is_json:
        emoji = request.json.get('emoji')
    else:
        emoji = request.form.get('emoji')
    
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
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'チャンネル名は必須です'}), 400
        flash('チャンネル名は必須です')
        return redirect(url_for('chat.messages'))
    
    # 同名チャンネルのチェック
    existing_channel = Channel.query.filter_by(name=name).first()
    if existing_channel:
        print(f"エラー: 同名のチャンネルが存在します: {name}")
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': '同じ名前のチャンネルが既に存在します'}), 400
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
        
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'チャンネルを作成しました',
                'channel': {
                    'id': channel.id,
                    'name': channel.name
                }
            }), 200
            
        flash('チャンネルを作成しました')
        return redirect(url_for('chat.messages', channel_id=channel.id))
    except Exception as e:
        db.session.rollback()
        print(f"エラー: チャンネル作成に失敗: {str(e)}")
        
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'チャンネルの作成に失敗しました'}), 500
            
        flash('チャンネルの作成に失敗しました')
        return redirect(url_for('chat.messages'))

@bp.route('/channels/<string:channel_id>/delete', methods=['POST'])
@login_required
def delete_channel(channel_id):
    # チャンネルの取得
    channel = Channel.query.get_or_404(channel_id)
    
    # 自分が作成者かどうかチェック
    if channel.created_by != session.get('user_id'):
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': '自分が作成したチャンネルのみ削除できます'}), 403
        flash('自分が作成したチャンネルのみ削除できます', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    # デフォルトチャンネルは削除できないようにする
    default_channel = get_or_create_default_channel()
    if channel.id == default_channel.id:
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'デフォルトチャンネルは削除できません'}), 400
        flash('デフォルトチャンネルは削除できません', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    try:
        # チャンネルに関連するメッセージを削除
        Message.query.filter_by(channel_id=channel.id).delete()
        
        # チャンネルを削除
        db.session.delete(channel)
        db.session.commit()
        
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'チャンネルを削除しました',
                'redirect_to': url_for('chat.messages', channel_id=default_channel.id)
            }), 200
            
        flash('チャンネルを削除しました', 'success')
        return redirect(url_for('chat.messages', channel_id=default_channel.id))
    except Exception as e:
        db.session.rollback()
        
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'チャンネルの削除に失敗しました'}), 500
            
        flash('チャンネルの削除に失敗しました', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))

@bp.route('/channels/<string:channel_id>/edit', methods=['POST'])
@login_required
def edit_channel(channel_id):
    # チャンネルの取得
    channel = Channel.query.get_or_404(channel_id)
    
    # 自分が作成者かどうかチェック
    if channel.created_by != session.get('user_id'):
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': '自分が作成したチャンネルのみ編集できます'}), 403
        flash('自分が作成したチャンネルのみ編集できます', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    # デフォルトチャンネルは編集できないようにする
    default_channel = get_or_create_default_channel()
    if channel.id == default_channel.id:
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'デフォルトチャンネルは編集できません'}), 400
        flash('デフォルトチャンネルは編集できません', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    # 新しいチャンネル名を取得
    new_name = request.form.get('name')
    if not new_name:
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'チャンネル名は必須です'}), 400
        flash('チャンネル名は必須です', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    # 同名チャンネルのチェック（自分自身は除く）
    existing_channel = Channel.query.filter(Channel.name == new_name, Channel.id != channel_id).first()
    if existing_channel:
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': '同じ名前のチャンネルが既に存在します'}), 400
        flash('同じ名前のチャンネルが既に存在します', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))
    
    try:
        # 変更があるかチェック
        if channel.name != new_name:
            # チャンネル名を更新
            channel.name = new_name
            channel.updated_at = datetime.now(UTC)
            db.session.commit()
            
            # AJAXリクエストの場合はJSONレスポンスを返す
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'チャンネル名を更新しました',
                    'channel': {
                        'id': channel.id,
                        'name': new_name
                    }
                }), 200
                
            flash('チャンネル名を更新しました', 'success')
        else:
            # 変更がない場合もJSONレスポンスを返す
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': '変更はありません',
                    'channel': {
                        'id': channel.id,
                        'name': channel.name
                    }
                }), 200
                
        return redirect(url_for('chat.messages', channel_id=channel_id))
    except Exception as e:
        db.session.rollback()
        
        # AJAXリクエストの場合はJSONレスポンスを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'チャンネル名の更新に失敗しました'}), 500
            
        flash('チャンネル名の更新に失敗しました', 'error')
        return redirect(url_for('chat.messages', channel_id=channel_id))

# 新しいテストルートの追加
@bp.route('/simple_test')
@login_required
def simple_test():
    """シンプルなテストページ"""
    # デフォルトチャンネルを取得
    default_channel = get_or_create_default_channel()
    return render_template('simple_test.html', channel_id=default_channel.id)

# 画像表示用のエンドポイントを追加
@bp.route('/uploads/<filename>')
def get_uploaded_image(filename):
    """アップロードされた画像を提供する"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@bp.route('/search')
@login_required
def search_messages():
    """メッセージを検索する"""
    keyword = request.args.get('keyword', '')
    channel_id = request.args.get('channel_id')
    
    if not keyword or not channel_id:
        return jsonify({'messages': []})
    
    # キーワードを含むメッセージを検索
    messages = Message.query.filter(
        Message.channel_id == channel_id,
        Message.content.ilike(f'%{keyword}%')
    ).order_by(Message.created_at.desc()).all()
    
    # 検索結果をフォーマット
    result = []
    for message in messages:
        # メッセージの作成日時をJSTに変換
        created_at_jst = message.created_at.replace(tzinfo=UTC).astimezone(JST)
        timestamp = created_at_jst.strftime('%Y年%m月%d日 %H:%M')
        
        # メンションを処理したコンテンツを取得
        content = format_mentions(message.content)
        
        result.append({
            'id': message.id,
            'username': message.author.username,
            'content': content,
            'timestamp': timestamp,
            'is_edited': message.is_edited
        })
    
    return jsonify({'messages': result})

@bp.route('/channels/search')
@login_required
def search_channels():
    """チャンネルを検索する"""
    keyword = request.args.get('keyword', '')
    
    if not keyword:
        # キーワードがない場合は全てのチャンネルを返す
        channels = Channel.query.all()
    else:
        # キーワードを含むチャンネルを検索
        channels = Channel.query.filter(
            Channel.name.ilike(f'%{keyword}%')
        ).all()
    
    # 検索結果をフォーマット
    result = []
    for channel in channels:
        # チャンネルの作成日時をJSTに変換
        created_at_jst = channel.created_at.replace(tzinfo=UTC).astimezone(JST)
        updated_at_jst = channel.updated_at.replace(tzinfo=UTC).astimezone(JST)
        
        result.append({
            'id': channel.id,
            'name': channel.name,
            'created_by': channel.created_by,
            'created_at': created_at_jst.strftime('%Y年%m月%d日 %H:%M'),
            'updated_at': updated_at_jst.strftime('%Y年%m月%d日 %H:%M')
        })
    
    return jsonify({'channels': result}) 