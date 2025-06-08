# GPTsアクション設定ガイド

## 1. GPTsでアクションを追加

1. **ChatGPT**にアクセス → **GPTs**を選択
2. 既存のGPTsを編集、または新しいGPTsを作成
3. **Configure**タブ → **Actions**セクション
4. **Create new action**をクリック

## 2. スキーマを設定

`gpts-action-schema.json`の内容を**Schema**フィールドにコピー&ペースト

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "GPTs Action Test API",
    "description": "GPTsからJSONデータを受信・保存するためのテストAPI",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://gpts-action-test.onrender.com"
    }
  ],
  "paths": {
    "/api/receive": {
      "post": {
        "operationId": "receiveData",
        "summary": "GPTsからデータを受信",
        "description": "GPTsアクションからJSONデータを受信して保存します",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "message": {
                    "type": "string",
                    "description": "送信するメッセージ"
                  },
                  "user_id": {
                    "type": "string",
                    "description": "ユーザーID"
                  },
                  "action_type": {
                    "type": "string",
                    "description": "アクションの種類",
                    "enum": ["test", "data_send", "log", "notification"]
                  },
                  "data": {
                    "type": "object",
                    "description": "追加データ（任意の構造）",
                    "additionalProperties": true
                  },
                  "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "タイムスタンプ"
                  }
                },
                "required": ["message"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "データの受信に成功"
          }
        }
      }
    }
  }
}
```

## 3. アクションをテスト

1. **Test**ボタンをクリック
2. テストデータを入力:
   ```json
   {
     "message": "Hello from GPTs",
     "action_type": "test",
     "user_id": "test_user_001"
   }
   ```
3. **Test**実行

## 4. GPTsの指示文例

```
あなたは、ユーザーからの要求に応じてAPIにデータを送信するアシスタントです。

以下の場合にreceiveDataアクションを使用してください：
- ユーザーがデータの保存を依頼した場合
- ログやメッセージを記録する必要がある場合
- テストデータを送信する場合

送信するデータには必ず以下を含めてください：
- message: 何をしたかの説明
- action_type: アクションの種類（test, data_send, log, notification）
- user_id: 可能であればユーザーを識別する情報
- timestamp: 現在の日時

送信後は、APIからのレスポンスを用户に報告してください。
```

## 5. テスト用プロンプト

```
以下のデータをAPIに送信してテストしてください：
- メッセージ: "GPTsアクションのテスト"
- アクションタイプ: "test"
- ユーザーID: "demo_user"
- 追加データ: {"test_number": 1, "feature": "action_test"}
```

## 6. 結果確認

送信後、以下のURLで結果を確認：
- **ログ**: https://gpts-action-test.onrender.com/logs
- **データ**: https://gpts-action-test.onrender.com/data

## 7. 認証設定（オプション）

セキュリティが必要な場合：
- **Authentication**: API Key
- **Auth Type**: Bearer
- **API Key**: 独自のAPIキーを設定

## トラブルシューティング

**エラーが発生した場合：**
1. スキーマの構文をチェック
2. APIのURLが正しいか確認
3. render.comでアプリが起動しているか確認
4. ログページでエラーメッセージを確認