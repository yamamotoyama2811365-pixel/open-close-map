import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg

from collectors.runner import run_collectors
from collectors.processor import promote_candidates, enrich_candidates
from collectors.article_enricher import fetch_article_facts
from collectors.address_audit import audit_addresses
from collectors.news_resolver import resolve_google_news_url
from collectors.rescue_processor import rescue_sources
from collectors.address_quality import audit_and_clean
from collectors.non_store_quality import audit_non_store_events
from collectors.text_rules import extract_best_store_name_from_title
from collectors.openclose_hub import collect_openclose_hub,enrich_hub_candidates

app=FastAPI(title="Open Close Map API",version="1.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

DATABASE_URL=os.getenv("DATABASE_URL","").strip()

def db_conn():
    return psycopg.connect(DATABASE_URL) if DATABASE_URL else None

def init_db():
    conn=db_conn()
    if conn is None:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stores(
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    category TEXT,
                    prefecture TEXT,
                    city TEXT,
                    address TEXT,
                    facility_name TEXT,
                    floor TEXT,
                    postal_code TEXT,
                    open_date DATE,
                    close_date DATE,
                    source_url TEXT,
                    source_name TEXT,
                    official_url TEXT,
                    confidence INTEGER DEFAULT 0,
                    last_verified_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            for q in [
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS facility_name TEXT",
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS floor TEXT",
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS postal_code TEXT",
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS source_name TEXT"
            ]:
                cur.execute(q)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS tenant_listings(
                    id BIGSERIAL PRIMARY KEY,
                    store_id BIGINT REFERENCES stores(id) ON DELETE SET NULL,
                    source_name TEXT,
                    source_url TEXT,
                    status TEXT DEFAULT 'detected',
                    last_verified_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS discovery_items(
                    id BIGSERIAL PRIMARY KEY,
                    fingerprint TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    source_name TEXT,
                    source_url TEXT NOT NULL,
                    resolved_source_url TEXT,
                    published_at TIMESTAMPTZ,
                    detected_status TEXT,
                    prefecture TEXT,
                    city TEXT,
                    confidence INTEGER DEFAULT 0,
                    raw_summary TEXT,
                    processed BOOLEAN DEFAULT FALSE,
                    store_name_candidate TEXT,
                    event_date_candidate DATE,
                    category_candidate TEXT,
                    address_candidate TEXT,
                    facility_name_candidate TEXT,
                    floor_candidate TEXT,
                    postal_code_candidate TEXT,
                    rescue_attempted_at TIMESTAMPTZ,
                    rescue_status TEXT,
                    rescue_error TEXT,
                    discovery_channel TEXT,
                    official_url_candidate TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            for q in [
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS resolved_source_url TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS address_candidate TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS facility_name_candidate TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS floor_candidate TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS postal_code_candidate TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS rescue_attempted_at TIMESTAMPTZ",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS rescue_status TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS rescue_error TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS publisher_name TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS publisher_home_url TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS discovery_channel TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS official_url_candidate TEXT",
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS official_url TEXT"
            ]:
                cur.execute(q)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {
        "service":"open-close-map-api",
        "status":"ok",
        "version":"1.3.0",
        "time":datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
def health():
    return {
        "ok":True,
        "database_configured":bool(DATABASE_URL),
        "time":datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/stats")
def stats():
    conn=db_conn()
    if conn is None:
        return {
            "today_open":0,"week_open":0,"week_close":0,
            "tenant_detected":0,"discovery_unprocessed":0,
            "stores_total":0,"stores_with_address":0,"mode":"no-database"
        }

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER(
                        WHERE status IN('open','opening') AND open_date=CURRENT_DATE
                    ),
                    COUNT(*) FILTER(
                        WHERE status IN('open','opening')
                          AND open_date BETWEEN CURRENT_DATE AND CURRENT_DATE+INTERVAL '7 days'
                    ),
                    COUNT(*) FILTER(
                        WHERE status IN('closed','closing')
                          AND close_date BETWEEN CURRENT_DATE AND CURRENT_DATE+INTERVAL '7 days'
                    ),
                    COUNT(*) FILTER(WHERE COALESCE(status,'') <> 'excluded'),
                    COUNT(*) FILTER(
                        WHERE COALESCE(status,'') <> 'excluded'
                          AND address IS NOT NULL AND address<>''
                    )
                FROM stores
            """)
            today,weeko,weekc,total,withaddr=cur.fetchone()

            cur.execute("""
                SELECT COUNT(*)
                FROM tenant_listings
                WHERE status IN('detected','active')
            """)
            tenant=cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*)
                FROM discovery_items
                WHERE processed=FALSE
            """)
            unprocessed=cur.fetchone()[0]

    return {
        "today_open":today,
        "week_open":weeko,
        "week_close":weekc,
        "tenant_detected":tenant,
        "discovery_unprocessed":unprocessed,
        "stores_total":total,
        "stores_with_address":withaddr,
        "mode":"database"
    }

@app.get("/api/stores")
def stores(
    status:Optional[str]=None,
    prefecture:Optional[str]=None,
    city:Optional[str]=None,
    limit:int=Query(default=50,ge=1,le=200)
):
    conn=db_conn()
    if conn is None:
        return {"items":[],"count":0}

    clauses=[]
    params=[]

    if not status:
        clauses.append("COALESCE(status,'') <> 'excluded'")

    if status:
        clauses.append("status=%s")
        params.append(status)
    if prefecture:
        clauses.append("prefecture=%s")
        params.append(prefecture)
    if city:
        clauses.append("city=%s")
        params.append(city)

    where=("WHERE "+" AND ".join(clauses)) if clauses else ""
    params.append(limit)

    with conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT
                    id,name,status,category,prefecture,city,address,
                    facility_name,floor,postal_code,
                    open_date,close_date,source_url,source_name,official_url,
                    confidence,last_verified_at
                FROM stores
                {where}
                ORDER BY COALESCE(open_date,close_date,created_at::date) DESC NULLS LAST,id DESC
                LIMIT %s
            """,params)
            rows=cur.fetchall()

    return {
        "items":[{
            "id":r[0],"name":r[1],"status":r[2],"category":r[3],
            "prefecture":r[4],"city":r[5],"address":r[6],
            "facility_name":r[7],"floor":r[8],"postal_code":r[9],
            "open_date":r[10].isoformat() if r[10] else None,
            "close_date":r[11].isoformat() if r[11] else None,
            "source_url":r[12],"source_name":r[13],"official_url":r[14],
            "confidence":r[15],
            "last_verified_at":r[16].isoformat() if r[16] else None
        } for r in rows],
        "count":len(rows)
    }

@app.get("/api/stores/{store_id}")
def store(store_id:int):
    conn=db_conn()
    if conn is None:
        raise HTTPException(503,"Database unavailable")

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,name,status,category,prefecture,city,address,
                    facility_name,floor,postal_code,
                    open_date,close_date,source_url,source_name,official_url,
                    confidence,last_verified_at
                FROM stores
                WHERE id=%s
            """,(store_id,))
            r=cur.fetchone()

    if not r:
        raise HTTPException(404,"Store not found")

    return {
        "id":r[0],"name":r[1],"status":r[2],"category":r[3],
        "prefecture":r[4],"city":r[5],"address":r[6],
        "facility_name":r[7],"floor":r[8],"postal_code":r[9],
        "open_date":r[10].isoformat() if r[10] else None,
        "close_date":r[11].isoformat() if r[11] else None,
        "source_url":r[12],"source_name":r[13],"official_url":r[14],
        "confidence":r[15],
        "last_verified_at":r[16].isoformat() if r[16] else None
    }

# ---- Restored detail-page APIs ----

@app.get("/api/stores/{store_id}/nearby")
def nearby(store_id:int,limit:int=Query(default=6,ge=1,le=20)):
    conn=db_conn()
    if conn is None:
        raise HTTPException(503,"Database unavailable")

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT prefecture,city
                FROM stores
                WHERE id=%s
            """,(store_id,))
            base=cur.fetchone()

            if not base:
                raise HTTPException(404,"Store not found")

            pref,city=base

            cur.execute("""
                SELECT id,name,status,category,facility_name
                FROM stores
                WHERE id<>%s
                  AND COALESCE(status,'') <> 'excluded'
                  AND COALESCE(prefecture,'')=COALESCE(%s,'')
                  AND COALESCE(city,'')=COALESCE(%s,'')
                ORDER BY id DESC
                LIMIT %s
            """,(store_id,pref,city,limit))
            rows=cur.fetchall()

    return {
        "items":[{
            "id":r[0],"name":r[1],"status":r[2],
            "category":r[3],"facility_name":r[4]
        } for r in rows]
    }

@app.get("/api/stores/{store_id}/tenant")
def tenant_info(store_id:int):
    conn=db_conn()
    if conn is None:
        raise HTTPException(503,"Database unavailable")

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id,source_name,source_url,status,last_verified_at
                FROM tenant_listings
                WHERE store_id=%s
                ORDER BY updated_at DESC
            """,(store_id,))
            rows=cur.fetchall()

    return {
        "items":[{
            "id":r[0],
            "source_name":r[1],
            "source_url":r[2],
            "status":r[3],
            "last_verified_at":r[4].isoformat() if r[4] else None
        } for r in rows]
    }

@app.get("/api/stores/{store_id}/area-summary")
def area_summary(store_id:int):
    conn=db_conn()
    if conn is None:
        raise HTTPException(503,"Database unavailable")

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT prefecture,city
                FROM stores
                WHERE id=%s
            """,(store_id,))
            base=cur.fetchone()

            if not base:
                raise HTTPException(404,"Store not found")

            pref,city=base

            cur.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER(WHERE status IN('open','opening')),
                    COUNT(*) FILTER(WHERE status IN('closed','closing'))
                FROM stores
                WHERE COALESCE(status,'') <> 'excluded'
                  AND COALESCE(prefecture,'')=COALESCE(%s,'')
                  AND COALESCE(city,'')=COALESCE(%s,'')
            """,(pref,city))
            total,opening,closing=cur.fetchone()

    return {
        "total":total,
        "opening":opening,
        "closing":closing
    }

@app.get("/api/stores/{store_id}/activity-score")
def activity_score(store_id:int):
    conn=db_conn()
    if conn is None:
        raise HTTPException(503,"Database unavailable")

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT prefecture,city
                FROM stores
                WHERE id=%s
            """,(store_id,))
            base=cur.fetchone()

            if not base:
                raise HTTPException(404,"Store not found")

            pref,city=base

            cur.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER(WHERE status IN('open','opening')),
                    COUNT(*) FILTER(WHERE status IN('closed','closing'))
                FROM stores
                WHERE COALESCE(status,'') <> 'excluded'
                  AND COALESCE(prefecture,'')=COALESCE(%s,'')
                  AND COALESCE(city,'')=COALESCE(%s,'')
            """,(pref,city))
            total,opening,closing=cur.fetchone()

    total=int(total or 0)
    opening=int(opening or 0)
    closing=int(closing or 0)

    density=min(40,round(total/20*40)) if total else 0
    open_ratio=(opening/total) if total else 0
    momentum=min(35,round(open_ratio*45))
    turnover=min(25,round((opening+closing)/20*25)) if total else 0
    score=max(0,min(100,density+momentum+turnover))

    if score>=80:
        label="非常に活発"
        comment="店舗の出入りが多く、商業動向が活発なエリアです。"
    elif score>=65:
        label="活発"
        comment="新規出店や店舗入替が比較的多いエリアです。"
    elif score>=50:
        label="標準"
        comment="一定の店舗動向が確認できるエリアです。"
    else:
        label="データ蓄積中"
        comment="現時点では店舗情報が少なく、今後のデータ蓄積で評価が変わる可能性があります。"

    return {
        "score":score,
        "label":label,
        "comment":comment,
        "breakdown":{
            "store_density":density,
            "opening_momentum":momentum,
            "turnover_activity":turnover
        },
        "version":"activity-v1"
    }

# ---- Collection / enrichment ----

@app.post("/api/collect")
def collect():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**run_collectors(DATABASE_URL)}

