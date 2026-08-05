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
        "以下のイベントデータをもとに、日本語のメール本文を作成してください。\n\n"
        "【対象地域】オスロおよびその周辺、ヨーテボリ、クリスチャンサン\n"
        "【期間】今後1ヶ月以内\n\n"
        "【除外するカテゴリ】\n"
        "- ノルウェー王宮の一般公開、お笑いショー、スタンドアップコメディ、トークショー、Comedy、Stand-up\n\n"
        "【ルール】\n"
        "- 冒頭に一言のみ（例：今後1ヶ月のオスロ周辺イベントです。）\n"
        "- 同じイベント名で複数日程がある場合は「7/1〜7/3」のようにまとめて1件として表示する\n"
        "- 日付順に以下の2行形式で全件並べる（直近だけでなく1ヶ月分すべて掲載）:\n"
        "  1行目: 📅日付 ★イベント名 📍会場/都市\n"
        "  2行目: 　→ イベントの内容を日本語で50文字以内で説明\n"
        "- 注目イベントには★、通常は・を使う\n"
        "- URLを入れる\n"
        "- 末尾の署名・ソース一覧は不要\n"
        "- 除外カテゴリ以外のイベントは省略せず全件掲載すること\n\n"
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
