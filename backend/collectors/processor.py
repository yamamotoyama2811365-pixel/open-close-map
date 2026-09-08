from .article_enricher import fetch_article_facts
from .text_rules import calculate_confidence

def enrich_one_candidate(cur, row):
    (
        did,title,summary,name,ds,cat,pref,city,event,url,sname,conf,
        addr,facility,floor,postal
    ) = row

    # RSS本文ですでに番地まで取得できていない場合だけ記事元を確認
    if not addr or not facility:
        facts = fetch_article_facts(url)

        addr = addr or facts.get("address")
        facility = facility or facts.get("facility_name")
        floor = floor or facts.get("floor")
        postal = postal or facts.get("postal_code")

        # Google Newsのリダイレクト先など、最終URLが得られた場合
        resolved_url = facts.get("resolved_url") or url
    else:
        resolved_url = url

    new_conf = calculate_confidence(
        title or "", summary or "", ds, pref, city, event, cat, addr, facility
    )
    conf = max(int(conf or 0), int(new_conf or 0))

    cur.execute("""
        UPDATE discovery_items
        SET address_candidate=%s,
            facility_name_candidate=%s,
            floor_candidate=%s,
            postal_code_candidate=%s,
            resolved_source_url=%s,
            confidence=%s
        WHERE id=%s
    """,(addr,facility,floor,postal,resolved_url,conf,did))

    return {
        "id": did,
        "address": addr,
        "facility_name": facility,
        "floor": floor,
        "postal_code": postal,
        "resolved_source_url": resolved_url,
        "confidence": conf
    }

def enrich_candidates(database_url, limit=30, only_unprocessed=True):
    import psycopg
    done=0
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            where="WHERE processed=FALSE" if only_unprocessed else ""
            cur.execute(f"""
                SELECT id,title,raw_summary,store_name_candidate,detected_status,
                       category_candidate,prefecture,city,event_date_candidate,
                       source_url,source_name,confidence,address_candidate,
                       facility_name_candidate,floor_candidate,postal_code_candidate
                FROM discovery_items
                {where}
                ORDER BY confidence DESC, id DESC
                LIMIT %s
            """,(limit,))
            rows=cur.fetchall()

            for row in rows:
                enrich_one_candidate(cur,row)
                done+=1
    return {"enriched":done,"limit":limit}

def promote_candidates(database_url,min_confidence=80, enrich_limit=30):
    import psycopg

    # 先に上位候補の住所・施設名をベストエフォートで補強
    if enrich_limit > 0:
        enrich_candidates(database_url, limit=enrich_limit, only_unprocessed=True)

    promoted=skipped=0
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id,store_name_candidate,detected_status,category_candidate,
                       prefecture,city,event_date_candidate,
                       COALESCE(resolved_source_url,source_url),
                       source_name,confidence,address_candidate,
                       facility_name_candidate,floor_candidate,postal_code_candidate
                FROM discovery_items
                WHERE processed=FALSE
                  AND confidence >= %s
                  AND detected_status IN ('opening','closing')
                  AND store_name_candidate IS NOT NULL
                ORDER BY confidence DESC,id DESC
            """,(min_confidence,))

            for row in cur.fetchall():
                (
                    did,name,ds,cat,pref,city,event,url,sname,conf,
                    addr,facility,floor,postal
                )=row

                status="opening" if ds=="opening" else "closing"
                od=event if status=="opening" else None
                cd=event if status=="closing" else None

                cur.execute("""
                    SELECT id FROM stores
                    WHERE name=%s
                      AND COALESCE(prefecture,'')=COALESCE(%s,'')
                      AND COALESCE(city,'')=COALESCE(%s,'')
                      AND COALESCE(open_date,DATE '1900-01-01')=COALESCE(%s,DATE '1900-01-01')
                      AND COALESCE(close_date,DATE '1900-01-01')=COALESCE(%s,DATE '1900-01-01')
                    LIMIT 1
                """,(name,pref,city,od,cd))

                existing=cur.fetchone()
                if existing:
                    # 既存店舗でも住所情報だけ補完
                    cur.execute("""
                        UPDATE stores
                        SET address=COALESCE(address,%s),
                            facility_name=COALESCE(facility_name,%s),
                            floor=COALESCE(floor,%s),
                            postal_code=COALESCE(postal_code,%s),
                            source_url=COALESCE(%s,source_url),
                            confidence=GREATEST(confidence,%s),
                            updated_at=NOW()
                        WHERE id=%s
                    """,(addr,facility,floor,postal,url,conf,existing[0]))
                    cur.execute("UPDATE discovery_items SET processed=TRUE WHERE id=%s",(did,))
                    skipped+=1
                    continue

                cur.execute("""
                    INSERT INTO stores(
                        name,status,category,prefecture,city,address,facility_name,
                        floor,postal_code,open_date,close_date,source_url,source_name,
                        confidence,last_verified_at
                    )
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                """,(
                    name,status,cat,pref,city,addr,facility,floor,postal,
                    od,cd,url,sname,conf
                ))

                cur.execute("UPDATE discovery_items SET processed=TRUE WHERE id=%s",(did,))
                promoted+=1

    return {
        "promoted":promoted,
        "skipped":skipped,
        "min_confidence":min_confidence,
        "address_enrichment_limit":enrich_limit
    }
