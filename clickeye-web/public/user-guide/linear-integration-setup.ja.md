---
title: Linear 連携設定
description: Linear API キーの登録、Webhook 設定、DayQueued フローまでステップごとに案内します。
order: 5
---

# Linear 連携設定

ClickEye の AI Team が生成したサブタスクを Linear イシューとして自動登録し、イシューの状態が `Queued` に変更されると、ローカルの Claude Code が自動で開発を開始する一連の流れを設定します。

---

## 全体の流れ

```
[ClickEye AI Team] AI ドラフト生成
         │ → Linear イシュー自動登録
         ▼
[Linear] イシュー状態 → Queued に変更
         │
         ▼
[ローカル PC] Webhook 受信またはポーリング
         │
         ▼
[Claude Code] 自動開発パイプライン実行
```

---

## Step 1 — Linear API キーの発行

1. [https://linear.app/settings/api](https://linear.app/settings/api) にアクセス
2. **Personal API keys → Create key** をクリック
3. 名前を入力（例: `ClickEye`）
4. 権限: **Full access** または最小限の `issues:write`
5. 発行されたキー（`lin_api_...`）をコピーします

---

## Step 2 — Linear チーム ID の確認

Linear の **チーム ID** が必要です。次の方法で確認してください:

- Linear アプリ → 左サイドバーでチーム名を右クリック → **Copy Team ID**
- または URL で確認: `https://linear.app/{workspace}/team/{TEAM_ID}/issues`

---

## Step 3 — ClickEye 設定ページで保存

1. [ClickEye 設定 → Linear](https://app.24sevenclaw.com/settings/linear) にアクセス
2. 次の項目を入力します:

| フィールド | 説明 | 必須 |
|------|------|------|
| Linear API Key | `lin_api_...` 形式 | ✅ |
| Team ID | イシューを作成するチームの UUID | ✅ |
| Webhook Secret | HMAC 署名検証用の任意の文字列 | ⬜ |
| Tunnel URL | ローカル webhook サーバーの公開 URL | ⬜ |

3. **保存** をクリック

> **セキュリティのヒント**: Webhook Secret には `openssl rand -hex 32` で生成した強力なランダム文字列を使用してください。

> **Tunnel URL を保存する場合**: サーバーが自動で Linear ワークスペースに Webhook を登録します。

---

## Step 4 — ウィザードで Linear スキルを選択（ZIP 生成時）

7-Step ウィザードの Step 5（エージェント & スキル）で **Linear** スキルを選択すると、ZIP に Linear 連携スクリプトが含まれます。

ZIP の解凍後、`.env` ファイルに次の値が必要です:

```bash
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-uuid
WEBHOOK_SECRET=your-webhook-secret
TUNNEL_PROVIDER=cloudflare   # cloudflare | ngrok | polling
```

---

## Step 5 — リアルタイムトラッキング方式の選択

### 方式 A: Cloudflare Tunnel（推奨）

無料で静的 URL を提供します。

```bash
bash scripts/setup-tunnel.sh
```

スクリプト実行時:
1. `cloudflared` が自動でインストールされます（Homebrew / apt / snap）
2. トンネルが起動し、`https://xxxx.trycloudflare.com` の URL が発行されます
3. `.env` の `WEBHOOK_PUBLIC_URL` が自動で更新されます

発行された URL を、[ClickEye 設定ページ](https://app.24sevenclaw.com/settings/linear)の **Tunnel URL** フィールドに保存してください。

> ⚠️ このターミナルウィンドウを閉じるとトンネルが終了します。バックグラウンド実行: `nohup bash scripts/setup-tunnel.sh &`

### 方式 B: ngrok

```bash
TUNNEL_PROVIDER=ngrok bash scripts/setup-tunnel.sh
```

- 無料プラン: 再起動のたびに URL が変更されます。URL 変更時は設定ページで再保存が必要です
- 有料の固定 URL: `NGROK_AUTH_TOKEN` を `.env` に設定すると自動で認証されます

### 方式 C: 30秒ポーリング（トンネルなし）

Webhook なしで 30 秒ごとに Linear をポーリングします。トンネル設定が難しい環境に適しています。

```bash
python scripts/linear_watcher.py
```

バックグラウンド実行:

```bash
python scripts/linear_watcher.py &
```

---

## Step 6 — ローカル Webhook サーバーの起動（Cloudflare/ngrok 方式）

新しいターミナルで実行します:

```bash
bash scripts/start-webhook.sh
```

ヘルスチェック:

```bash
curl http://localhost:9876/health
# {"status":"ok","port":9876}
```

---

## Step 7 — DayQueued フローの確認

すべての設定が完了すると、次のフローで自動開発がトリガーされます:

1. ClickEye AI Team → **AI ドラフト生成** をクリック
2. Linear にイシューが自動で登録されます（例: `24S-123`）
3. Linear でイシューの状態を **Queued**（または `DayQueued`、`NightQueued`）に変更します
4. ローカル環境でパイプラインが自動で実行されます:

   - **Webhook モード**: `start-webhook.sh` のターミナルで確認
     ```
     [ClickEye] Linear webhook 受信: イシュー 24S-123 → Queued
     [ClickEye] 自動開発パイプラインをトリガー
     ```
   - **ポーリングモード**: `linear_watcher.py` のターミナルで確認
     ```
     [watcher] イシューを検出: 24S-123 (Queued) → パイプライン実行
     ```

---

## トラブルシューティング

| 症状 | 原因 | 解決方法 |
|------|------|----------|
| 「Linear の認証情報がありません」バナー | API キー未保存 | 設定ページで API キーを保存 |
| Linear イシューの生成失敗 | API キーの期限切れまたは権限不足 | 新しいキーを発行して再保存 |
| Webhook を受信しない | Tunnel URL の不一致 | 設定ページで現在の Tunnel URL を再保存 |
| 署名検証の失敗（401） | Webhook Secret の不一致 | `.env` と設定ページの Secret が同一か確認 |
| `cloudflared` のインストール失敗 | インターネット接続または権限の問題 | [手動インストールガイド](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| ngrok URL の変更 | 無料プランの再起動 | 設定ページで新しい URL を再保存、または有料プランを使用 |
| ポーリングがイシューを検出しない | `LINEAR_TEAM_ID` の誤り | `.env` の TEAM_ID が正しいか Linear で確認 |

---

## セキュリティチェックリスト

- [ ] Linear API キーが `.env` のみにあり、Git にコミットされていないか？（`.gitignore` を確認）
- [ ] Webhook Secret は十分に強力か？（`openssl rand -hex 32` を推奨）
- [ ] `start-webhook.sh` がローカルホストでのみ受信しているか？（ポート 9876 の外部公開は不要）
- [ ] Cloudflare/ngrok トンネルがポート 9876 のみを公開しているか？

---

## 関連ガイド

- [7-Step ソリューションウィザード](/guide/wizard-7-step) — ウィザードで Linear スキルを選択する
- [AI Team 管理](/guide/ai-team-management) — AI ドラフト生成および Linear イシューの確認
