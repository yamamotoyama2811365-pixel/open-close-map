import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg
from collectors.runner import run_collectors

app = FastAPI(title="Open Close Map API", version="0.2.0", description="Backend API for 開店閉店マップ")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def db_conn():
    return psycopg.connect(DATABASE_URL) if DATABASE_URL else None

def init_db():
    conn = db_conn()
    if conn is None:
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stores (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    category TEXT,
                    prefecture TEXT,
                    city TEXT,
                    address TEXT,
                    open_date DATE,
                    close_date DATE,
                    source_url TEXT,
                    source_name TEXT,
                    confidence INTEGER DEFAULT 0,
                    last_verified_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS source_name TEXT")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tenant_listings (
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
                CREATE TABLE IF NOT EXISTS discovery_items (
                    id BIGSERIAL PRIMARY KEY,
                    fingerprint TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    source_name TEXT,
                    source_url TEXT NOT NULL,
                    published_at TIMESTAMPTZ,
                    detected_status TEXT,
                    prefecture TEXT,
                    city TEXT,
                    confidence INTEGER DEFAULT 0,
                    raw_summary TEXT,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

@app.on_event("startup")
def startup_event():
    init_db()

class StoreCreate(BaseModel):
    name: str
    status: str
    category: Optional[str] = None
    prefecture: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    confidence: int = 0

@app.get("/")
def root():
    return {"service":"open-close-map-api","status":"ok","version":"0.2.0","time":datetime.now(timezone.utc).isoformat()}

@app.get("/health")
def health():
    return {"ok":True,"database_configured":bool(DATABASE_URL),"time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/stores")
def list_stores(status: Optional[str]=None, prefecture: Optional[str]=None, city: Optional[str]=None, limit: int=Query(default=50, ge=1, le=200)):
    conn = db_conn()
    if conn is None:
        return {"items":[],"count":0,"mode":"no-database"}
    clauses, params = [], []
    if status:
        clauses.append("status = %s"); params.append(status)
    if prefecture:
        clauses.append("prefecture = %s"); params.append(prefecture)
    if city:
        clauses.append("city = %s"); params.append(city)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id,name,status,category,prefecture,city,address,
                       open_date,close_date,source_url,source_name,confidence,last_verified_at
                FROM stores {where}
                ORDER BY COALESCE(open_date, close_date) DESC NULLS LAST, id DESC
                LIMIT %s
            """, params)
            rows = cur.fetchall()
    items = [{
        "id":r[0],"name":r[1],"status":r[2],"category":r[3],"prefecture":r[4],"city":r[5],"address":r[6],
        "open_date":r[7].isoformat() if r[7] else None,"close_date":r[8].isoformat() if r[8] else None,
        "source_url":r[9],"source_name":r[10],"confidence":r[11],"last_verified_at":r[12].isoformat() if r[12] else None
    } for r in rows]
    return {"items":items,"count":len(items),"mode":"database"}

@app.post("/api/stores")
def create_store(store: StoreCreate):
    conn = db_conn()
    if conn is None:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO stores (
                    name,status,category,prefecture,city,address,
                    open_date,close_date,source_url,source_name,confidence,last_verified_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW()) RETURNING id
            """, (
                store.name,store.status,store.category,store.prefecture,store.city,store.address,
                store.open_date,store.close_date,store.source_url,store.source_name,store.confidence
            ))
            store_id = cur.fetchone()[0]
    return {"ok":True,"id":store_id}

@app.get("/api/discovery")
def discovery(status: Optional[str]=None, processed: Optional[bool]=None, limit: int=Query(default=50, ge=1, le=200)):
    conn = db_conn()
    if conn is None:
        return {"items":[],"count":0,"mode":"no-database"}
    clauses, params = [], []
    if status:
        clauses.append("detected_status = %s"); params.append(status)
    if processed is not None:
        clauses.append("processed = %s"); params.append(processed)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id,title,source_name,source_url,published_at,detected_status,
                       prefecture,city,confidence,processed,created_at
                FROM discovery_items {where}
                ORDER BY COALESCE(published_at,created_at) DESC
                LIMIT %s
            """, params)
            rows = cur.fetchall()
    items = [{
        "id":r[0],"title":r[1],"source_name":r[2],"source_url":r[3],
        "published_at":r[4].isoformat() if r[4] else None,"detected_status":r[5],
        "prefecture":r[6],"city":r[7],"confidence":r[8],"processed":r[9],
        "created_at":r[10].isoformat() if r[10] else None
    } for r in rows]
    return {"items":items,"count":len(items),"mode":"database"}

@app.get("/api/stats")
def stats():
    conn = db_conn()
    if conn is None:
        return {"today_open":0,"week_open":0,"week_close":0,"tenant_detected":0,"discovery_unprocessed":0,"mode":"no-database"}
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status='open' AND open_date=CURRENT_DATE),
                    COUNT(*) FILTER (WHERE status IN ('open','opening') AND open_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'),
                    COUNT(*) FILTER (WHERE status IN ('closed','closing') AND close_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days')
                FROM stores
            """)
            row = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM tenant_listings WHERE status IN ('detected','active')")
            tenant_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM discovery_items WHERE processed=FALSE")
            discovery_count = cur.fetchone()[0]
    return {"today_open":row[0],"week_open":row[1],"week_close":row[2],"tenant_detected":tenant_count,"discovery_unprocessed":discovery_count,"mode":"database"}

@app.post("/api/collect")
def collect():
    if not DATABASE_URL:
        return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True, **run_collectors(DATABASE_URL)}
