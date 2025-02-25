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
    password = os.getenv('MYSQL_PASSWORD')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql://{os.getenv('MYSQL_USER')}@"
        f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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