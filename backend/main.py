import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg
from collectors.runner import run_collectors
from collectors.processor import promote_candidates

app=FastAPI(title="Open Close Map API",version="0.5.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
DATABASE_URL=os.getenv("DATABASE_URL","").strip()
def db_conn(): return psycopg.connect(DATABASE_URL) if DATABASE_URL else None

def init_db():
    conn=db_conn()
    if conn is None:return
    with conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS stores(id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,status TEXT NOT NULL,category TEXT,prefecture TEXT,city TEXT,address TEXT,open_date DATE,close_date DATE,source_url TEXT,source_name TEXT,confidence INTEGER DEFAULT 0,last_verified_at TIMESTAMPTZ,created_at TIMESTAMPTZ DEFAULT NOW(),updated_at TIMESTAMPTZ DEFAULT NOW())""")
            cur.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS source_name TEXT")
            cur.execute("""CREATE TABLE IF NOT EXISTS tenant_listings(id BIGSERIAL PRIMARY KEY,store_id BIGINT REFERENCES stores(id) ON DELETE SET NULL,source_name TEXT,source_url TEXT,status TEXT DEFAULT 'detected',last_verified_at TIMESTAMPTZ,created_at TIMESTAMPTZ DEFAULT NOW(),updated_at TIMESTAMPTZ DEFAULT NOW())""")
            cur.execute("""CREATE TABLE IF NOT EXISTS discovery_items(id BIGSERIAL PRIMARY KEY,fingerprint TEXT UNIQUE NOT NULL,title TEXT NOT NULL,source_name TEXT,source_url TEXT NOT NULL,published_at TIMESTAMPTZ,detected_status TEXT,prefecture TEXT,city TEXT,confidence INTEGER DEFAULT 0,raw_summary TEXT,processed BOOLEAN DEFAULT FALSE,store_name_candidate TEXT,event_date_candidate DATE,category_candidate TEXT,created_at TIMESTAMPTZ DEFAULT NOW())""")
@app.on_event("startup")
def startup_event(): init_db()

class StoreCreate(BaseModel):
    name:str; status:str; category:Optional[str]=None; prefecture:Optional[str]=None; city:Optional[str]=None; address:Optional[str]=None; open_date:Optional[str]=None; close_date:Optional[str]=None; source_url:Optional[str]=None; source_name:Optional[str]=None; confidence:int=0

@app.get("/")
def root(): return {"service":"open-close-map-api","status":"ok","version":"0.5.0","time":datetime.now(timezone.utc).isoformat()}
@app.get("/health")
def health(): return {"ok":True,"database_configured":bool(DATABASE_URL),"time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/stats")
def stats():
    conn=db_conn()
    if conn is None:return {"today_open":0,"week_open":0,"week_close":0,"tenant_detected":0,"discovery_unprocessed":0,"stores_total":0,"mode":"no-database"}
    with conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT COUNT(*) FILTER(WHERE status IN('open','opening') AND open_date=CURRENT_DATE),COUNT(*) FILTER(WHERE status IN('open','opening') AND open_date BETWEEN CURRENT_DATE AND CURRENT_DATE+INTERVAL '7 days'),COUNT(*) FILTER(WHERE status IN('closed','closing') AND close_date BETWEEN CURRENT_DATE AND CURRENT_DATE+INTERVAL '7 days'),COUNT(*) FROM stores""")
            today_open,week_open,week_close,stores_total=cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM tenant_listings WHERE status IN('detected','active')"); tenant_detected=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM discovery_items WHERE processed=FALSE"); discovery_unprocessed=cur.fetchone()[0]
    return {"today_open":today_open,"week_open":week_open,"week_close":week_close,"tenant_detected":tenant_detected,"discovery_unprocessed":discovery_unprocessed,"stores_total":stores_total,"mode":"database"}

