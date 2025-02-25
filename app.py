from app import create_app, socketio
import os

# 開発サーバー用のアプリケーションインスタンスを作成
app = create_app()

if __name__ == '__main__':
    # 開発サーバーとして直接実行する場合
    port = int(os.environ.get('PORT', 3000))
    socketio.run(
        app,
        host='0.0.0.0',  # すべてのインターフェースでリッスン
        port=port,
        debug=False
    ) 