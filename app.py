import os
from flask import Flask
from flask_socketio import SocketIO

# appパッケージからcreate_app関数とsocketioインスタンスをインポート
from app import create_app, socketio

# アプリケーションインスタンスを作成
flask_app = create_app()

# Gunicornで使用するWSGIアプリケーション
# この変数名がGunicornの起動コマンドで指定する名前と一致する必要があります
app = flask_app

if __name__ == '__main__':
    # 開発サーバーとして直接実行する場合
    port = int(os.environ.get('PORT', 3000))
    socketio.run(
        flask_app,
        host='0.0.0.0',  # すべてのインターフェースでリッスン
        port=port,
        debug=False
    ) 