@app.get("/api/stores")
def list_stores(status:Optional[str]=None,prefecture:Optional[str]=None,city:Optional[str]=None,limit:int=Query(default=50,ge=1,le=200)):
    conn=db_conn()
    if conn is None:return {"items":[],"count":0}
    clauses=[];params=[]
    if status:clauses.append("status=%s");params.append(status)
    if prefecture:clauses.append("prefecture=%s");params.append(prefecture)
    if city:clauses.append("city=%s");params.append(city)
    where="WHERE "+" AND ".join(clauses) if clauses else "";params.append(limit)
    with conn:
        with conn.cursor() as cur:
            cur.execute(f"""SELECT id,name,status,category,prefecture,city,address,open_date,close_date,source_url,source_name,confidence,last_verified_at FROM stores {where} ORDER BY COALESCE(open_date,close_date,created_at::date) DESC NULLS LAST,id DESC LIMIT %s""",params);rows=cur.fetchall()
    items=[{"id":r[0],"name":r[1],"status":r[2],"category":r[3],"prefecture":r[4],"city":r[5],"address":r[6],"open_date":r[7].isoformat() if r[7] else None,"close_date":r[8].isoformat() if r[8] else None,"source_url":r[9],"source_name":r[10],"confidence":r[11],"last_verified_at":r[12].isoformat() if r[12] else None} for r in rows]
    return {"items":items,"count":len(items)}

@app.get("/api/stores/{store_id}")
def get_store(store_id:int):
    conn=db_conn()
    if conn is None:raise HTTPException(503,"Database unavailable")
    with conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,name,status,category,prefecture,city,address,open_date,close_date,source_url,source_name,confidence,last_verified_at FROM stores WHERE id=%s""",(store_id,));r=cur.fetchone()
    if not r:raise HTTPException(404,"Store not found")
    return {"id":r[0],"name":r[1],"status":r[2],"category":r[3],"prefecture":r[4],"city":r[5],"address":r[6],"open_date":r[7].isoformat() if r[7] else None,"close_date":r[8].isoformat() if r[8] else None,"source_url":r[9],"source_name":r[10],"confidence":r[11],"last_verified_at":r[12].isoformat() if r[12] else None}

@app.get("/api/stores/{store_id}/nearby")
def nearby(store_id:int,limit:int=Query(default=6,ge=1,le=20)):
    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT prefecture,city FROM stores WHERE id=%s",(store_id,));base=cur.fetchone()
            if not base:raise HTTPException(404,"Store not found")
            pref,city=base
            cur.execute("""SELECT id,name,status,category FROM stores WHERE id<>%s AND COALESCE(prefecture,'')=COALESCE(%s,'') AND COALESCE(city,'')=COALESCE(%s,'') ORDER BY id DESC LIMIT %s""",(store_id,pref,city,limit))
            rows=cur.fetchall()
    return {"items":[{"id":r[0],"name":r[1],"status":r[2],"category":r[3]} for r in rows]}

@app.get("/api/stores/{store_id}/tenant")
def tenant_info(store_id:int):
    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,source_name,source_url,status,last_verified_at FROM tenant_listings WHERE store_id=%s ORDER BY updated_at DESC""",(store_id,));rows=cur.fetchall()
    return {"items":[{"id":r[0],"source_name":r[1],"source_url":r[2],"status":r[3],"last_verified_at":r[4].isoformat() if r[4] else None} for r in rows]}

@app.get("/api/stores/{store_id}/area-summary")
def area_summary(store_id:int):
    conn=db_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT prefecture,city FROM stores WHERE id=%s",(store_id,));base=cur.fetchone()
            if not base:raise HTTPException(404,"Store not found")
            pref,city=base
            cur.execute("""SELECT COUNT(*),COUNT(*) FILTER(WHERE status IN('open','opening')),COUNT(*) FILTER(WHERE status IN('closed','closing')) FROM stores WHERE COALESCE(prefecture,'')=COALESCE(%s,'') AND COALESCE(city,'')=COALESCE(%s,'')""",(pref,city))
            total,opening,closing=cur.fetchone()
    return {"total":total,"opening":opening,"closing":closing}

@app.post("/api/collect")
def collect():
    if not DATABASE_URL:return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**run_collectors(DATABASE_URL)}
@app.post("/api/process")
def process(min_confidence:int=Query(default=80,ge=60,le=95)):
    if not DATABASE_URL:return {"ok":False,"error":"DATABASE_URL is not configured"}
    return {"ok":True,**promote_candidates(DATABASE_URL,min_confidence)}
