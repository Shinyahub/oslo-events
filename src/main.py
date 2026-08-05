"""
メインスクリプト（メール配信 + Web用JSON書き出し）
"""

import logging
import os
import sys

from src.collectors import collect_all_events
from src.export_json import export_events_to_json
from src.mailer import build_subject, send_email
from src.summarizer import summarize_events_with_claude

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> None:
    ticketmaster_key = os.environ.get("TICKETMASTER_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipients_raw = os.environ.get("RECIPIENTS", "")
    weeks_ahead = int(os.environ.get("WEEKS_AHEAD", "4"))

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

    # Step 1: イベント収集
    logger.info("=== Step 1: Collecting events ===")
    events = collect_all_events(
        ticketmaster_api_key=ticketmaster_key,
        weeks_ahead=weeks_ahead,
    )

    # Step 2: Web用JSONに書き出し（GitHub Pagesで表示）
    logger.info("=== Step 2: Exporting events.json for GitHub Pages ===")
    export_events_to_json(events, output_path="docs/events.json")

    # Step 3: Claude APIでメール用サマリー生成
    logger.info(f"=== Step 3: Summarizing {len(events)} events with Claude ===")
    summary = summarize_events_with_claude(
        events=events,
        anthropic_api_key=anthropic_key,
    )

    # Step 4: メール送信
    logger.info("=== Step 4: Sending email ===")
    subject = build_subject(len(events))
    send_email(
        gmail_user=gmail_user,
        gmail_app_password=gmail_password,
        recipients=recipients,
        subject=subject,
        text_body=summary,
        event_count=len(events),
    )

    logger.info("✅ Done!")


if __name__ == "__main__":
    main()
