from flask import Blueprint, request, render_template, redirect, url_for, flash
from app.auth import create_user, authenticate_user, login_user, logout_user

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        # 入力チェック
        if not username or not password:
            flash('ユーザー名とパスワードは必須です')
            return render_template('auth/register.html')
        
        if password != password_confirm:
            flash('パスワードが一致しません')
            return render_template('auth/register.html')
        
        try:
            user = create_user(username, password)
            login_user(user)
            return redirect(url_for('main.index'))
        except Exception as e:
            flash('ユーザーの作成に失敗しました')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('ユーザー名とパスワードは必須です')
            return render_template('auth/login.html')
        
        user = authenticate_user(username, password)
        if user:
            login_user(user)
            return redirect(url_for('main.index'))
        
        flash('ユーザー名またはパスワードが正しくありません')
        return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index')) 