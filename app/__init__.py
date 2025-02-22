from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from config import Config

# グローバルなインスタンスの初期化
db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()

def create_app(config_class=Config):
    # Flaskアプリケーションの作成
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    if not app.config.get('SOCKETIO_ENABLED', True):
        app.wsgi_app = app.wsgi_app
    else:
        socketio.init_app(app, cors_allowed_origins="*")

    # ルートの登録
    from app.routes import main, auth, chat
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(chat.bp, url_prefix='/chat')

    # モデルの登録
    from app.models import User, Channel, Message, Reaction, ChannelMember

    # エラーハンドラーの登録
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app 