# Open Close Map Backend

Render用の最小バックエンドです。

## Render設定

- Service Type: Web Service
- Root Directory: `backend`
- Language: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## 環境変数

PostgreSQLを接続したら、RenderのEnvironmentに以下を追加します。

- `DATABASE_URL` = Render PostgreSQLのInternal Database URL

未設定でもAPI自体は起動しますが、DB系APIは空データを返します。

## 確認URL

- `/`
- `/health`
- `/api/stats`
- `/api/stores`

## 次の段階

1. PostgreSQL接続
2. 自動収集collector追加
3. 重複排除
4. 情報確度スコア
5. Static SiteからAPIを呼び出して実データ表示