@app.post("/api/enrich-addresses")
def enrich_addresses(limit:int=Query(default=50,ge=1,le=200)):
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**enrich_candidates(DATABASE_URL,limit=limit,include_processed=True)}

@app.post("/api/backfill-addresses")
def backfill_addresses(limit:int=Query(default=100,ge=1,le=500)):
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**enrich_candidates(DATABASE_URL,limit=limit,include_processed=True)}

@app.post("/api/process")
def process(
    min_confidence:int=Query(default=80,ge=60,le=98),
    enrich_limit:int=Query(default=40,ge=0,le=200)
):
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}

    return {
        "ok":True,
        **promote_candidates(
            DATABASE_URL,
            min_confidence=min_confidence,
            enrich_limit=enrich_limit
        )
    }

@app.get("/api/test-article")
def test_article(url:str):
    return fetch_article_facts(url)

@app.get("/api/address-audit")
def address_audit(limit:int=Query(default=50,ge=1,le=100)):
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**audit_addresses(DATABASE_URL,limit=limit)}

@app.get("/api/resolve-news-url")
def resolve_news_url(url:str):
    return resolve_google_news_url(url)

@app.post("/api/resolve-and-backfill")
def resolve_and_backfill():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {
        "ok":True,
        "batch_size":5,
        **enrich_candidates(DATABASE_URL,limit=5,include_processed=True)
    }

