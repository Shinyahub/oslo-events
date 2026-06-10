# 🇳🇴 Oslo Events Weekly Mailer

オスロ周辺（ヨーテボリ・クリスチャンサン含む）のイベント情報を毎週自動収集し、
Claude AIが日本語サマリーにしてメールで届けるシステムです。

## 収集ソース

| ソース | 内容 |
|--------|------|
| Ticketmaster API | コンサート・スポーツ・ライブ全般 |
| VisitOslo.com | オスロ公式観光サイトのイベント |
| VisitNorway.com | ノルウェー全土のイベント |
| Billettservice.no | ノルウェーの主要チケットサービス |

---

## セットアップ手順

### 1. リポジトリをフォーク or クローン

```bash
git clone https://github.com/あなたのユーザー名/oslo-events-mailer.git
cd oslo-events-mailer
```

### 2. GitHub Secrets の設定

GitHubリポジトリの **Settings → Secrets and variables → Actions** で以下を追加：

| Secret名 | 内容 | 取得方法 |
|----------|------|----------|
| `ANTHROPIC_API_KEY` | Claude APIキー | [console.anthropic.com](https://console.anthropic.com) |
| `GMAIL_USER` | GmailアドレスEX: you@gmail.com | Gmailアカウント |
| `GMAIL_APP_PASSWORD` | Googleアプリパスワード（16文字） | 下記参照 |
| `RECIPIENTS` | 送信先メール（カンマ区切り可）EX: a@b.com,c@d.com | 自分のアドレス等 |
| `TICKETMASTER_API_KEY` | Ticketmaster APIキー（省略可） | [developer.ticketmaster.com](https://developer.ticketmaster.com) |

### 3. Googleアプリパスワードの取得

1. Googleアカウント → **セキュリティ** → **2段階認証プロセス** を有効化
2. **アプリパスワード** → アプリ名「oslo-events」などで作成
3. 生成された16文字を `GMAIL_APP_PASSWORD` に設定

### 4. Ticketmaster APIキー（任意・無料）

1. [developer.ticketmaster.com](https://developer.ticketmaster.com) でアカウント作成
2. 「Get API Key」→ Consumer Key をコピー
3. `TICKETMASTER_API_KEY` に設定（設定しなくてもスクレイピングのみで動作）

---

## 実行スケジュール

**毎週月曜日 朝7時（日本時間）** に自動実行されます。

cronを変更する場合は `.github/workflows/weekly_events.yml` を編集：
```yaml
schedule:
  - cron: "0 22 * * 0"  # UTC日曜22時 = JST月曜7時
```

---

## 手動テスト実行

GitHub の **Actions タブ → 週次オスロイベントメール配信 → Run workflow** で手動実行できます。

ローカルでテストする場合：

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY="your-key"
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export RECIPIENTS="you@gmail.com"
# export TICKETMASTER_API_KEY="your-tm-key"  # 省略可

python -m src.main
```

---

## ディレクトリ構成

```
oslo-events/
├── .github/
│   └── workflows/
│       └── weekly_events.yml   # GitHub Actions スケジュール
├── src/
│   ├── __init__.py
│   ├── main.py                 # エントリポイント
│   ├── collectors.py           # イベント収集（API + スクレイピング）
│   ├── summarizer.py           # Claude APIでAI要約
│   └── mailer.py               # Gmail SMTP送信
├── requirements.txt
└── README.md
```

---

## トラブルシューティング

### メールが届かない
- Gmailのアプリパスワードが正しいか確認（16文字、スペースなし）
- 「安全性の低いアプリのアクセス」ではなく必ずアプリパスワードを使用
- RECIPIENTSの形式: `user@example.com` または `a@b.com,c@d.com`

### イベントが0件
- スクレイピング先のサイト構造が変わった可能性があります
- `collectors.py` のCSSセレクタを更新してください
- Ticketmaster APIキーを設定すると安定して取得できます

### GitHub Actionsが動かない
- Actionsタブで有効化されているか確認
- Secretsがすべて正しく設定されているか確認
