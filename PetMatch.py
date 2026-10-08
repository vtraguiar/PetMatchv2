from app import app, socketio
from config.extensions import db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    print("Tabelas criadas com sucesso!")

    socketio.run(
        app,
        debug=True,
        allow_unsafe_werkzeug=True
    )