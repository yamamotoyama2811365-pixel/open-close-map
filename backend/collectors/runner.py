import hashlib, feedparser
from datetime import datetime, timezone
from .sources import RSS_SOURCES
from .text_rules import (
    classify_title,detect_prefecture,detect_city,detect_category,extract_date,
    clean_store_name,calculate_confidence,extract_address,extract_facility_name,
    extract_floor,extract_postal_code,extract_source_name_from_title
)

def fingerprint(title,url):
    return hashlib.sha256(f"{title.strip()}|{url.strip()}".encode()).hexdigest()

def run_collectors(database_url):
    import psycopg
    fetched=inserted=duplicates=0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for source in RSS_SOURCES:
                feed=feedparser.parse(source["url"])

                for entry in feed.entries[:source.get("limit",50)]:
                    fetched+=1
                    title=(entry.get("title") or "").strip()
                    url=(entry.get("link") or "").strip()
                    summary=(entry.get("summary") or "").strip()
                    if not title or not url:continue

                    src_obj=entry.get("source") or {}
                    publisher_name=None
                    publisher_home=None
                    try:
                        publisher_name=(src_obj.get("title") or "").strip() or None
                        publisher_home=(src_obj.get("href") or "").strip() or None
                    except Exception:
                        pass
                    publisher_name=publisher_name or extract_source_name_from_title(title)

                    status,base=classify_title(title)
                    if status is None:continue

                    text=title+"\n"+summary
                    pref=detect_prefecture(text)
                    city=detect_city(text)
                    cat=detect_category(text)
                    event=extract_date(text)
                    name=clean_store_name(title)
                    addr=extract_address(text)
                    facility=extract_facility_name(text,addr)
                    floor=extract_floor(text)
                    postal=extract_postal_code(text)

                    conf=max(base,calculate_confidence(
                        title,summary,status,pref,city,event,cat,addr,facility
                    ))

                    published=None
                    if entry.get("published_parsed"):
                        p=entry["published_parsed"]
                        published=datetime(
                            p.tm_year,p.tm_mon,p.tm_mday,p.tm_hour,p.tm_min,p.tm_sec,
                            tzinfo=timezone.utc
                        )

                    cur.execute("""
                    INSERT INTO discovery_items(
                        fingerprint,title,source_name,source_url,published_at,
                        detected_status,prefecture,city,confidence,raw_summary,
                        store_name_candidate,event_date_candidate,category_candidate,
                        address_candidate,facility_name_candidate,floor_candidate,
                        postal_code_candidate,publisher_name,publisher_home_url
                    )
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(fingerprint) DO UPDATE SET
                        prefecture=COALESCE(EXCLUDED.prefecture,discovery_items.prefecture),
                        city=COALESCE(EXCLUDED.city,discovery_items.city),
                        confidence=GREATEST(discovery_items.confidence,EXCLUDED.confidence),
                        store_name_candidate=COALESCE(EXCLUDED.store_name_candidate,discovery_items.store_name_candidate),
                        event_date_candidate=COALESCE(EXCLUDED.event_date_candidate,discovery_items.event_date_candidate),
                        category_candidate=COALESCE(EXCLUDED.category_candidate,discovery_items.category_candidate),
                        address_candidate=COALESCE(EXCLUDED.address_candidate,discovery_items.address_candidate),
                        facility_name_candidate=COALESCE(EXCLUDED.facility_name_candidate,discovery_items.facility_name_candidate),
                        floor_candidate=COALESCE(EXCLUDED.floor_candidate,discovery_items.floor_candidate),
                        postal_code_candidate=COALESCE(EXCLUDED.postal_code_candidate,discovery_items.postal_code_candidate),
                        publisher_name=COALESCE(EXCLUDED.publisher_name,discovery_items.publisher_name),
                        publisher_home_url=COALESCE(EXCLUDED.publisher_home_url,discovery_items.publisher_home_url)
                    RETURNING (xmax=0)
                    """,(
                        fingerprint(title,url),title,source["name"],url,published,status,pref,
                        city,conf,summary[:2000] if summary else None,name,event,cat,
                        addr,facility,floor,postal,publisher_name,publisher_home
                    ))

                    if cur.fetchone()[0]:inserted+=1
                    else:duplicates+=1

    return {"fetched":fetched,"inserted":inserted,"duplicates":duplicates,"sources":len(RSS_SOURCES)}
