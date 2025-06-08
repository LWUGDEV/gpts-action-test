# GPTs Action Test Application

GPTsアクションからJSONデータを受信し、保存・参照できるWebアプリケーションです。

## 機能

- **JSONデータ受信**: `/api/receive` エンドポイントでGPTsからのPOSTリクエストを受信
- **データ保存**: 受信したJSONデータをファイルに保存
- **ログ管理**: すべての処理ログを記録・表示
- **Webインターface**: ブラウザで処理ログと受信データを確認可能

## エンドポイント

### POST /api/receive
GPTsアクションからJSONデータを受信するエンドポイント

**リクエスト例:**
```bash
curl -X POST https://your-app.onrender.com/api/receive \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "message": "Hello from GPTs"}'
```

**レスポンス例:**
```json
{
  "status": "success",
  "message": "Data received and saved",
  "timestamp": "2025-06-09T12:00:00.000000",
  "received_data": {
    "test": "data",
    "message": "Hello from GPTs"
  }
}
```

## Webページ

- `/` - メインページ（エンドポイント情報とナビゲーション）
- `/logs` - 処理ログの表示
- `/data` - 受信データの表示

## render.com デプロイ手順

1. GitHubリポジトリにコードをプッシュ
2. render.comで新しいWebサービスを作成
3. GitHubリポジトリを接続
4. 自動デプロイが実行される

## ローカル開発

```bash
pip install -r requirements.txt
python app.py
```

アプリケーションは http://localhost:5000 で起動します。

## データ保存

- `data/logs.json` - 処理ログ（最新100件）
- `data/received_data.json` - 受信データ（最新100件）