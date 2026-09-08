import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI,Query,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg
from collectors.runner import run_collectors
from collectors.processor import promote_candidates,enrich_candidates
from collectors.article_enricher import fetch_article_facts

app=FastAPI(title="Open Close Map API",version="0.7.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
DATABASE_URL=os.getenv("DATABASE_URL","").strip()
def db_conn():return psycopg.connect(DATABASE_URL) if DATABASE_URL else None

def init_db():
    conn=db_conn()
    if conn is None:return
    with conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS stores(
                id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,status TEXT NOT NULL,category TEXT,
                prefecture TEXT,city TEXT,address TEXT,facility_name TEXT,floor TEXT,postal_code TEXT,
                open_date DATE,close_date DATE,source_url TEXT,source_name TEXT,confidence INTEGER DEFAULT 0,
                last_verified_at TIMESTAMPTZ,created_at TIMESTAMPTZ DEFAULT NOW(),updated_at TIMESTAMPTZ DEFAULT NOW())""")
            for q in [
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS facility_name TEXT",
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS floor TEXT",
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS postal_code TEXT",
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS source_name TEXT"]:
                cur.execute(q)

            cur.execute("""CREATE TABLE IF NOT EXISTS tenant_listings(
                id BIGSERIAL PRIMARY KEY,store_id BIGINT REFERENCES stores(id) ON DELETE SET NULL,
                source_name TEXT,source_url TEXT,status TEXT DEFAULT 'detected',
                last_verified_at TIMESTAMPTZ,created_at TIMESTAMPTZ DEFAULT NOW(),updated_at TIMESTAMPTZ DEFAULT NOW())""")

            cur.execute("""CREATE TABLE IF NOT EXISTS discovery_items(
                id BIGSERIAL PRIMARY KEY,fingerprint TEXT UNIQUE NOT NULL,title TEXT NOT NULL,
                source_name TEXT,source_url TEXT NOT NULL,resolved_source_url TEXT,published_at TIMESTAMPTZ,
                detected_status TEXT,prefecture TEXT,city TEXT,confidence INTEGER DEFAULT 0,raw_summary TEXT,
                processed BOOLEAN DEFAULT FALSE,store_name_candidate TEXT,event_date_candidate DATE,
                category_candidate TEXT,address_candidate TEXT,facility_name_candidate TEXT,
                floor_candidate TEXT,postal_code_candidate TEXT,created_at TIMESTAMPTZ DEFAULT NOW())""")
            for q in [
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS resolved_source_url TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS address_candidate TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS facility_name_candidate TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS floor_candidate TEXT",
                "ALTER TABLE discovery_items ADD COLUMN IF NOT EXISTS postal_code_candidate TEXT"]:
                cur.execute(q)

@app.on_event("startup")
def startup():init_db()

@app.get("/")
def root():return {"service":"open-close-map-api","status":"ok","version":"0.7.0","time":datetime.now(timezone.utc).isoformat()}
@app.get("/health")
def health():return {"ok":True,"database_configured":bool(DATABASE_URL),"time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/stats")
def stats():
    conn=db_conn()
    if conn is None:return {"today_open":0,"week_open":0,"week_close":0,"tenant_detected":0,"discovery_unprocessed":0,"stores_total":0,"stores_with_address":0,"mode":"no-database"}
    with conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT
                COUNT(*) FILTER(WHERE status IN('open','opening') AND open_date=CURRENT_DATE),
                COUNT(*) FILTER(WHERE status IN('open','opening') AND open_date BETWEEN CURRENT_DATE AND CURRENT_DATE+INTERVAL '7 days'),
                COUNT(*) FILTER(WHERE status IN('closed','closing') AND close_date BETWEEN CURRENT_DATE AND CURRENT_DATE+INTERVAL '7 days'),
                COUNT(*),
                COUNT(*) FILTER(WHERE address IS NOT NULL AND address<>'')
                FROM stores""")
            today,weeko,weekc,total,withaddr=cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM tenant_listings WHERE status IN('detected','active')");tenant=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM discovery_items WHERE processed=FALSE");unprocessed=cur.fetchone()[0]
    return {"today_open":today,"week_open":weeko,"week_close":weekc,"tenant_detected":tenant,
            "discovery_unprocessed":unprocessed,"stores_total":total,"stores_with_address":withaddr,"mode":"database"}

@app.get("/api/stores")
def stores(limit:int=Query(default=50,ge=1,le=200)):
    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,name,status,category,prefecture,city,address,facility_name,floor,postal_code,
                open_date,close_date,source_url,source_name,confidence,last_verified_at
                FROM stores ORDER BY id DESC LIMIT %s""",(limit,))
            rows=cur.fetchall()
    return {"items":[{"id":r[0],"name":r[1],"status":r[2],"category":r[3],"prefecture":r[4],"city":r[5],
                      "address":r[6],"facility_name":r[7],"floor":r[8],"postal_code":r[9],
                      "open_date":r[10].isoformat() if r[10] else None,"close_date":r[11].isoformat() if r[11] else None,
                      "source_url":r[12],"source_name":r[13],"confidence":r[14],
                      "last_verified_at":r[15].isoformat() if r[15] else None} for r in rows],
            "count":len(rows)}

@app.get("/api/stores/{store_id}")
def store(store_id:int):
    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,name,status,category,prefecture,city,address,facility_name,floor,postal_code,
                open_date,close_date,source_url,source_name,confidence,last_verified_at FROM stores WHERE id=%s""",(store_id,))
            r=cur.fetchone()
    if not r:raise HTTPException(404,"Store not found")
    return {"id":r[0],"name":r[1],"status":r[2],"category":r[3],"prefecture":r[4],"city":r[5],
            "address":r[6],"facility_name":r[7],"floor":r[8],"postal_code":r[9],
            "open_date":r[10].isoformat() if r[10] else None,"close_date":r[11].isoformat() if r[11] else None,
            "source_url":r[12],"source_name":r[13],"confidence":r[14],
            "last_verified_at":r[15].isoformat() if r[15] else None}

@app.post("/api/collect")
def collect():
    return {"ok":True,**run_collectors(DATABASE_URL)}

@app.post("/api/enrich-addresses")
def enrich_addresses(limit:int=Query(default=50,ge=1,le=200)):
    return {"ok":True,**enrich_candidates(DATABASE_URL,limit=limit,include_processed=True)}

@app.post("/api/backfill-addresses")
def backfill_addresses(limit:int=Query(default=100,ge=1,le=500)):
    return {"ok":True,**enrich_candidates(DATABASE_URL,limit=limit,include_processed=True)}

@app.post("/api/process")
def process(min_confidence:int=Query(default=80,ge=60,le=98),enrich_limit:int=Query(default=40,ge=0,le=200)):
    return {"ok":True,**promote_candidates(DATABASE_URL,min_confidence=min_confidence,enrich_limit=enrich_limit)}

@app.get("/api/test-article")
def test_article(url:str):
    """住所抽出テスト用。DBには保存しない。"""
    return fetch_article_facts(url)
