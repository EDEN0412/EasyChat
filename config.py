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
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    
    # データベース設定
    password = os.getenv('MYSQL_PASSWORD', '')
    db_type = os.getenv('DB_TYPE', 'mysql')  # デフォルトはMySQL
    
    # データベースURIの構築
    if db_type == 'postgresql':
        # PostgreSQL用のURI
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@"
            f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DATABASE')}"
        )
    else:
        # MySQL用のURI
        SQLALCHEMY_DATABASE_URI = (
            f"mysql://{os.getenv('MYSQL_USER')}@"
            f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
        )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False  # 明示的なコミットを要求
    
    # SQLAlchemyのプール設定を最適化
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,  # プールサイズを小さく保つ
        'max_overflow': 2,  # オーバーフロー接続を制限
        'pool_timeout': 30,  # タイムアウトを30秒に設定
        'pool_recycle': 1800,  # 30分でコネクションをリサイクル
        'pool_pre_ping': True,  # 接続前にpingを送信
        'echo': True,  # SQLログを出力
        'echo_pool': True,  # プール関連のログを出力
    }
    
    # アプリケーション設定
    APP_PORT = int(os.getenv('APP_PORT', 5000))

class TestConfig(Config):
    TESTING = True
    # テスト用データベース設定を明示的に指定
    SQLALCHEMY_DATABASE_URI = (
        f"mysql://{os.getenv('MYSQL_USER')}@"
        f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/test_chatapp"
    )
    WTF_CSRF_ENABLED = False
    
    def __init__(self):
        print(f"TestConfig initialized with URI: {self.SQLALCHEMY_DATABASE_URI}") 