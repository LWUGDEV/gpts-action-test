from flask import Flask, request, jsonify, render_template_string, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
import json
import datetime
import os
import io
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

app = Flask(__name__)

# PostgreSQL設定
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'postgresql://localhost:5432/workout_logs'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# データ保存用ディレクトリ（ログ用）
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

LOGS_FILE = DATA_DIR / "logs.json"
RECEIVED_DATA_FILE = DATA_DIR / "received_data.json"
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"

# データベースモデル
class WorkoutSession(db.Model):
    __tablename__ = 'workout_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    day_of_week = db.Column(db.String(20))
    facility = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # リレーション
    workout_logs = db.relationship('WorkoutLog', backref='session', lazy=True, cascade='all, delete-orphan')

class WorkoutLog(db.Model):
    __tablename__ = 'workout_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_sessions.id'), nullable=False)
    exercise_name = db.Column(db.String(200), nullable=False)
    exercise_category = db.Column(db.String(50))
    weight = db.Column(db.String(50))
    reps = db.Column(db.Integer)
    rest_pause_reps = db.Column(db.Integer, default=0)
    sets = db.Column(db.Integer)
    target_muscle = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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

def save_conversation_data(data):
    """会話データを保存"""
    conversations = []
    if CONVERSATIONS_FILE.exists():
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
        except:
            conversations = []
    
    conversation_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "conversation_id": data.get("conversation_id", f"conv_{len(conversations) + 1}"),
        "data": data
    }
    
    conversations.append(conversation_entry)
    
    # 最新100件のみ保持
    conversations = conversations[-100:]
    
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

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
                <div class="endpoint">
                    <strong>POST:</strong> /api/conversation<br>
                    <strong>Content-Type:</strong> application/json<br>
                    <strong>説明:</strong> 会話データを解析・保存
                </div>
                <div class="endpoint">
                    <strong>POST:</strong> /api/workout<br>
                    <strong>Content-Type:</strong> application/json<br>
                    <strong>説明:</strong> 筋トレログを保存（レストレップ法対応）
                </div>
            </div>
            
            <div class="section">
                <h2>筋トレログ</h2>
                <a href="/workouts" class="button">ワークアウト一覧</a>
                <a href="/workouts/weekly" class="button">週次サマリ</a>
                <a href="/workouts/monthly" class="button">月次サマリ</a>
                <a href="/api/export/excel" class="button" style="background: #28a745;">📊 Excelダウンロード</a>
            </div>
            
            <div class="section">
                <h2>データ参照</h2>
                <a href="/logs" class="button">処理ログを見る</a>
                <a href="/data" class="button">受信データを見る</a>
                <a href="/conversations" class="button">会話データを見る</a>
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

