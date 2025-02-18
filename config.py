import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class Config:
    # Flask設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI = (
        f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@"
        f"{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # アプリケーション設定
    APP_PORT = int(os.getenv('APP_PORT', 5000)) 