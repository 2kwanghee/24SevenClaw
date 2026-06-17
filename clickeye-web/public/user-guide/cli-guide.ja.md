---
title: CLI の使い方
description: ClickEye CLI ツールのインストールおよび主要コマンドを案内します。
order: 4
---

# CLI の使い方

ClickEye CLI は、パワーユーザー向けのコマンドラインインターフェースです。Web ダッシュボードと同一の生成エンジンを共有します。

## インストール

```bash
npm install -g @clickeye/cli
```

## 基本コマンド

```bash
# バージョン確認
clickeye --version

# ヘルプ
clickeye --help

# ログイン
clickeye login

# ソリューション生成
clickeye create

# ソリューション一覧
clickeye list
```

## ソリューション生成

```bash
# インタラクティブモードでソリューションを生成
clickeye create

# オプション指定
clickeye create --platform claude-code --stack nextjs
```

## 設定ファイル

CLI の設定は `~/.clickeye/config.json` に保存されます。

```json
{
  "apiUrl": "https://api.clickeye.io",
  "token": "your-api-token"
}
```

> 詳細な内容は今後アップデート予定です (24S-186)。
