from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from config import Config
import traceback
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

# グローバルなインスタンスの初期化
db = SQLAlchemy()
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
            # 明示的にエンジンを作成してテスト
            engine = db.get_engine()
            print(f"データベースエンジン: {engine}")
            
            # 接続テスト - 新しい接続を作成
            with engine.connect() as connection:
                print("データベース接続成功")
                
                # テーブル一覧を取得
                inspector = sa.inspect(engine)
                tables = inspector.get_table_names()
                print(f"データベーステーブル一覧: {tables}")
                
                # usersテーブルが存在するか確認
                if 'users' in tables:
                    print("usersテーブルが存在します")
                else:
                    print("警告: usersテーブルが存在しません。テーブルを作成します。")
                    # テーブルを作成
                    from app.models import User, Channel, Message, Reaction, ChannelMember
                    db.create_all()
                    print("テーブルを作成しました")
                    
                    # 再度テーブル一覧を確認
                    tables = inspector.get_table_names()
                    print(f"テーブル作成後のテーブル一覧: {tables}")
    except SQLAlchemyError as e:
        print(f"SQLAlchemyエラー: {str(e)}")
        print(traceback.format_exc())
        print("アプリケーションは起動しますが、データベース機能が正常に動作しない可能性があります。")
    except Exception as e:
        print(f"データベース接続エラー: {str(e)}")
        print(traceback.format_exc())
        print("アプリケーションは起動しますが、データベース機能が正常に動作しない可能性があります。")

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