import os
import secrets
import uuid
import tempfile
from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.forms import ProfileForm
from app.models.user import User

profile = Blueprint('profile', __name__)

# 画像保存用の一時ディレクトリ
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'easychat_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_avatar(form_avatar):
    """アバター画像を保存し、ファイル名を返す"""
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_avatar.filename)
    avatar_fn = random_hex + f_ext
    
    # 一時ディレクトリに保存
    avatar_path = os.path.join(UPLOAD_FOLDER, avatar_fn)
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
    
    # 画像をリサイズして保存
    output_size = (150, 150)
    i = Image.open(form_avatar)
    i.thumbnail(output_size)
    i.save(avatar_path)
    
    return f'/profile/uploads/{avatar_fn}'

@profile.route('/profile/edit', methods=['POST'])
@login_required
def edit():
    form = ProfileForm()
    
    if form.validate_on_submit():
        # 変更があったかどうかを追跡するフラグ
        changes_made = False
        
        # アバター画像が提供された場合は保存
        if form.avatar.data:
            avatar_file = save_avatar(form.avatar.data)
            if current_user.avatar_url != avatar_file:
                current_user.avatar_url = avatar_file
                changes_made = True
        
        # ステータスメッセージが変更された場合のみ更新
        if form.status_message.data != current_user.status_message:
            current_user.status_message = form.status_message.data
            changes_made = True
        
        # 変更があった場合のみ保存して通知
        if changes_made:
            db.session.commit()
            flash('プロフィールが更新されました', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('profile.view', username=current_user.username))

@profile.route('/profile/<username>', methods=['GET'])
def view(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # 自分のプロフィールを表示する場合はフォームも用意
    form = None
    if current_user.is_authenticated and current_user.id == user.id:
        form = ProfileForm()
        form.status_message.data = current_user.status_message
    
    return render_template('profile/view.html', user=user, form=form)

# アップロードされた画像を提供するルート
@profile.route('/profile/uploads/<filename>')
def get_uploaded_avatar(filename):
    """アップロードされたアバター画像を提供する"""
    return send_from_directory(UPLOAD_FOLDER, filename) 