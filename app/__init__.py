from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# グローバルなインスタンスの初期化
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    # Flaskアプリケーションの作成
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)

    # ルートの登録
    from app.routes import main
    app.register_blueprint(main.bp)

    return app 