"""
イベント情報収集モジュール
- Ticketmaster API
- Visitoslo.com スクレイピング
- Ruter/visitnorway などのサイト
"""

import os
import re
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

REGIONS = [
    {"name": "Oslo", "lat": 59.9139, "lon": 10.7522, "radius": "50km"},
    {"name": "Gothenburg", "lat": 57.7089, "lon": 11.9746, "radius": "30km"},
    {"name": "Kristiansand", "lat": 58.1599, "lon": 8.0182, "radius": "30km"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ──────────────────────────────────────────
# Ticketmaster API
# ──────────────────────────────────────────

def fetch_ticketmaster_events(api_key: str, weeks_ahead: int = 3) -> list[dict]:
    """Ticketmaster Discovery APIからイベントを取得"""
    events = []
    start_dt = datetime.utcnow()
    end_dt = start_dt + timedelta(weeks=weeks_ahead)
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    for region in REGIONS:
        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {
            "apikey": api_key,
            "latlong": f"{region['lat']},{region['lon']}",
            "radius": region["radius"].replace("km", ""),
            "unit": "km",
            "startDateTime": start_str,
            "endDateTime": end_str,
            "size": 200,
            "sort": "date,asc",
            "locale": "*",
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            raw_events = (
                data.get("_embedded", {}).get("events", [])
            )
            for ev in raw_events:
                events.append(_parse_ticketmaster_event(ev, region["name"]))
            logger.info(f"Ticketmaster: {len(raw_events)} events for {region['name']}")
        except Exception as e:
            logger.warning(f"Ticketmaster fetch failed for {region['name']}: {e}")
        time.sleep(0.3)

    return _dedupe(events)


def _parse_ticketmaster_event(ev: dict, region: str) -> dict:
    classifications = ev.get("classifications", [{}])
    genre = (
        classifications[0].get("genre", {}).get("name", "")
        if classifications else ""
    )
    segment = (
        classifications[0].get("segment", {}).get("name", "")
        if classifications else ""
    )
    venue = ev.get("_embedded", {}).get("venues", [{}])[0]
    dates = ev.get("dates", {}).get("start", {})
    return {
        "title": ev.get("name", ""),
        "date": dates.get("localDate", ""),
        "time": dates.get("localTime", ""),
        "venue": venue.get("name", ""),
        "city": venue.get("city", {}).get("name", region),
        "category": f"{segment} / {genre}".strip(" /"),
        "url": ev.get("url", ""),
        "source": "Ticketmaster",
        "description": "",
    }


# ──────────────────────────────────────────
# Visit Oslo スクレイピング
# ──────────────────────────────────────────

def fetch_visitoslo_events(weeks_ahead: int = 3) -> list[dict]:
    """visitoslo.com からイベントをスクレイピング"""
    events = []
    end_date = (datetime.now() + timedelta(weeks=weeks_ahead)).strftime("%Y-%m-%d")
    start_date = datetime.now().strftime("%Y-%m-%d")
    url = (
        f"https://www.visitoslo.com/en/whats-on/"
        f"?startDate={start_date}&endDate={end_date}"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # visitoslo のカードセレクタ（サイト構造に合わせて調整）
        cards = soup.select("article.event-card, div.event-item, li.event")
        if not cards:
            # フォールバック: より広いセレクタ
            cards = soup.select("[class*='event']")

        for card in cards[:30]:
            title_el = card.select_one("h2, h3, .title, .event-title")
            date_el = card.select_one(".date, time, [class*='date']")
            link_el = card.select_one("a[href]")
            category_el = card.select_one(".category, .tag, [class*='category']")

            title = title_el.get_text(strip=True) if title_el else ""
            date = date_el.get_text(strip=True) if date_el else ""
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = "https://www.visitoslo.com" + href
            category = category_el.get_text(strip=True) if category_el else "Event"

            if title:
                events.append({
                    "title": title,
                    "date": date,
                    "time": "",
                    "venue": "",
                    "city": "Oslo",
                    "category": category,
                    "url": href,
                    "source": "VisitOslo",
                    "description": "",
                })
        logger.info(f"VisitOslo: {len(events)} events scraped")
    except Exception as e:
        logger.warning(f"VisitOslo scrape failed: {e}")
    return events


# ──────────────────────────────────────────
# Visit Norway スクレイピング
# ──────────────────────────────────────────

def fetch_visitnorway_events(weeks_ahead: int = 3) -> list[dict]:
    """visitnorway.com のイベントページをスクレイピング"""
    events = []
    url = "https://www.visitnorway.com/things-to-do/events/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select("article, .event-card, [class*='EventCard'], [class*='event-item']")
        for card in cards[:20]:
            title_el = card.select_one("h2, h3, h4, .title")
            date_el = card.select_one("time, .date, [class*='date']")
            link_el = card.select_one("a[href]")
            loc_el = card.select_one(".location, [class*='location'], [class*='place']")

            title = title_el.get_text(strip=True) if title_el else ""
            date = date_el.get_text(strip=True) if date_el else ""
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = "https://www.visitnorway.com" + href
            location = loc_el.get_text(strip=True) if loc_el else "Norway"

            # オスロ・ヨーテボリ・クリスチャンサン周辺に絞る
            relevant_cities = ["oslo", "gothenburg", "göteborg", "kristiansand", "norway"]
            if title and any(c in location.lower() for c in relevant_cities):
                events.append({
                    "title": title,
                    "date": date,
                    "time": "",
                    "venue": "",
                    "city": location,
                    "category": "Festival/Event",
                    "url": href,
                    "source": "VisitNorway",
                    "description": "",
                })
        logger.info(f"VisitNorway: {len(events)} events scraped")
    except Exception as e:
        logger.warning(f"VisitNorway scrape failed: {e}")
    return events


# ──────────────────────────────────────────
# Billettservice (Norwegian ticketing)
# ──────────────────────────────────────────

def fetch_billettservice_events(weeks_ahead: int = 3) -> list[dict]:
    """billettservice.no からオスロ周辺イベントを取得"""
    events = []
    url = "https://www.billettservice.no/category/alle-arrangementer/10001?affiliate=TNO"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Billettservice の構造
        cards = soup.select(".event-listing__item, [class*='EventCard'], [data-testid*='event']")
        if not cards:
            cards = soup.select("li[class*='event'], div[class*='event']")

        for card in cards[:30]:
            title_el = card.select_one("h2, h3, [class*='title'], [class*='name']")
            date_el = card.select_one("[class*='date'], time, [class*='Date']")
            link_el = card.select_one("a[href]")

            title = title_el.get_text(strip=True) if title_el else ""
            date = date_el.get_text(strip=True) if date_el else ""
            href = link_el["href"] if link_el else ""
            if href and not href.startswith("http"):
                href = "https://www.billettservice.no" + href

            if title:
                events.append({
                    "title": title,
                    "date": date,
                    "time": "",
                    "venue": "",
                    "city": "Oslo",
                    "category": "Concert/Event",
                    "url": href,
                    "source": "Billettservice",
                    "description": "",
                })
        logger.info(f"Billettservice: {len(events)} events scraped")
    except Exception as e:
        logger.warning(f"Billettservice scrape failed: {e}")
    return events


# ──────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────

def _dedupe(events: list[dict]) -> list[dict]:
    """タイトル+日付で重複を除去"""
    seen = set()
    unique = []
    for ev in events:
        key = (ev["title"].lower().strip(), ev["date"])
        if key not in seen and ev["title"]:
            seen.add(key)
            unique.append(ev)
    return unique


def collect_all_events(
    ticketmaster_api_key: Optional[str] = None,
    weeks_ahead: int = 3,
) -> list[dict]:
    """全ソースからイベントを収集して統合"""
    all_events = []

    # Ticketmaster API
    if ticketmaster_api_key:
        logger.info("Fetching from Ticketmaster...")
        all_events.extend(fetch_ticketmaster_events(ticketmaster_api_key, weeks_ahead))

    # Web scraping
    logger.info("Scraping VisitOslo...")
    all_events.extend(fetch_visitoslo_events(weeks_ahead))

    logger.info("Scraping VisitNorway...")
    all_events.extend(fetch_visitnorway_events(weeks_ahead))

    logger.info("Scraping Billettservice...")
    all_events.extend(fetch_billettservice_events(weeks_ahead))

    # 重複除去 & 日付ソート
    all_events = _dedupe(all_events)
    all_events.sort(key=lambda x: x.get("date", "") or "9999")

    logger.info(f"Total events collected: {len(all_events)}")
    return all_events
