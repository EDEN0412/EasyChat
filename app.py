from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(
        app,
        host='127.0.0.1',  # localhostに限定
        port=3000,         # 明示的にポート3000を指定
        debug=True
    ) 