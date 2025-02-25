"""
Gunicornが使用するWSGIアプリケーションを提供するファイル
"""
from app import create_app

# アプリケーションインスタンスを作成
application = create_app()

# Gunicornで使用するWSGIアプリケーション
app = application

if __name__ == "__main__":
    app.run() 