from app import create_app, socketio
import os

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    socketio.run(
        app,
        host='0.0.0.0',  # すべてのインターフェースでリッスン
        port=port,
        debug=False
    ) 