from flask import Flask, render_template, request, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO, join_room, leave_room
from flask_login import LoginManager
from config import Config
import traceback
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool
import os
from functools import wraps

# グローバルなインスタンスの初期化
db = SQLAlchemy(engine_options={'poolclass': NullPool})  # プーリングを無効化
migrate = Migrate()
socketio = SocketIO()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'この機能を使用するにはログインが必要です。'
login_manager.login_message_category = 'info'

def check_auth(username, password):
    """Basic認証のクレデンシャルを確認"""
    return username == os.getenv('BASIC_AUTH_USERNAME') and password == os.getenv('BASIC_AUTH_PASSWORD')

def authenticate():
    """Basic認証を要求するレスポンスを返す"""
    return Response(
        'Basic認証が必要です。', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def create_app(config_class=Config):
    # Flaskアプリケーションの作成
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 環境変数の確認とBasic認証の設定
    env = os.getenv('FLASK_ENV', 'production')  # デフォルトはproduction
    print(f"現在の環境: {env}")
    print(f"Basic認証ユーザー名設定: {os.getenv('BASIC_AUTH_USERNAME')}")
    print(f"Basic認証パスワード設定: {'設定済み' if os.getenv('BASIC_AUTH_PASSWORD') else '未設定'}")

    # Basic認証の設定
    if env == 'production' or (os.getenv('BASIC_AUTH_USERNAME') and os.getenv('BASIC_AUTH_PASSWORD')):
        print(f"Basic認証を有効化します（環境: {env}）")
        @app.before_request
        def basic_auth(*args, **kwargs):
            if request.endpoint != 'static':  # 静的ファイルは認証をスキップ
                auth = request.authorization
                if not auth or not check_auth(auth.username, auth.password):
                    return authenticate()
    else:
        print("Basic認証は開発環境で無効です")

    # データベース接続情報をログに出力
    print(f"データベース接続URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"SQLAlchemyプール設定: {app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})}")
    
    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    if not app.config.get('SOCKETIO_ENABLED', True):
        app.wsgi_app = app.wsgi_app
    else:
        socketio.init_app(app, cors_allowed_origins="*")

    # ユーザーローダーの設定
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(user_id)

    # データベース接続テスト
    try:
        with app.app_context():
            # テーブルが存在しない場合は作成
            db.create_all()
            print("データベーステーブルの初期化が完了しました")
            
            # 接続テスト
            with db.engine.connect() as conn:
                result = conn.execute(sa.text('SELECT 1')).scalar()
                print(f"データベース接続テスト成功: {result}")
            
    except SQLAlchemyError as e:
        print(f"SQLAlchemyエラー: {str(e)}")
        print(traceback.format_exc())
    except Exception as e:
        print(f"データベース接続エラー: {str(e)}")
        print(traceback.format_exc())

    # ルートの登録
    from app.routes import main, auth, chat, profile
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(chat.bp, url_prefix='/chat')
    app.register_blueprint(profile.profile)

    # モデルの登録
    from app.models import User, Channel, Message, Reaction

    # エラーハンドラーの登録
    @app.errorhandler(404)
    def not_found_error(error):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'ページが見つかりません'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'アクセス権限がありません'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'サーバーエラーが発生しました'}), 500
        return render_template('errors/500.html'), 500

    return app 