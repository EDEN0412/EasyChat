from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from app.auth import create_user, authenticate_user, login_user, logout_user
import traceback

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        print(f"登録リクエスト: username={username}")
        
        if not username or not password:
            error_msg = 'ユーザー名とパスワードは必須です'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            error_msg = 'パスワードが一致しません'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth/register.html')
        
        try:
            # ユーザー作成を試みる
            user = create_user(username, password)
            
            if user:
                # 作成成功したら直接ログインしてチャットページへ
                login_user(user)
                success_msg = 'アカウントが作成されました'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': success_msg, 'user_id': user.id}), 200
                flash(success_msg, 'success')
                return redirect(url_for('chat.messages'))
            else:
                error_msg = 'ユーザーの作成に失敗しました。もう一度お試しください'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': error_msg}), 500
                flash(error_msg, 'error')
                return render_template('auth/register.html')
        except Exception as e:
            print(f"登録処理中にエラーが発生しました: {str(e)}")
            print(traceback.format_exc())
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 500
            flash(error_msg, 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"ログイン試行: username={username}")
        
        if not username or not password:
            error_msg = 'ユーザー名とパスワードは必須です'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth/login.html')
        
        user = authenticate_user(username, password)
        
        if user:
            login_user(user)
            success_msg = 'ログインしました'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': success_msg, 'user_id': user.id}), 200
            flash(success_msg, 'success')
            return redirect(url_for('chat.messages'))
        else:
            error_msg = 'ユーザー名またはパスワードが無効です'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 401
            flash(error_msg, 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    success_msg = 'ログアウトしました'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success_msg}), 200
    flash(success_msg, 'success')
    return redirect(url_for('main.index')) 