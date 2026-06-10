"""
Gmail SMTP を使ったメール送信モジュール
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def build_html_email(text_body: str, event_count: int) -> str:
    """プレーンテキストのサマリーをHTML形式のメールに変換"""
    now = datetime.now()
    date_str = now.strftime("%Y年%m月%d日")

    # マークダウン的な書式をHTMLに変換
    lines = text_body.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("## ") or line.startswith("# "):
            content = line.lstrip("# ").strip()
            html_lines.append(f"<h2>{content}</h2>")
        elif line.startswith("### "):
            content = line.lstrip("# ").strip()
            html_lines.append(f"<h3>{content}</h3>")
        elif line.startswith("・") or line.startswith("- "):
            content = line.lstrip("・- ").strip()
            # URLをリンクに変換
            import re
            content = re.sub(
                r"(https?://[^\s]+)",
                r'<a href="\1" style="color:#0066cc;">\1</a>',
                content,
            )
            html_lines.append(f"<li>{content}</li>")
        elif line.startswith("→") or line.startswith("  →"):
            content = line.strip().lstrip("→ ")
            html_lines.append(
                f'<div style="margin-left:20px;font-size:0.85em;">'
                f'<a href="{content}" style="color:#0066cc;">🔗 詳細・チケット</a></div>'
            )
        elif line.strip() == "":
            html_lines.append("<br>")
        else:
            # 絵文字で始まるセクションヘッダっぽい行
            if any(line.startswith(e) for e in ["🎵", "🎪", "🏃", "🎨", "🎭", "✨", "📌"]):
                html_lines.append(f'<h3 style="color:#333;border-bottom:2px solid #eee;padding-bottom:4px;">{line}</h3>')
            else:
                html_lines.append(f"<p>{line}</p>")

    body_html = "\n".join(html_lines)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>オスロ周辺イベント情報</title>
</head>
<body style="font-family: 'Hiragino Sans', 'Meiryo', sans-serif; background:#f5f5f5; margin:0; padding:20px;">
  <div style="max-width:700px; margin:0 auto; background:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
    
    <!-- ヘッダー -->
    <div style="background:linear-gradient(135deg, #003087 0%, #0066cc 100%); padding:24px 32px; color:white;">
      <div style="font-size:12px; opacity:0.8; margin-bottom:4px;">🇳🇴 週次イベント情報</div>
      <h1 style="margin:0; font-size:22px; font-weight:bold;">オスロ周辺 イベントまとめ</h1>
      <div style="margin-top:8px; font-size:13px; opacity:0.9;">{date_str} 配信 ・ 今後3週間 ・ 計{event_count}件</div>
    </div>

    <!-- 本文 -->
    <div style="padding:24px 32px; line-height:1.8; color:#333; font-size:14px;">
      {body_html}
    </div>

    <!-- フッター -->
    <div style="background:#f9f9f9; border-top:1px solid #eee; padding:16px 32px; font-size:11px; color:#999; text-align:center;">
      このメールは自動送信されています。<br>
      情報ソース: Ticketmaster / VisitOslo / VisitNorway / Billettservice<br>
      イベント情報は変更になる場合があります。公式サイトでご確認ください。
    </div>
  </div>
</body>
</html>"""


def send_email(
    gmail_user: str,
    gmail_app_password: str,
    recipients: list[str],
    subject: str,
    text_body: str,
    event_count: int = 0,
) -> bool:
    """Gmail SMTPでHTMLメールを送信"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Oslo Events 🇳🇴 <{gmail_user}>"
    msg["To"] = ", ".join(recipients)

    # テキスト版（フォールバック）
    part_text = MIMEText(text_body, "plain", "utf-8")
    msg.attach(part_text)

    # HTML版
    html_body = build_html_email(text_body, event_count)
    part_html = MIMEText(html_body, "html", "utf-8")
    msg.attach(part_html)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, recipients, msg.as_bytes())
        logger.info(f"Email sent successfully to {recipients}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail authentication failed. Check App Password.")
        raise
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise


def build_subject(event_count: int) -> str:
    """件名を生成"""
    now = datetime.now()
    week_str = now.strftime("%m/%d")
    return f"🇳🇴 オスロ周辺イベント情報 ({week_str}週) - {event_count}件のイベント"
