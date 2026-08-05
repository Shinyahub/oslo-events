"""
Claude API を使ったイベント情報の日本語サマリー生成
"""

import json
import logging
from typing import Optional
import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはオスロ在住の日本人向けに、ノルウェー・スウェーデン周辺のイベント情報を
わかりやすく日本語でまとめるアシスタントです。

以下のルールに従ってください：
- 日本語で、親しみやすく読みやすい文体で書く
- イベント名はオリジナル言語（英語/ノルウェー語）を残しつつ、日本語の説明を追加
- 日付・場所・内容を簡潔にまとめる
- 特に注目イベントは冒頭でハイライトする
- カテゴリ別（音楽・フェスティバル・スポーツ・文化・その他）に整理する"""


def summarize_events_with_claude(
    events: list[dict],
    anthropic_api_key: str,
    max_events: int = 60,
) -> str:
    """Claude APIを使ってイベント一覧を日本語サマリーに変換"""
    
    if not events:
        return "今週は収集できたイベント情報がありませんでした。"

    client = anthropic.Anthropic(api_key=anthropic_api_key)

    # イベントデータをJSON文字列に変換（トークン節約のため上位max_eventsのみ）
    events_for_summary = events[:max_events]
    events_json = json.dumps(events_for_summary, ensure_ascii=False, indent=2)

    user_prompt = (
        "以下のイベントデータをもとに、簡潔な日本語のメール本文を作成してください。\n\n"
        "【対象地域】オスロおよびその周辺、ヨーテボリ、クリスチャンサン\n"
        "【期間】今後4週間以内\n\n"
        "【ルール】\n"
        "- 全体400文字以内\n"
        "- 日付順に1行形式: 絵文字+日付 イベント名 会場/都市\n"
        "- 説明文・URLは不要\n"
        "- 注目イベントに先頭に星マーク\n"
        "- 冒頭一言のみ\n"
        "- 末尾の署名・ソース一覧は不要\n\n"
        f"【イベントデータ】\n{events_json}"
    )
    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API summarization failed: {e}")
        # フォールバック: シンプルなテキスト変換
        return _fallback_summary(events)


def _fallback_summary(events: list[dict]) -> str:
    """Claude API が使えない場合のシンプルなサマリー"""
    lines = ["【今後のイベント一覧】\n"]
    for ev in events[:40]:
        date = ev.get("date", "日付未定")
        title = ev.get("title", "")
        city = ev.get("city", "")
        category = ev.get("category", "")
        url = ev.get("url", "")
        line = f"・{date} | {title} | {city} | {category}"
        if url:
            line += f"\n  → {url}"
        lines.append(line)
    return "\n".join(lines)
