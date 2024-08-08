import os
import random
import logging
import threading
from flask import Flask, redirect, url_for, session, render_template
from flask_socketio import SocketIO, emit
from flask_dance.contrib.github import make_github_blueprint, github
from dotenv import load_dotenv

#читаем файл для скрытия секретных данных
load_dotenv('secrets.env')

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
socketio = SocketIO(app)

logging.basicConfig(level=logging.DEBUG)

# настройка OAuth с помощью flask-dance
github_bp = make_github_blueprint(
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    redirect_to='github_authorized'
)

app.register_blueprint(github_bp, url_prefix='/github_login/github/authorized')

#главная (начальная) страница
@app.route('/')
def index():
    if 'github_user' not in session:  # проверяем, есть ли пользователь в сессии
        return render_template('login.html')  # страница с кнопкой для авторизации
    return render_template('random_number.html')  # страница с генерацией чисел

#путь oauth авторизации
@app.route('/github_login/github/authorized')
def github_authorized():
    if not github.authorized:
        return redirect(url_for('github_login'))
    response = github.get('/user')
    if response.ok:
        session['github_user'] = response.json()
        app.logger.debug(f'Successfully authorized user: {session["github_user"]}')
        return redirect(url_for('index'))
    else:
        app.logger.error('Authorization failed.')
        return 'Authorization failed.'


#путь авторизации
@app.route('/github_login')
def github_login():
    return render_template('login.html')

#путь выхода (разлогирования)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

current_number = random.randint(1, 100)

# Функция для генерации и эмиссии нового числа
def generate_number():
    global current_number
    while True:
        current_number = random.randint(1, 100)
        socketio.emit('new_number', {'number': current_number})
        socketio.sleep(5)

# запуск генерации чисел в отдельном потоке
thread = threading.Thread(target=generate_number)
thread.daemon = True
thread.start()

#обработчик события connect
@socketio.on('connect')
def handle_connect():
    emit('new_number', {'number': current_number})

if __name__ == "__main__":
    socketio.run(app, debug=False, allow_unsafe_werkzeug=True)