@app.post("/api/rescue-sources")
def rescue_source_batch():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}

    # rescue_sources itself catches per-record errors.
    result=rescue_sources(DATABASE_URL,batch_size=5)
    return {"ok":True,**result}

@app.get("/api/rescue-status")
def rescue_status():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}

    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(rescue_status,'not_attempted') AS status,
                    COUNT(*)
                FROM discovery_items
                GROUP BY COALESCE(rescue_status,'not_attempted')
                ORDER BY 2 DESC
            """)
            rows=cur.fetchall()

    return {
        "ok":True,
        "summary":{r[0]:r[1] for r in rows}
    }

@app.get("/api/address-quality-audit")
def address_quality_audit():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**audit_and_clean(DATABASE_URL,apply=False,limit=100)}

@app.post("/api/address-quality-clean")
def address_quality_clean():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**audit_and_clean(DATABASE_URL,apply=True,limit=100)}

@app.get("/api/non-store-audit")
def non_store_audit():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**audit_non_store_events(DATABASE_URL,apply=False,limit=200)}

@app.post("/api/non-store-clean")
def non_store_clean():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**audit_non_store_events(DATABASE_URL,apply=True,limit=200)}

@app.post("/api/rescue-retry")
def rescue_retry():
    """
    新しい救済ロジックを試せるよう、失敗/未対応/住所未取得を再キュー化。
    excluded_event は戻さない。
    """
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}

    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE discovery_items
                SET rescue_attempted_at=NULL,
                    rescue_status=NULL,
                    rescue_error=NULL
                WHERE rescue_status IN(
                    'unsupported_publisher',
                    'relocation_failed',
                    'error',
                    'relocated_no_valid_address'
                )
            """)
            reset=cur.rowcount

    return {"ok":True,"reset":reset}

