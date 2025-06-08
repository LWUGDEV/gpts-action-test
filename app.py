from flask import Flask, request, jsonify, render_template_string
import json
import datetime
import os
from pathlib import Path

app = Flask(__name__)

# データ保存用ディレクトリ
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

LOGS_FILE = DATA_DIR / "logs.json"
RECEIVED_DATA_FILE = DATA_DIR / "received_data.json"

def log_event(event_type, data=None, status="success", error=None):
    """イベントをログに記録"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event_type": event_type,
        "status": status,
        "data": data,
        "error": error
    }
    
    # ログファイルの読み込み
    logs = []
    if LOGS_FILE.exists():
        try:
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            logs = []
    
    logs.append(log_entry)
    
    # 最新100件のみ保持
    logs = logs[-100:]
    
    # ログファイルの書き込み
    with open(LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def save_received_data(data):
    """受信したデータを保存"""
    received_data = []
    if RECEIVED_DATA_FILE.exists():
        try:
            with open(RECEIVED_DATA_FILE, 'r', encoding='utf-8') as f:
                received_data = json.load(f)
        except:
            received_data = []
    
    data_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "data": data
    }
    
    received_data.append(data_entry)
    
    # 最新100件のみ保持
    received_data = received_data[-100:]
    
    with open(RECEIVED_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(received_data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    """メインページ"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>GPTs Action Test</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; display: inline-block; margin: 5px; }
            .button:hover { background: #005a8b; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>GPTs Action Test Application</h1>
            
            <div class="section">
                <h2>エンドポイント情報</h2>
                <div class="endpoint">
                    <strong>POST:</strong> /api/receive<br>
                    <strong>Content-Type:</strong> application/json<br>
                    <strong>説明:</strong> GPTsアクションからJSONデータを受信
                </div>
            </div>
            
            <div class="section">
                <h2>データ参照</h2>
                <a href="/logs" class="button">処理ログを見る</a>
                <a href="/data" class="button">受信データを見る</a>
            </div>
            
            <div class="section">
                <h2>テスト用</h2>
                <p>curlでテストする場合:</p>
                <div class="endpoint">
curl -X POST {{ request.url_root }}api/receive \\<br>
  -H "Content-Type: application/json" \\<br>
  -d '{"test": "data", "message": "Hello from GPTs"}'
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/api/receive', methods=['POST'])
def receive_data():
    """GPTsアクションからのデータを受信"""
    try:
        # リクエストデータの取得
        data = request.get_json()
        
        if data is None:
            log_event("receive_data", error="No JSON data received", status="error")
            return jsonify({"error": "No JSON data received"}), 400
        
        # データの保存
        save_received_data(data)
        
        # ログの記録
        log_event("receive_data", data=data)
        
        # レスポンス
        response_data = {
            "status": "success",
            "message": "Data received and saved",
            "timestamp": datetime.datetime.now().isoformat(),
            "received_data": data
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        error_msg = str(e)
        log_event("receive_data", error=error_msg, status="error")
        return jsonify({"error": error_msg}), 500

@app.route('/logs')
def view_logs():
    """処理ログの表示"""
    logs = []
    if LOGS_FILE.exists():
        try:
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            logs = []
    
    # 最新のログから表示
    logs.reverse()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>処理ログ - GPTs Action Test</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1000px; margin: 0 auto; }
            .log-entry { margin: 10px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .log-success { border-left: 4px solid #4CAF50; }
            .log-error { border-left: 4px solid #f44336; }
            .timestamp { color: #666; font-size: 0.9em; }
            .data { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; font-family: monospace; }
            .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; display: inline-block; margin: 5px; }
            .button:hover { background: #005a8b; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>処理ログ</h1>
            <p><a href="/" class="button">← ホームに戻る</a> <a href="/data" class="button">受信データを見る</a></p>
            
            {% if logs %}
                {% for log in logs %}
                <div class="log-entry {{ 'log-success' if log.status == 'success' else 'log-error' }}">
                    <div class="timestamp">{{ log.timestamp }}</div>
                    <div><strong>イベント:</strong> {{ log.event_type }}</div>
                    <div><strong>ステータス:</strong> {{ log.status }}</div>
                    {% if log.error %}
                    <div><strong>エラー:</strong> {{ log.error }}</div>
                    {% endif %}
                    {% if log.data %}
                    <div><strong>データ:</strong></div>
                    <div class="data">{{ log.data | tojson(indent=2) }}</div>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
                <p>まだログがありません。</p>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, logs=logs)

@app.route('/data')
def view_data():
    """受信データの表示"""
    received_data = []
    if RECEIVED_DATA_FILE.exists():
        try:
            with open(RECEIVED_DATA_FILE, 'r', encoding='utf-8') as f:
                received_data = json.load(f)
        except:
            received_data = []
    
    # 最新のデータから表示
    received_data.reverse()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>受信データ - GPTs Action Test</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1000px; margin: 0 auto; }
            .data-entry { margin: 10px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; border-left: 4px solid #2196F3; }
            .timestamp { color: #666; font-size: 0.9em; }
            .data { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; font-family: monospace; }
            .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; display: inline-block; margin: 5px; }
            .button:hover { background: #005a8b; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>受信データ</h1>
            <p><a href="/" class="button">← ホームに戻る</a> <a href="/logs" class="button">処理ログを見る</a></p>
            
            {% if received_data %}
                {% for entry in received_data %}
                <div class="data-entry">
                    <div class="timestamp">受信時刻: {{ entry.timestamp }}</div>
                    <div class="data">{{ entry.data | tojson(indent=2) }}</div>
                </div>
                {% endfor %}
            {% else %}
                <p>まだ受信データがありません。</p>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, received_data=received_data)

if __name__ == '__main__':
    log_event("app_start", data={"message": "Application started"})
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)