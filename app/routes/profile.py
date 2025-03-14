import os
import secrets
from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import ProfileForm
from app.models.user import User

profile = Blueprint('profile', __name__)

def save_avatar(form_avatar):
    """アバター画像を保存し、ファイル名を返す"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_avatar.filename)
    avatar_fn = random_hex + f_ext
    avatar_path = os.path.join(current_app.root_path, 'static/avatars', avatar_fn)
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
    
    # 画像をリサイズして保存
    output_size = (150, 150)
    i = Image.open(form_avatar)
    i.thumbnail(output_size)
    i.save(avatar_path)
    
    return f'/static/avatars/{avatar_fn}'

@profile.route('/profile/edit', methods=['POST'])
@login_required
def edit():
    form = ProfileForm()
    
    if form.validate_on_submit():
        # アバター画像が提供された場合は保存
        if form.avatar.data:
            avatar_file = save_avatar(form.avatar.data)
            current_user.avatar_url = avatar_file
        
        current_user.status_message = form.status_message.data
        current_user.theme_preference = form.theme_preference.data
        
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
        if current_user.theme_preference:
            form.theme_preference.data = current_user.theme_preference
    
    return render_template('profile/view.html', user=user, form=form) 