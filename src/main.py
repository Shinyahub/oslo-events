"""
オスロ周辺イベント週次メール配信 - メインスクリプト

実行:
  python -m src.main

環境変数（GitHub Secrets に設定）:
  TICKETMASTER_API_KEY  - Ticketmaster Discovery API キー（省略可）
  ANTHROPIC_API_KEY     - Claude API キー
  GMAIL_USER            - Gmailアドレス
  GMAIL_APP_PASSWORD    - Googleアプリパスワード
  RECIPIENTS            - 送信先メールアドレス（カンマ区切り）
  WEEKS_AHEAD           - 何週間先まで収集するか（デフォルト: 3）
"""

import logging
import os
import sys

from src.collectors import collect_all_events
from src.mailer import build_subject, send_email
from src.summarizer import summarize_events_with_claude

# ──────────────────────────────────────────
# ロギング設定
# ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> None:
    # ── 環境変数の読み込み ──
    ticketmaster_key = os.environ.get("TICKETMASTER_API_KEY")  # オプション
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipients_raw = os.environ.get("RECIPIENTS", "")
    weeks_ahead = int(os.environ.get("WEEKS_AHEAD", "3"))

    # ── バリデーション ──
    missing = []
    if not anthropic_key:
        missing.append("ANTHROPIC_API_KEY")
    if not gmail_user:
        missing.append("GMAIL_USER")
    if not gmail_password:
        missing.append("GMAIL_APP_PASSWORD")
    if not recipients_raw:
        missing.append("RECIPIENTS")
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    # ── Step 1: イベント収集 ──
    logger.info("=== Step 1: Collecting events from all sources ===")
    events = collect_all_events(
        ticketmaster_api_key=ticketmaster_key,
        weeks_ahead=weeks_ahead,
    )

    if not events:
        logger.warning("No events collected. Sending empty report.")

    # ── Step 2: Claude APIでサマリー生成 ──
    logger.info(f"=== Step 2: Summarizing {len(events)} events with Claude ===")
    summary = summarize_events_with_claude(
        events=events,
        anthropic_api_key=anthropic_key,
    )

    # ── Step 3: メール送信 ──
    logger.info("=== Step 3: Sending email ===")
    subject = build_subject(len(events))
    success = send_email(
        gmail_user=gmail_user,
        gmail_app_password=gmail_password,
        recipients=recipients,
        subject=subject,
        text_body=summary,
        event_count=len(events),
    )

    if success:
        logger.info("✅ Weekly event email sent successfully!")
    else:
        logger.error("❌ Email sending failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
