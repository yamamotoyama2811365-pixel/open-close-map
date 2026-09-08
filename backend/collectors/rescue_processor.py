from .source_relocator import relocate_source
from .article_enricher import fetch_article_facts
from .text_rules import calculate_confidence, extract_source_name_from_title

def rescue_sources(database_url, batch_size=5):
    import psycopg
    from datetime import datetime, timezone

    scanned=relocated=address_found=store_updated=unsupported=failed=rejected=0
    results=[]

    # Fetch targets first. Prefer never-attempted items so the same unsupported
    # five records don't block the queue forever.
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    s.id,s.name,s.prefecture,s.city,s.address,
                    d.id,d.title,d.source_name,d.source_url,d.resolved_source_url,
                    d.raw_summary,d.detected_status,d.category_candidate,
                    d.event_date_candidate,d.confidence
                FROM stores s
                JOIN LATERAL(
                    SELECT *
                    FROM discovery_items d
                    WHERE d.store_name_candidate=s.name
                      AND(
                        COALESCE(d.prefecture,'')=COALESCE(s.prefecture,'')
                        OR d.prefecture IS NULL OR s.prefecture IS NULL
                      )
                    ORDER BY
                        CASE WHEN d.rescue_attempted_at IS NULL THEN 0 ELSE 1 END,
                        d.id DESC
                    LIMIT 1
                ) d ON TRUE
                WHERE (s.address IS NULL OR s.address='')
                  AND d.rescue_attempted_at IS NULL
                ORDER BY s.id DESC
                LIMIT %s
            """,(batch_size,))
            rows=cur.fetchall()

    for row in rows:
        (
            store_id,store_name,pref,city,store_address,
            did,title,source_name,source_url,resolved_source_url,
            summary,detected_status,category,event_date,confidence
        )=row
        scanned+=1

        item={
            "store_id":store_id,
            "store_name":store_name,
            "title":title,
        }

        try:
            real_publisher=extract_source_name_from_title(title) or source_name
            item["publisher"]=real_publisher

            relocation=relocate_source(title,real_publisher,source_url)
            item["relocation"]=relocation

            if not relocation.get("ok"):
                reason=relocation.get("reason") or "relocation_failed"
                if reason=="unsupported_publisher":
                    unsupported+=1
                    rescue_status="unsupported_publisher"
                else:
                    failed+=1
                    rescue_status="relocation_failed"

                with psycopg.connect(database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE discovery_items
                            SET rescue_attempted_at=NOW(),
                                rescue_status=%s,
                                rescue_error=%s
                            WHERE id=%s
                        """,(rescue_status,str(reason)[:500],did))
                results.append(item)
                continue

            relocated+=1
            real_url=relocation.get("url")

            facts=fetch_article_facts(
                real_url,
                expected_prefecture=pref,
                expected_store_name=store_name
            )

            item["facts"]={
                "address":facts.get("address"),
                "facility_name":facts.get("facility_name"),
                "floor":facts.get("floor"),
                "postal_code":facts.get("postal_code"),
                "method":facts.get("method"),
                "quality":facts.get("quality"),
                "resolved_url":facts.get("resolved_url")
            }

            addr=facts.get("address")
            facility=facts.get("facility_name")
            floor=facts.get("floor")
            postal=facts.get("postal_code")

            if facts.get("quality") in ("rejected_prefecture_mismatch","rejected_not_street_address"):
                rejected+=1

            new_conf=calculate_confidence(
                title or "",summary or "",detected_status,
                pref,city,event_date,category,addr,facility
            )
            confidence=max(int(confidence or 0),int(new_conf or 0))

            with psycopg.connect(database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE discovery_items
                        SET resolved_source_url=%s,
                            address_candidate=CASE WHEN %s IS NOT NULL THEN %s ELSE address_candidate END,
                            facility_name_candidate=COALESCE(%s,facility_name_candidate),
                            floor_candidate=CASE WHEN %s IS NOT NULL THEN %s ELSE floor_candidate END,
                            postal_code_candidate=CASE WHEN %s IS NOT NULL THEN %s ELSE postal_code_candidate END,
                            confidence=GREATEST(confidence,%s),
                            rescue_attempted_at=NOW(),
                            rescue_status=%s,
                            rescue_error=NULL
                        WHERE id=%s
                    """,(
                        real_url,addr,addr,facility,floor,floor,postal,postal,confidence,
                        "success_address" if addr else "relocated_no_valid_address",
                        did
                    ))

                    if addr:
                        address_found+=1
                        cur.execute("""
                            UPDATE stores
                            SET address=%s,
                                facility_name=COALESCE(%s,facility_name),
                                floor=%s,
                                postal_code=%s,
                                source_url=%s,
                                source_name=COALESCE(%s,source_name),
                                confidence=GREATEST(confidence,%s),
                                updated_at=NOW()
                            WHERE id=%s
                        """,(addr,facility,floor,postal,real_url,real_publisher,confidence,store_id))
                        store_updated+=cur.rowcount

            results.append(item)

        except Exception as e:
            failed+=1
            err=f"{type(e).__name__}: {e}"[:500]
            item["error"]=err
            try:
                with psycopg.connect(database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE discovery_items
                            SET rescue_attempted_at=NOW(),
                                rescue_status='error',
                                rescue_error=%s
                            WHERE id=%s
                        """,(err,did))
            except Exception:
                pass
            results.append(item)

    return {
        "batch_size":batch_size,
        "scanned":scanned,
        "relocated":relocated,
        "address_found":address_found,
        "store_updated":store_updated,
        "rejected_address":rejected,
        "unsupported_publisher":unsupported,
        "failed":failed,
        "results":results
    }
