"""
イベントデータをdocs/events.jsonに書き出すモジュール
GitHub Pagesから読み込まれる
"""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

EXCLUDED_KEYWORDS = [
    "comedy", "stand-up", "standup", "talk show", "talkshow",
    "komedi", "kongehuset", "slottet", "royal palace",
]


def should_exclude(event: dict) -> bool:
    title = (event.get("title") or "").lower()
    category = (event.get("category") or "").lower()
    return any(kw in title or kw in category for kw in EXCLUDED_KEYWORDS)


def export_events_to_json(events: list[dict], output_path: str = "docs/events.json") -> None:
    """イベントリストをJSONファイルに書き出す"""

    # 除外フィルタ
    filtered = [ev for ev in events if not should_exclude(ev)]

    payload = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(filtered),
        "events": filtered,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {len(filtered)} events to {output_path}")
