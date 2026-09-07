import hashlib
from datetime import datetime, timezone
import feedparser

from .sources import RSS_SOURCES
from .text_rules import (
    classify_title,
    detect_prefecture,
    detect_city,
    detect_category,
    extract_date,
    clean_store_name,
    calculate_confidence,
)

def fingerprint(title: str, url: str) -> str:
    return hashlib.sha256(f"{title.strip()}|{url.strip()}".encode("utf-8")).hexdigest()

def run_collectors(database_url: str):
    import psycopg

    fetched = inserted = duplicates = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for source in RSS_SOURCES:
                feed = feedparser.parse(source["url"])

                for entry in feed.entries[:source.get("limit", 50)]:
                    fetched += 1
                    title = (entry.get("title") or "").strip()
                    url = (entry.get("link") or "").strip()
                    summary = (entry.get("summary") or "").strip()

                    if not title or not url:
                        continue

                    status, base_confidence = classify_title(title)
                    if status is None:
                        continue

                    text = title + " " + summary
                    prefecture = detect_prefecture(text)
                    city = detect_city(text)
                    category = detect_category(text)
                    event_date = extract_date(text)
                    store_name = clean_store_name(title)
                    confidence = max(
                        base_confidence,
                        calculate_confidence(title, summary, status, prefecture, city, event_date, category)
                    )

                    published_at = None
                    if entry.get("published_parsed"):
                        p = entry["published_parsed"]
                        published_at = datetime(
                            p.tm_year, p.tm_mon, p.tm_mday,
                            p.tm_hour, p.tm_min, p.tm_sec,
                            tzinfo=timezone.utc
                        )

                    cur.execute("""
                        INSERT INTO discovery_items (
                            fingerprint, title, source_name, source_url,
                            published_at, detected_status, prefecture, city,
                            confidence, raw_summary, store_name_candidate,
                            event_date_candidate, category_candidate
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (fingerprint) DO UPDATE SET
                            prefecture = COALESCE(EXCLUDED.prefecture, discovery_items.prefecture),
                            city = COALESCE(EXCLUDED.city, discovery_items.city),
                            confidence = GREATEST(discovery_items.confidence, EXCLUDED.confidence),
                            store_name_candidate = COALESCE(EXCLUDED.store_name_candidate, discovery_items.store_name_candidate),
                            event_date_candidate = COALESCE(EXCLUDED.event_date_candidate, discovery_items.event_date_candidate),
                            category_candidate = COALESCE(EXCLUDED.category_candidate, discovery_items.category_candidate)
                        RETURNING (xmax = 0) AS inserted
                    """, (
                        fingerprint(title, url), title, source["name"], url,
                        published_at, status, prefecture, city, confidence,
                        summary[:1500] if summary else None, store_name,
                        event_date, category
                    ))

                    was_inserted = cur.fetchone()[0]
                    if was_inserted:
                        inserted += 1
                    else:
                        duplicates += 1

    return {
        "fetched": fetched,
        "inserted": inserted,
        "duplicates": duplicates,
        "sources": len(RSS_SOURCES),
    }
