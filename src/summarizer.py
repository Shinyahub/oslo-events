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

    user_prompt = f"""以下のイベントデータ（JSON）をもとに、週次イベント情報メールの本文を日本語で作成してください。

【対象地域】オスロおよびその周辺（車で行ける範囲）、ヨーテボリ、クリスチャンサン
【期間】今後4週間以内（全イベントを漏れなく掲載すること）

【フォーマット】
1. 冒頭に「今週のハイライト」として特に注目の3〜5イベントを紹介
2. カテゴリ別セクションに分けてリストアップ
   - 🎵 音楽・ライブ
   - 🎪 フェスティバル・お祭り
   - 🏃 スポーツ・マラソン
   - 🎨 文化・アート・展示
   - 🎭 その他エンタメ
3. 各イベントは「日付 | イベント名 | 会場/都市 | 一言説明」の形式で
4. URLがある場合はリンクを短くしたうえで添付

【イベントデータ】
{events_json}

読み手はオスロ在住の日本人です。週末や連休のお出かけ計画に役立つ情報を提供してください。
取得したイベントデータは全件（約100件以上）あります。直近だけでなく4週間分すべてを網羅してリストアップしてください。"""

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
