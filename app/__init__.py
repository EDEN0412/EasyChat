from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from config import Config
import traceback
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

# グローバルなインスタンスの初期化
db = SQLAlchemy(engine_options={'poolclass': NullPool})  # プーリングを無効化
migrate = Migrate()
socketio = SocketIO()

def create_app(config_class=Config):
    # Flaskアプリケーションの作成
    app = Flask(__name__)
    app.config.from_object(config_class)

    # データベース接続情報をログに出力
    print(f"データベース接続URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"SQLAlchemyプール設定: {app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})}")
    
    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    if not app.config.get('SOCKETIO_ENABLED', True):
        app.wsgi_app = app.wsgi_app
    else:
        socketio.init_app(app, cors_allowed_origins="*")

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