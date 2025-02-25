from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from app.auth import create_user, authenticate_user, login_user, logout_user
import traceback

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"登録リクエスト: username={username}")
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。')
            return render_template('auth/register.html')
        
        try:
            # ユーザー作成を試みる
            user = create_user(username, password)
            
            if user:
                flash('アカウントが作成されました。ログインしてください。')
                return redirect(url_for('auth.login'))
            else:
                flash('ユーザーの作成に失敗しました。もう一度お試しください。')
                # 再度登録ページを表示
                return render_template('auth/register.html')
        except Exception as e:
            print(f"登録処理中にエラーが発生しました: {str(e)}")
            print(traceback.format_exc())
            flash('ユーザーの作成に失敗しました。もう一度お試しください。')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください。')
            return render_template('auth/login.html')
        
        user = authenticate_user(username, password)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.index'))
        else:
            flash('ユーザー名またはパスワードが正しくありません。')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    logout_user()
    flash('ログアウトしました。')
    return redirect(url_for('main.index')) 