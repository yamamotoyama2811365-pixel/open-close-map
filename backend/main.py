import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    import psycopg
except Exception:
    psycopg = None

app = FastAPI(
    title="Open Close Map API",
    version="0.1.0",
    description="Backend API for 開店閉店マップ",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def db_conn():
    if not DATABASE_URL or psycopg is None:
        return None
    return psycopg.connect(DATABASE_URL)


def init_db():
    conn = db_conn()
    if conn is None:
        return
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
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
                    confidence INTEGER DEFAULT 0,
                    last_verified_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
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
                """
            )


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
    confidence: int = 0


@app.get("/")
def root():
    return {
        "service": "open-close-map-api",
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health():
    db = bool(DATABASE_URL)
    return {
        "ok": True,
        "database_configured": db,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/stats")
def stats():
    conn = db_conn()
    if conn is None:
        return {
            "today_open": 0,
            "week_open": 0,
            "week_close": 0,
            "tenant_detected": 0,
            "mode": "no-database",
        }

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  COUNT(*) FILTER (WHERE status = 'open' AND open_date = CURRENT_DATE),
                  COUNT(*) FILTER (WHERE status IN ('open','opening') AND open_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'),
                  COUNT(*) FILTER (WHERE status IN ('closed','closing') AND close_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days')
                FROM stores
                """
            )
            row = cur.fetchone()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM tenant_listings
                WHERE status IN ('detected', 'active')
                """
            )
            tenant_count = cur.fetchone()[0]

    return {
        "today_open": row[0],
        "week_open": row[1],
        "week_close": row[2],
        "tenant_detected": tenant_count,
        "mode": "database",
    }


@app.get("/api/stores")
def list_stores(
    status: Optional[str] = Query(default=None),
    prefecture: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    conn = db_conn()
    if conn is None:
        return {"items": [], "count": 0, "mode": "no-database"}

    clauses = []
    params = []

    if status:
        clauses.append("status = %s")
        params.append(status)
    if prefecture:
        clauses.append("prefecture = %s")
        params.append(prefecture)
    if city:
        clauses.append("city = %s")
        params.append(city)

    where = "WHERE " + " AND ".join(clauses) if clauses else ""

    sql = f"""
        SELECT id, name, status, category, prefecture, city, address,
               open_date, close_date, source_url, confidence, last_verified_at
        FROM stores
        {where}
        ORDER BY COALESCE(open_date, close_date) DESC NULLS LAST, id DESC
        LIMIT %s
    """
    params.append(limit)

    with conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "name": r[1],
            "status": r[2],
            "category": r[3],
            "prefecture": r[4],
            "city": r[5],
            "address": r[6],
            "open_date": r[7].isoformat() if r[7] else None,
            "close_date": r[8].isoformat() if r[8] else None,
            "source_url": r[9],
            "confidence": r[10],
            "last_verified_at": r[11].isoformat() if r[11] else None,
        })

    return {"items": items, "count": len(items), "mode": "database"}


@app.post("/api/stores")
def create_store(store: StoreCreate):
    conn = db_conn()
    if conn is None:
        return {"ok": False, "error": "DATABASE_URL is not configured"}

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stores (
                    name, status, category, prefecture, city, address,
                    open_date, close_date, source_url, confidence, last_verified_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, NOW()
                )
                RETURNING id
                """,
                (
                    store.name,
                    store.status,
                    store.category,
                    store.prefecture,
                    store.city,
                    store.address,
                    store.open_date,
                    store.close_date,
                    store.source_url,
                    store.confidence,
                ),
            )
            store_id = cur.fetchone()[0]

    return {"ok": True, "id": store_id}
