"""
イベントデータをdocs/events.jsonに書き出すモジュール
収集時にClaude APIで日本語説明も生成する
"""

import json
import logging
import os
import time
from datetime import datetime
import anthropic

logger = logging.getLogger(__name__)

EXCLUDED_KEYWORDS = [
    "comedy", "stand-up", "standup", "talk show", "talkshow",
    "komedi", "kongehuset", "slottet", "royal palace",
    "humorfest", "humor fest",
]


def should_exclude(event: dict) -> bool:
    title = (event.get("title") or "").lower()
    category = (event.get("category") or "").lower()
    return any(kw in title or kw in category for kw in EXCLUDED_KEYWORDS)


def generate_description(client: anthropic.Anthropic, title: str, category: str, city: str) -> str:
    """Claude APIでイベントの日本語説明を生成"""
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            messages=[{
                "role": "user",
                "content": (
                    f"以下のイベントについて、日本語で40文字以内の一言説明を書いてください。"
                    f"説明文のみ返してください。\n"
                    f"イベント名: {title}\nカテゴリ: {category}\n都市: {city}"
                )
            }]
        )
        return msg.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Description generation failed for '{title}': {e}")
        return ""


def export_events_to_json(
    events: list[dict],
    output_path: str = "docs/events.json",
    anthropic_api_key: str = "",
) -> None:
    """イベントリストをJSONファイルに書き出す（日本語説明付き）"""

    # 除外フィルタ
    filtered = [ev for ev in events if not should_exclude(ev)]

    # Claude APIで説明文を生成
    if anthropic_api_key:
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        logger.info(f"Generating Japanese descriptions for {len(filtered)} events...")
        for i, ev in enumerate(filtered):
            if not ev.get("description"):
                ev["description"] = generate_description(
                    client,
                    ev.get("title", ""),
                    ev.get("category", ""),
                    ev.get("city", ""),
                )
                if i % 10 == 0:
                    logger.info(f"  {i+1}/{len(filtered)} descriptions generated")
                time.sleep(0.1)  # API負荷を分散

    payload = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(filtered),
        "events": filtered,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {len(filtered)} events to {output_path}")