@app.get("/api/name-quality-audit")
def name_quality_audit(limit:int=Query(default=100,ge=1,le=300)):
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}

    conn=db_conn()
    items=[]
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.id,s.name,d.title
                FROM stores s
                JOIN LATERAL(
                    SELECT title
                    FROM discovery_items d
                    WHERE d.store_name_candidate=s.name
                    ORDER BY d.id DESC
                    LIMIT 1
                ) d ON TRUE
                WHERE COALESCE(s.status,'') <> 'excluded'
                ORDER BY s.id DESC
                LIMIT %s
            """,(limit,))
            rows=cur.fetchall()

    for sid,current,title in rows:
        better=extract_best_store_name_from_title(title)
        if better and better != current:
            items.append({
                "store_id":sid,
                "current_name":current,
                "suggested_name":better,
                "title":title
            })

    return {"ok":True,"count":len(items),"items":items}

@app.post("/api/collect-hub")
def collect_hub():
    """
    開店閉店系の専用サイトだけを収集。
    Google Newsは使わない。
    """
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**collect_openclose_hub(DATABASE_URL)}

@app.post("/api/enrich-hub")
def enrich_hub():
    """
    開店閉店系サイトの個別記事から、
    住所・正式店名・開閉店日・公式URL候補を20件固定で補完。
    """
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**enrich_hub_candidates(DATABASE_URL,limit=20)}

@app.post("/api/hub-cycle")
def hub_cycle():
    """
    1回で 専用サイト収集 → 20件詳細補完 → DB昇格 を行う。
    """
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}

    collected=collect_openclose_hub(DATABASE_URL)
    enriched=enrich_hub_candidates(DATABASE_URL,limit=20)
    processed=promote_candidates(
        DATABASE_URL,
        min_confidence=78,
        enrich_limit=0
    )
    return {
        "ok":True,
        "collected":collected,
        "enriched":enriched,
        "processed":processed
    }

@app.get("/api/source-hub-status")
def source_hub_status():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}

    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    source_name,
                    detected_status,
                    COUNT(*),
                    COUNT(*) FILTER(WHERE processed=FALSE),
                    COUNT(*) FILTER(WHERE address_candidate IS NOT NULL),
                    COUNT(*) FILTER(WHERE official_url_candidate IS NOT NULL)
                FROM discovery_items
                WHERE discovery_channel='openclose_hub'
                GROUP BY source_name,detected_status
                ORDER BY source_name,detected_status
            """)
            rows=cur.fetchall()

    return {
        "ok":True,
        "items":[{
            "source_name":r[0],
            "status":r[1],
            "total":r[2],
            "unprocessed":r[3],
            "with_address":r[4],
            "with_official_url":r[5]
        } for r in rows]
    }
