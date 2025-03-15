import os
import secrets
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.forms import ProfileForm
from app.models.user import User

profile = Blueprint('profile', __name__)

@profile.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit():
    form = ProfileForm()
    
    # GETリクエストの場合はフォームに現在の値をセット
    if request.method == 'GET':
        form.status_message.data = current_user.status_message
        if current_user.avatar_bg_color:
            form.avatar_bg_color.data = current_user.avatar_bg_color
        if current_user.avatar_text_color:
            form.avatar_text_color.data = current_user.avatar_text_color
        return render_template('profile/edit.html', form=form)
    
    # POSTリクエストの場合は処理を実行
    if form.validate_on_submit():
        # 変更があったかどうかを追跡するフラグ
        changes_made = False
        
        # ステータスメッセージが変更された場合のみ更新
        if form.status_message.data != current_user.status_message:
            current_user.status_message = form.status_message.data
            changes_made = True
            
        # 背景色が変更された場合のみ更新
        if form.avatar_bg_color.data != current_user.avatar_bg_color:
            current_user.avatar_bg_color = form.avatar_bg_color.data
            changes_made = True
            
        # テキスト色が変更された場合のみ更新
        if form.avatar_text_color.data != current_user.avatar_text_color:
            current_user.avatar_text_color = form.avatar_text_color.data
            changes_made = True
        
        # 変更があった場合のみ保存して通知
        if changes_made:
            db.session.commit()
            flash('プロフィールが更新されました', 'success')
            return redirect(url_for('profile.view', username=current_user.username))
        else:
            # 変更がない場合は編集ページに留まる（通知なし）
            return render_template('profile/edit.html', form=form)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
        return render_template('profile/edit.html', form=form)

@profile.route('/profile/<username>', methods=['GET'])
def view(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # 自分のプロフィールを表示する場合はフォームも用意
    form = None
    if current_user.is_authenticated and current_user.id == user.id:
        form = ProfileForm()
        form.status_message.data = current_user.status_message
    
    return render_template('profile/view.html', user=user, form=form) 