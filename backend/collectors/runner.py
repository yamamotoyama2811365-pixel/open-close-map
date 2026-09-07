import hashlib
from datetime import datetime, timezone
import feedparser
from .sources import RSS_SOURCES
from .text_rules import classify_title, detect_prefecture

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

                    detected_status, confidence = classify_title(title)
                    if detected_status is None:
                        continue

                    prefecture = detect_prefecture(title + " " + summary)
                    published_at = None
                    if entry.get("published_parsed"):
                        p = entry["published_parsed"]
                        published_at = datetime(
                            p.tm_year, p.tm_mon, p.tm_mday,
                            p.tm_hour, p.tm_min, p.tm_sec,
                            tzinfo=timezone.utc
                        )

                    cur.execute(
                        """
                        INSERT INTO discovery_items (
                            fingerprint, title, source_name, source_url,
                            published_at, detected_status, prefecture,
                            confidence, raw_summary
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (fingerprint) DO NOTHING
                        RETURNING id
                        """,
                        (
                            fingerprint(title, url), title, source["name"], url,
                            published_at, detected_status, prefecture,
                            confidence, summary[:1500] if summary else None
                        ),
                    )
                    if cur.fetchone():
                        inserted += 1
                    else:
                        duplicates += 1

    return {"fetched": fetched, "inserted": inserted, "duplicates": duplicates, "sources": len(RSS_SOURCES)}
