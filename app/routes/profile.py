import os
import secrets
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
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

# APIエンドポイント
@profile.route('/profile/api/<username>', methods=['GET'])
def get_profile_api(username):
    """ユーザープロフィールAPIエンドポイント"""
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'error': 'ユーザーが見つかりません'}), 404
    
    # プロフィール情報をJSON形式で返す
    profile_data = {
        'username': user.username,
        'status_message': user.status_message or '',
        'avatar_bg_color': user.avatar_bg_color or '#3498db',
        'avatar_text_color': user.avatar_text_color or '#ffffff',
        'created_at': user.created_at.strftime('%Y年%m月%d日')
    }
    
    # アバター画像の参照を削除
    # if user.avatar_image:
    #     profile_data['avatar_image'] = url_for('static', filename=f'uploads/avatars/{user.avatar_image}')
    
    return jsonify(profile_data)

@profile.route('/profile/api/update_status', methods=['POST'])
@login_required
def update_status_api():
    """ステータスメッセージ更新APIエンドポイント"""
    data = request.get_json()
    
    if 'status_message' not in data:
        return jsonify({'success': False, 'error': 'ステータスメッセージが含まれていません'}), 400
    
    # ステータスメッセージを更新
    current_user.status_message = data['status_message']
    db.session.commit()
    
    return jsonify({
        'success': True,
        'status_message': current_user.status_message
    })

@profile.route('/profile/api/update_avatar_colors', methods=['POST'])
@login_required
def update_avatar_colors_api():
    """アバターカラー更新APIエンドポイント"""
    data = request.get_json()
    
    # バリデーション
    if 'avatar_bg_color' not in data or 'avatar_text_color' not in data:
        return jsonify({'success': False, 'error': '背景色とテキスト色が必要です'}), 400
    
    # 色形式の簡易バリデーション（16進カラーコードの形式かチェック）
    bg_color = data['avatar_bg_color']
    text_color = data['avatar_text_color']
    
    import re
    color_pattern = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')
    
    if not color_pattern.match(bg_color) or not color_pattern.match(text_color):
        return jsonify({'success': False, 'error': '無効な色形式です。#RRGGBBの形式で指定してください'}), 400
    
    # アバターカラーを更新
    current_user.avatar_bg_color = bg_color
    current_user.avatar_text_color = text_color
    db.session.commit()
    
    return jsonify({
        'success': True,
        'avatar_bg_color': current_user.avatar_bg_color,
        'avatar_text_color': current_user.avatar_text_color
    }) 