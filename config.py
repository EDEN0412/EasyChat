import os
from dotenv import load_dotenv

# 環境変数からテスト環境かどうかを判断
is_testing = os.environ.get('FLASK_ENV') == 'testing'

# テスト環境の場合は.env.testを、それ以外は.envを読み込む
if is_testing:
    load_dotenv('.env.test', override=True)
    print("Loading TEST environment from .env.test")
else:
    load_dotenv()
    print("Loading PRODUCTION environment from .env")

class Config:
    # Flask設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    
    # データベース設定
    password = os.getenv('MYSQL_PASSWORD', '')
    db_type = os.getenv('DB_TYPE', 'mysql')  # デフォルトはMySQL
    
    # RenderのPostgreSQLデータベース設定
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemyの設定
    SQLALCHEMY_ENGINE_OPTIONS = {
        'echo': True,  # SQLログを有効化
        'echo_pool': True,  # プールのデバッグログを有効化
    }
    
    if db_type == 'postgresql':
        # PostgreSQL固有の設定を追加
        SQLALCHEMY_ENGINE_OPTIONS.update({
            'connect_args': {
                'connect_timeout': 10,
                'application_name': 'easychat',
                'options': '-c statement_timeout=10000'
            }
        })
    
    # アプリケーション設定
    APP_PORT = int(os.getenv('APP_PORT', 5000))

class TestConfig(Config):
    TESTING = True
    # テスト用データベース設定を明示的に指定
    SQLALCHEMY_DATABASE_URI = (
        f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@"
        f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/test_chatapp"
    )
    WTF_CSRF_ENABLED = False
    
    def __init__(self):
        print(f"TestConfig initialized with URI: {self.SQLALCHEMY_DATABASE_URI}") 