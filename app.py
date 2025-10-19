from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO
import os, subprocess, signal, threading

app = Flask(__name__)
socketio = SocketIO(app)
UPLOAD_FOLDER = 'bots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot_process = None
bot_file_path = None

def stream_logs(process):
    for line in iter(process.stdout.readline, b''):
        socketio.emit('log', line.decode('utf-8'))
    process.stdout.close()

@app.route('/')
def index():
    global bot_process
    status = "🟢 Running" if bot_process else "🔴 Stopped"
    files = os.listdir(UPLOAD_FOLDER)
    return render_template('index.html', status=status, files=files)

@app.route('/upload', methods=['POST'])
def upload():
    global bot_file_path
    file = request.files['file']
    if file and file.filename.endswith('.py'):
        bot_file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(bot_file_path)
    return redirect(url_for('index'))

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_process, bot_file_path
    if bot_file_path and not bot_process:
        bot_process = subprocess.Popen(
            ['python', bot_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1
        )
        threading.Thread(target=stream_logs, args=(bot_process,), daemon=True).start()
    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot_process
    if bot_process:
        os.kill(bot_process.pid, signal.SIGTERM)
        bot_process = None
    return redirect(url_for('index'))

@app.route('/edit/<filename>')
def edit_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'r') as f:
        content = f.read()
    return jsonify({"content": content})

@app.route('/save/<filename>', methods=['POST'])
def save_file(filename):
    data = request.get_json()
    code = data.get('code', '')
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'w') as f:
        f.write(code)
    return jsonify({"status": "saved"})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080)