@app.route('/api/conversation', methods=['POST'])
def save_conversation():
    """会話データを受信・保存"""
    try:
        # リクエストデータの取得
        data = request.get_json()
        
        if data is None:
            log_event("save_conversation", error="No JSON data received", status="error")
            return jsonify({"error": "No JSON data received"}), 400
        
        # 必須フィールドのチェック
        if not data.get("user_input") or not data.get("conversation_summary"):
            log_event("save_conversation", error="Missing required fields", status="error")
            return jsonify({"error": "user_input and conversation_summary are required"}), 400
        
        # 会話データの保存
        save_conversation_data(data)
        
        # ログの記録
        log_event("save_conversation", data=data)
        
        # レスポンス
        response_data = {
            "status": "success",
            "message": "Conversation data saved successfully",
            "conversation_id": data.get("conversation_id", f"conv_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        error_msg = str(e)
        log_event("save_conversation", error=error_msg, status="error")
        return jsonify({"error": error_msg}), 500

@app.route('/api/workout', methods=['POST'])
def save_workout():
    """筋トレログを受信・保存"""
    try:
        # リクエストデータの取得
        data = request.get_json()
        
        if data is None:
            log_event("save_workout", error="No JSON data received", status="error")
            return jsonify({"error": "No JSON data received"}), 400
        
        # 必須フィールドのチェック
        if not data.get("date") or not data.get("exercises"):
            log_event("save_workout", error="Missing required fields", status="error")
            return jsonify({"error": "date and exercises are required"}), 400
        
        # セッションを作成または取得
        session_date = datetime.datetime.strptime(data['date'], '%Y-%m-%d').date()
        
        session = WorkoutSession.query.filter_by(date=session_date).first()
        if not session:
            session = WorkoutSession(
                date=session_date,
                day_of_week=data.get('day_of_week'),
                facility=data.get('facility')
            )
            db.session.add(session)
            db.session.flush()  # IDを取得するため
        
        # エクササイズデータを保存
        for exercise in data['exercises']:
            workout_log = WorkoutLog(
                session_id=session.id,
                exercise_name=exercise.get('name'),
                exercise_category=exercise.get('category'),
                weight=exercise.get('weight'),
                reps=exercise.get('reps'),
                rest_pause_reps=exercise.get('rest_pause_reps', 0),
                sets=exercise.get('sets'),
                target_muscle=exercise.get('target_muscle'),
                notes=exercise.get('notes')
            )
            db.session.add(workout_log)
        
        db.session.commit()
        
        # ログの記録
        log_event("save_workout", data={"session_id": session.id, "exercises_count": len(data['exercises'])})
        
        # レスポンス
        response_data = {
            "status": "success",
            "message": "Workout data saved successfully",
            "session_id": session.id,
            "date": data['date'],
            "exercises_count": len(data['exercises']),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        log_event("save_workout", error=error_msg, status="error")
        return jsonify({"error": error_msg}), 500

@app.route('/api/workout/<int:session_id>', methods=['GET'])
def get_workout_session(session_id):
    """特定のワークアウトセッションを取得"""
    try:
        session = WorkoutSession.query.get_or_404(session_id)
        
        session_data = {
            'id': session.id,
            'date': session.date.strftime('%Y-%m-%d'),
            'day_of_week': session.day_of_week,
            'facility': session.facility,
            'exercises': []
        }
        
        for log in session.workout_logs:
            exercise_data = {
                'id': log.id,
                'name': log.exercise_name,
                'category': log.exercise_category,
                'weight': log.weight,
                'reps': log.reps,
                'rest_pause_reps': log.rest_pause_reps,
                'sets': log.sets,
                'target_muscle': log.target_muscle,
                'notes': log.notes
            }
            session_data['exercises'].append(exercise_data)
        
        return jsonify(session_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/workout/<int:session_id>', methods=['DELETE'])
def delete_workout_session(session_id):
    """ワークアウトセッションを削除"""
    try:
        session = WorkoutSession.query.get_or_404(session_id)
        
        # セッション情報をログに記録
        log_event("delete_workout_session", data={
            "session_id": session_id,
            "date": session.date.strftime('%Y-%m-%d'),
            "exercises_count": len(session.workout_logs)
        })
        
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Workout session deleted successfully",
            "session_id": session_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        log_event("delete_workout_session", error=error_msg, status="error")
        return jsonify({"error": error_msg}), 500

@app.route('/api/workout/exercise/<int:exercise_id>', methods=['PUT'])
def update_exercise(exercise_id):
    """個別エクササイズを更新"""
    try:
        exercise = WorkoutLog.query.get_or_404(exercise_id)
        data = request.get_json()
        
        if data is None:
            return jsonify({"error": "No JSON data received"}), 400
        
        # フィールドを更新
        if 'name' in data:
            exercise.exercise_name = data['name']
        if 'category' in data:
            exercise.exercise_category = data['category']
        if 'weight' in data:
            exercise.weight = data['weight']
        if 'reps' in data:
            exercise.reps = data['reps']
        if 'rest_pause_reps' in data:
            exercise.rest_pause_reps = data['rest_pause_reps']
        if 'sets' in data:
            exercise.sets = data['sets']
        if 'target_muscle' in data:
            exercise.target_muscle = data['target_muscle']
        if 'notes' in data:
            exercise.notes = data['notes']
        
        db.session.commit()
        
        log_event("update_exercise", data={"exercise_id": exercise_id, "updated_fields": list(data.keys())})
        
        return jsonify({
            "status": "success",
            "message": "Exercise updated successfully",
            "exercise_id": exercise_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        log_event("update_exercise", error=error_msg, status="error")
        return jsonify({"error": error_msg}), 500

@app.route('/api/workout/exercise/<int:exercise_id>', methods=['DELETE'])
def delete_exercise(exercise_id):
    """個別エクササイズを削除"""
    try:
        exercise = WorkoutLog.query.get_or_404(exercise_id)
        
        log_event("delete_exercise", data={
            "exercise_id": exercise_id,
            "exercise_name": exercise.exercise_name,
            "session_id": exercise.session_id
        })
        
        db.session.delete(exercise)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Exercise deleted successfully",
            "exercise_id": exercise_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        log_event("delete_exercise", error=error_msg, status="error")
        return jsonify({"error": error_msg}), 500

def create_excel_export():
    """筋トレログをExcel形式で出力"""
    try:
        # 全セッションとエクササイズを取得（日付順）
        sessions = WorkoutSession.query.order_by(WorkoutSession.date.asc()).all()
        
        # Excelワークブックを作成
        wb = Workbook()
        ws = wb.active
        ws.title = "筋トレログ"
        
        # ヘッダー行の設定（元のExcelファイルと同じ構造）
        headers = [
            "日付", "曜日", "施設名", "種目", "種別", 
            "重量(kg)", "回数(rep)", "レストレップ", "セット数", "部位", "備考"
        ]
        
        # ヘッダースタイル設定
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # ヘッダー行を設定
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # データ行を追加
        row_num = 2
        for session in sessions:
            for exercise in session.workout_logs:
                # レストレップ回数の表示形式
                rest_pause_display = ""
                if exercise.rest_pause_reps and exercise.rest_pause_reps > 0:
                    rest_pause_display = str(exercise.rest_pause_reps)
                
                # データ行
                data_row = [
                    session.date.strftime('%Y/%m/%d'),  # 日付
                    session.day_of_week or "",          # 曜日
                    session.facility or "",             # 施設名
                    exercise.exercise_name or "",       # 種目
                    exercise.exercise_category or "",   # 種別
                    exercise.weight or "",              # 重量(kg)
                    exercise.reps or "",                # 回数(rep)
                    rest_pause_display,                 # レストレップ
                    exercise.sets or "",                # セット数
                    exercise.target_muscle or "",       # 部位
                    exercise.notes or ""                # 備考
                ]
                
                for col_num, value in enumerate(data_row, 1):
                    ws.cell(row=row_num, column=col_num, value=value)
                
                row_num += 1
        
        # 列幅の自動調整
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # 最大50文字
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Excelファイルをメモリに保存
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        return excel_buffer
        
    except Exception as e:
        raise Exception(f"Excel export error: {str(e)}")

@app.route('/api/export/excel', methods=['GET'])
def export_excel():
    """筋トレログをExcelファイルでダウンロード"""
    try:
        # Excelファイルを生成
        excel_buffer = create_excel_export()
        
        # ファイル名生成（現在の日時）
        filename = f"workout_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # ダウンロード用レスポンスを作成
        response = make_response(excel_buffer.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        # ログ記録
        log_event("export_excel", data={"filename": filename})
        
        return response
        
    except Exception as e:
        error_msg = str(e)
        log_event("export_excel", error=error_msg, status="error")
        return jsonify({"error": error_msg}), 500

@app.route('/workouts')
def view_workouts():
    """筋トレログの一覧表示"""
    try:
        sessions = WorkoutSession.query.order_by(WorkoutSession.date.desc()).limit(30).all()
        
        sessions_data = []
        for session in sessions:
            session_data = {
                'id': session.id,
                'date': session.date.strftime('%Y-%m-%d'),
                'day_of_week': session.day_of_week,
                'facility': session.facility,
                'exercises': []
            }
            
            for log in session.workout_logs:
                exercise_data = {
                    'id': log.id,
                    'name': log.exercise_name,
                    'category': log.exercise_category,
                    'weight': log.weight,
                    'reps': log.reps,
                    'rest_pause_reps': log.rest_pause_reps,
                    'sets': log.sets,
                    'target_muscle': log.target_muscle,
                    'notes': log.notes
                }
                session_data['exercises'].append(exercise_data)
            
            sessions_data.append(session_data)
        
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>筋トレログ - GPTs Action Test</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                .session { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; border-left: 4px solid #4CAF50; position: relative; }
                .session-header { background: #f8f9fa; padding: 15px; margin: -20px -20px 15px -20px; border-radius: 8px 8px 0 0; }
                .session-date { font-size: 1.2em; font-weight: bold; color: #2c3e50; }
                .session-info { color: #666; margin-top: 5px; }
                .exercise { margin: 10px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; position: relative; }
                .exercise-header { font-weight: bold; color: #34495e; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
                .exercise-details { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; font-size: 0.9em; }
                .detail-item { background: white; padding: 8px; border-radius: 3px; }
                .detail-label { font-weight: bold; color: #7f8c8d; }
                .detail-value { color: #2c3e50; }
                .notes { margin-top: 10px; padding: 10px; background: #fff3cd; border-radius: 3px; font-style: italic; }
                .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; display: inline-block; margin: 5px; border: none; cursor: pointer; }
                .button:hover { background: #005a8b; }
                .button-small { padding: 5px 10px; font-size: 0.8em; margin: 2px; }
                .button-edit { background: #28a745; }
                .button-edit:hover { background: #218838; }
                .button-delete { background: #dc3545; }
                .button-delete:hover { background: #c82333; }
                .session-delete { position: absolute; top: 15px; right: 15px; }
                .exercise-actions { display: flex; gap: 5px; }
                .reps-display { font-weight: bold; }
                .rest-pause { color: #e74c3c; }
                .nav-buttons { margin-bottom: 20px; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
                .stat-value { font-size: 1.5em; font-weight: bold; color: #2c3e50; }
                .stat-label { color: #7f8c8d; margin-top: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>筋トレログ</h1>
                
                <div class="nav-buttons">
                    <a href="/" class="button">← ホームに戻る</a>
                    <a href="/workouts/weekly" class="button">週次サマリ</a>
                    <a href="/workouts/monthly" class="button">月次サマリ</a>
                    <a href="/logs" class="button">システムログ</a>
                    <a href="/api/export/excel" class="button" style="background: #28a745;">📊 Excelダウンロード</a>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">{{ sessions_data|length }}</div>
                        <div class="stat-label">最近のセッション数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ total_exercises }}</div>
                        <div class="stat-label">総エクササイズ数</div>
                    </div>
                </div>
                
                {% for session in sessions_data %}
                <div class="session" id="session-{{ session.id }}">
                    <button class="button button-small button-delete session-delete" onclick="deleteSession({{ session.id }})">セッション削除</button>
                    <div class="session-header">
                        <div class="session-date">{{ session.date }} ({{ session.day_of_week }})</div>
                        <div class="session-info">
                            {% if session.facility %}施設: {{ session.facility }}{% endif %}
                            | エクササイズ数: {{ session.exercises|length }}
                        </div>
                    </div>
                    
                    {% for exercise in session.exercises %}
                    <div class="exercise" id="exercise-{{ exercise.id }}">
                        <div class="exercise-header">
                            <span>{{ exercise.name }}</span>
                            <div class="exercise-actions">
                                <button class="button button-small button-edit" onclick="editExercise({{ exercise.id }})">編集</button>
                                <button class="button button-small button-delete" onclick="deleteExercise({{ exercise.id }})">削除</button>
                            </div>
                        </div>
                        <div class="exercise-details">
                            {% if exercise.category %}
                            <div class="detail-item">
                                <div class="detail-label">種別</div>
                                <div class="detail-value">{{ exercise.category }}</div>
                            </div>
                            {% endif %}
                            {% if exercise.weight %}
                            <div class="detail-item">
                                <div class="detail-label">重量</div>
                                <div class="detail-value">{{ exercise.weight }}</div>
                            </div>
                            {% endif %}
                            <div class="detail-item">
                                <div class="detail-label">回数</div>
                                <div class="detail-value reps-display">
                                    {{ exercise.reps }}回
                                    {% if exercise.rest_pause_reps > 0 %}
                                    <span class="rest-pause">+ {{ exercise.rest_pause_reps }}回</span>
                                    {% endif %}
                                </div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">セット数</div>
                                <div class="detail-value">{{ exercise.sets }}セット</div>
                            </div>
                            {% if exercise.target_muscle %}
                            <div class="detail-item">
                                <div class="detail-label">対象筋肉</div>
                                <div class="detail-value">{{ exercise.target_muscle }}</div>
                            </div>
                            {% endif %}
                        </div>
                        {% if exercise.notes %}
                        <div class="notes">{{ exercise.notes }}</div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p>まだ筋トレログがありません。</p>
                {% endfor %}
            </div>
            
            <script>
            function deleteSession(sessionId) {
                if (confirm('このセッション全体を削除しますか？')) {
                    fetch(`/api/workout/${sessionId}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            document.getElementById(`session-${sessionId}`).remove();
                            alert('セッションを削除しました');
                            location.reload();
                        } else {
                            alert('削除に失敗しました: ' + data.error);
                        }
                    })
                    .catch(error => {
                        alert('エラーが発生しました: ' + error);
                    });
                }
            }
            
            function deleteExercise(exerciseId) {
                if (confirm('このエクササイズを削除しますか？')) {
                    fetch(`/api/workout/exercise/${exerciseId}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            document.getElementById(`exercise-${exerciseId}`).remove();
                            alert('エクササイズを削除しました');
                        } else {
                            alert('削除に失敗しました: ' + data.error);
                        }
                    })
                    .catch(error => {
                        alert('エラーが発生しました: ' + error);
                    });
                }
            }
            
            function editExercise(exerciseId) {
                const newReps = prompt('新しい回数を入力してください:');
                if (newReps !== null && newReps !== '') {
                    const updateData = { reps: parseInt(newReps) };
                    
                    fetch(`/api/workout/exercise/${exerciseId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(updateData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            alert('エクササイズを更新しました');
                            location.reload();
                        } else {
                            alert('更新に失敗しました: ' + data.error);
                        }
                    })
                    .catch(error => {
                        alert('エラーが発生しました: ' + error);
                    });
                }
            }
            </script>
        </body>
        </html>
        '''
        
        total_exercises = sum(len(session['exercises']) for session in sessions_data)
        return render_template_string(html, sessions_data=sessions_data, total_exercises=total_exercises)
        
    except Exception as e:
        return f"エラーが発生しました: {str(e)}", 500

@app.route('/workouts/weekly')
def view_weekly_summary():
    """週次サマリ表示"""
    try:
        from sqlalchemy import func, text
        
        # 過去8週間のデータを取得
        weekly_data = db.session.query(
            func.date_trunc('week', WorkoutSession.date).label('week_start'),
            func.count(WorkoutSession.id).label('session_count'),
            func.count(WorkoutLog.id).label('exercise_count')
        ).join(WorkoutLog).group_by(
            func.date_trunc('week', WorkoutSession.date)
        ).order_by(
            func.date_trunc('week', WorkoutSession.date).desc()
        ).limit(8).all()
        
        # 筋肉部位別の週次統計
        muscle_stats = db.session.query(
            WorkoutLog.target_muscle,
            func.count(WorkoutLog.id).label('exercise_count'),
            func.date_trunc('week', WorkoutSession.date).label('week_start')
        ).join(WorkoutSession).filter(
            WorkoutLog.target_muscle.isnot(None)
        ).group_by(
            WorkoutLog.target_muscle,
            func.date_trunc('week', WorkoutSession.date)
        ).order_by(
            func.date_trunc('week', WorkoutSession.date).desc()
        ).limit(50).all()
        
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>週次サマリ - 筋トレログ</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                .week-summary { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; border-left: 4px solid #2196F3; }
                .week-header { font-size: 1.2em; font-weight: bold; color: #2c3e50; margin-bottom: 15px; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
                .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
                .stat-value { font-size: 1.5em; font-weight: bold; color: #2c3e50; }
                .stat-label { color: #7f8c8d; margin-top: 5px; font-size: 0.9em; }
                .muscle-stats { margin-top: 15px; }
                .muscle-item { display: inline-block; background: #e3f2fd; padding: 5px 10px; margin: 3px; border-radius: 15px; font-size: 0.9em; }
                .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; display: inline-block; margin: 5px; }
                .button:hover { background: #005a8b; }
                .nav-buttons { margin-bottom: 20px; }
                .chart-container { background: white; padding: 20px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>週次サマリ</h1>
                
                <div class="nav-buttons">
                    <a href="/workouts" class="button">← ワークアウト一覧</a>
                    <a href="/workouts/monthly" class="button">月次サマリ</a>
                    <a href="/" class="button">ホーム</a>
                </div>
                
                {% for week in weekly_data %}
                <div class="week-summary">
                    <div class="week-header">{{ week.week_start.strftime('%Y年%m月%d日') }}の週</div>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{{ week.session_count }}</div>
                            <div class="stat-label">トレーニング日数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ week.exercise_count }}</div>
                            <div class="stat-label">総エクササイズ数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ "%.1f"|format(week.exercise_count / week.session_count if week.session_count > 0 else 0) }}</div>
                            <div class="stat-label">1日平均エクササイズ数</div>
                        </div>
                    </div>
                    
                    <div class="muscle-stats">
                        <strong>対象筋肉:</strong>
                        {% for muscle in muscle_stats %}
                            {% if muscle.week_start == week.week_start %}
                            <span class="muscle-item">{{ muscle.target_muscle }} ({{ muscle.exercise_count }}回)</span>
                            {% endif %}
                        {% endfor %}
                    </div>
                </div>
                {% else %}
                <p>まだ週次データがありません。</p>
                {% endfor %}
            </div>
        </body>
        </html>
        '''
        
        return render_template_string(html, weekly_data=weekly_data, muscle_stats=muscle_stats)
        
    except Exception as e:
        return f"エラーが発生しました: {str(e)}", 500

@app.route('/workouts/monthly')
def view_monthly_summary():
    """月次サマリ表示"""
    try:
        from sqlalchemy import func, extract
        
        # 過去6ヶ月のデータを取得
        monthly_data = db.session.query(
            extract('year', WorkoutSession.date).label('year'),
            extract('month', WorkoutSession.date).label('month'),
            func.count(WorkoutSession.id).label('session_count'),
            func.count(WorkoutLog.id).label('exercise_count'),
            func.count(func.distinct(WorkoutLog.exercise_name)).label('unique_exercises')
        ).join(WorkoutLog).group_by(
            extract('year', WorkoutSession.date),
            extract('month', WorkoutSession.date)
        ).order_by(
            extract('year', WorkoutSession.date).desc(),
            extract('month', WorkoutSession.date).desc()
        ).limit(6).all()
        
        # 月別の筋肉部位統計
        monthly_muscle_stats = db.session.query(
            extract('year', WorkoutSession.date).label('year'),
            extract('month', WorkoutSession.date).label('month'),
            WorkoutLog.target_muscle,
            func.count(WorkoutLog.id).label('exercise_count')
        ).join(WorkoutSession).filter(
            WorkoutLog.target_muscle.isnot(None)
        ).group_by(
            extract('year', WorkoutSession.date),
            extract('month', WorkoutSession.date),
            WorkoutLog.target_muscle
        ).order_by(
            extract('year', WorkoutSession.date).desc(),
            extract('month', WorkoutSession.date).desc(),
            func.count(WorkoutLog.id).desc()
        ).all()
        
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>月次サマリ - 筋トレログ</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                .month-summary { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; border-left: 4px solid #FF9800; }
                .month-header { font-size: 1.3em; font-weight: bold; color: #2c3e50; margin-bottom: 15px; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 15px; }
                .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
                .stat-value { font-size: 1.5em; font-weight: bold; color: #2c3e50; }
                .stat-label { color: #7f8c8d; margin-top: 5px; font-size: 0.9em; }
                .muscle-stats { margin-top: 15px; }
                .muscle-item { display: inline-block; background: #fff3e0; padding: 5px 10px; margin: 3px; border-radius: 15px; font-size: 0.9em; }
                .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; display: inline-block; margin: 5px; }
                .button:hover { background: #005a8b; }
                .nav-buttons { margin-bottom: 20px; }
                .progress-bar { background: #e0e0e0; height: 10px; border-radius: 5px; margin: 10px 0; }
                .progress-fill { background: #4CAF50; height: 100%; border-radius: 5px; transition: width 0.3s ease; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>月次サマリ</h1>
                
                <div class="nav-buttons">
                    <a href="/workouts" class="button">← ワークアウト一覧</a>
                    <a href="/workouts/weekly" class="button">週次サマリ</a>
                    <a href="/" class="button">ホーム</a>
                </div>
                
                {% for month in monthly_data %}
                <div class="month-summary">
                    <div class="month-header">{{ month.year }}年{{ month.month }}月</div>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{{ month.session_count }}</div>
                            <div class="stat-label">トレーニング日数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ month.exercise_count }}</div>
                            <div class="stat-label">総エクササイズ数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ month.unique_exercises }}</div>
                            <div class="stat-label">ユニーク種目数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{{ "%.1f"|format(month.exercise_count / month.session_count if month.session_count > 0 else 0) }}</div>
                            <div class="stat-label">1日平均エクササイズ数</div>
                        </div>
                    </div>
                    
                    <div class="muscle-stats">
                        <strong>主要対象筋肉 TOP5:</strong>
                        {% set month_muscles = [] %}
                        {% for muscle in monthly_muscle_stats %}
                            {% if muscle.year == month.year and muscle.month == month.month %}
                                {% set _ = month_muscles.append(muscle) %}
                            {% endif %}
                        {% endfor %}
                        {% for muscle in month_muscles[:5] %}
                        <span class="muscle-item">{{ muscle.target_muscle }} ({{ muscle.exercise_count }}回)</span>
                        {% endfor %}
                    </div>
                </div>
                {% else %}
                <p>まだ月次データがありません。</p>
                {% endfor %}
            </div>
        </body>
        </html>
        '''
        
        return render_template_string(html, monthly_data=monthly_data, monthly_muscle_stats=monthly_muscle_stats)
        
    except Exception as e:
        return f"エラーが発生しました: {str(e)}", 500

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
            <p><a href="/" class="button">← ホームに戻る</a> <a href="/data" class="button">受信データを見る</a> <a href="/conversations" class="button">会話データを見る</a></p>
            
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
            <p><a href="/" class="button">← ホームに戻る</a> <a href="/logs" class="button">処理ログを見る</a> <a href="/conversations" class="button">会話データを見る</a></p>
            
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

@app.route('/conversations')
def view_conversations():
    """会話データの表示"""
    conversations = []
    if CONVERSATIONS_FILE.exists():
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
        except:
            conversations = []
    
    # 最新の会話から表示
    conversations.reverse()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>会話データ - GPTs Action Test</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .conversation-entry { margin: 15px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; border-left: 4px solid #9C27B0; }
            .timestamp { color: #666; font-size: 0.9em; margin-bottom: 10px; }
            .conversation-id { color: #9C27B0; font-weight: bold; margin-bottom: 10px; }
            .section { margin: 10px 0; }
            .section-title { font-weight: bold; color: #333; margin-bottom: 5px; }
            .user-input { background: #e3f2fd; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .assistant-response { background: #f3e5f5; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .summary { background: #fff3e0; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .topics { background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 5px 0; }
            .sentiment { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; }
            .sentiment-positive { background: #4CAF50; color: white; }
            .sentiment-negative { background: #f44336; color: white; }
            .sentiment-neutral { background: #757575; color: white; }
            .metadata { background: #f5f5f5; padding: 10px; border-radius: 5px; margin: 5px 0; font-family: monospace; font-size: 0.9em; }
            .button { background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 3px; display: inline-block; margin: 5px; }
            .button:hover { background: #005a8b; }
            .tags { margin: 5px 0; }
            .tag { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; margin-right: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>会話データ</h1>
            <p><a href="/" class="button">← ホームに戻る</a> <a href="/logs" class="button">処理ログを見る</a> <a href="/data" class="button">受信データを見る</a></p>
            
            {% if conversations %}
                {% for conversation in conversations %}
                <div class="conversation-entry">
                    <div class="timestamp">記録時刻: {{ conversation.timestamp }}</div>
                    <div class="conversation-id">会話ID: {{ conversation.conversation_id }}</div>
                    
                    {% if conversation.data.user_input %}
                    <div class="section">
                        <div class="section-title">ユーザー入力:</div>
                        <div class="user-input">{{ conversation.data.user_input }}</div>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.assistant_response %}
                    <div class="section">
                        <div class="section-title">アシスタント回答:</div>
                        <div class="assistant-response">{{ conversation.data.assistant_response }}</div>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.conversation_summary %}
                    <div class="section">
                        <div class="section-title">会話要約:</div>
                        <div class="summary">{{ conversation.data.conversation_summary }}</div>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.key_topics %}
                    <div class="section">
                        <div class="section-title">主要トピック:</div>
                        <div class="topics tags">
                            {% for topic in conversation.data.key_topics %}
                            <span class="tag">{{ topic }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.sentiment %}
                    <div class="section">
                        <div class="section-title">感情傾向:</div>
                        <span class="sentiment sentiment-{{ conversation.data.sentiment }}">{{ conversation.data.sentiment }}</span>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.category %}
                    <div class="section">
                        <div class="section-title">カテゴリ:</div>
                        <span class="tag">{{ conversation.data.category }}</span>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.action_items %}
                    <div class="section">
                        <div class="section-title">アクションアイテム:</div>
                        <ul>
                            {% for item in conversation.data.action_items %}
                            <li>{{ item }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.entities %}
                    <div class="section">
                        <div class="section-title">抽出エンティティ:</div>
                        <div class="tags">
                            {% for entity in conversation.data.entities %}
                            <span class="tag">{{ entity.type }}: {{ entity.value }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                    
                    {% if conversation.data.metadata %}
                    <div class="section">
                        <div class="section-title">メタデータ:</div>
                        <div class="metadata">{{ conversation.data.metadata | tojson(indent=2) }}</div>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
                <p>まだ会話データがありません。</p>
            {% endif %}
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, conversations=conversations)

def create_tables():
    """データベーステーブルを作成"""
    with app.app_context():
        db.create_all()

# アプリケーション起動時にテーブル作成
create_tables()

if __name__ == '__main__':
    log_event("app_start", data={"message": "Application started"})
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)