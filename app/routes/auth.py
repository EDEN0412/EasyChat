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
            flash('ユーザー名とパスワードは必須です', 'error')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('パスワードが一致しません', 'error')
            return render_template('auth/register.html')
        
        try:
            # ユーザー作成を試みる
            user = create_user(username, password)
            
            if user:
                # 作成成功したら直接ログインしてチャットページへ
                login_user(user)
                flash('アカウントが作成されました', 'success')
                return redirect(url_for('chat.messages'))
            else:
                flash('ユーザーの作成に失敗しました。もう一度お試しください', 'error')
                return render_template('auth/register.html')
        except Exception as e:
            print(f"登録処理中にエラーが発生しました: {str(e)}")
            print(traceback.format_exc())
            flash(str(e), 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"ログイン試行: username={username}")
        
        if not username or not password:
            flash('ユーザー名とパスワードは必須です', 'error')
            return render_template('auth/login.html')
        
        user = authenticate_user(username, password)
        if user:
            login_user(user)
            print(f"ログイン成功: user_id={user.id}")
            flash('ログインしました', 'success')
            return redirect(url_for('chat.messages'))
        else:
            flash('ユーザー名またはパスワードが正しくありません', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    logout_user()
    flash('ログアウトしました', 'success')
    return redirect(url_for('main.index')) 