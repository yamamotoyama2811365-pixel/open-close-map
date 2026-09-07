def promote_candidates(database_url: str, min_confidence: int = 80):
    import psycopg
    promoted = skipped = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id, store_name_candidate, detected_status, category_candidate,
                    prefecture, city, event_date_candidate, source_url, source_name,
                    confidence
                FROM discovery_items
                WHERE processed = FALSE
                  AND confidence >= %s
                  AND detected_status IN ('opening','closing')
                  AND store_name_candidate IS NOT NULL
            """, (min_confidence,))
            rows = cur.fetchall()

            for row in rows:
                discovery_id, name, detected_status, category, prefecture, city, event_date, source_url, source_name, confidence = row
                status = "opening" if detected_status == "opening" else "closing"
                open_date = event_date if status == "opening" else None
                close_date = event_date if status == "closing" else None

                cur.execute("""
                    SELECT id FROM stores
                    WHERE name = %s
                      AND COALESCE(prefecture,'') = COALESCE(%s,'')
                      AND COALESCE(city,'') = COALESCE(%s,'')
                      AND COALESCE(open_date, DATE '1900-01-01') = COALESCE(%s, DATE '1900-01-01')
                      AND COALESCE(close_date, DATE '1900-01-01') = COALESCE(%s, DATE '1900-01-01')
                    LIMIT 1
                """, (name, prefecture, city, open_date, close_date))

                if cur.fetchone():
                    cur.execute("UPDATE discovery_items SET processed = TRUE WHERE id = %s", (discovery_id,))
                    skipped += 1
                    continue

                cur.execute("""
                    INSERT INTO stores (
                        name,status,category,prefecture,city,
                        open_date,close_date,source_url,source_name,
                        confidence,last_verified_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                """, (
                    name,status,category,prefecture,city,
                    open_date,close_date,source_url,source_name,confidence
                ))
                cur.execute("UPDATE discovery_items SET processed = TRUE WHERE id = %s", (discovery_id,))
                promoted += 1

    return {"promoted": promoted, "skipped": skipped, "min_confidence": min_confidence}
