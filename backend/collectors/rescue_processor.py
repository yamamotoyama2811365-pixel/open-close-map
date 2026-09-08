from .source_relocator import relocate_source
from .article_enricher import fetch_article_facts
from .text_rules import calculate_confidence

def rescue_sources(database_url, batch_size=5):
    import psycopg

    scanned = relocated = address_found = store_updated = unsupported = failed = 0
    results = []

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    s.id, s.name, s.prefecture, s.city, s.address,
                    d.id, d.title, d.source_name, d.source_url, d.resolved_source_url,
                    d.raw_summary, d.detected_status, d.category_candidate,
                    d.event_date_candidate, d.confidence
                FROM stores s
                JOIN LATERAL (
                    SELECT *
                    FROM discovery_items d
                    WHERE d.store_name_candidate = s.name
                      AND (
                        COALESCE(d.prefecture,'') = COALESCE(s.prefecture,'')
                        OR d.prefecture IS NULL
                        OR s.prefecture IS NULL
                      )
                    ORDER BY d.id DESC
                    LIMIT 1
                ) d ON TRUE
                WHERE (s.address IS NULL OR s.address='')
                ORDER BY s.id DESC
                LIMIT %s
            """,(batch_size,))
            rows = cur.fetchall()

            for row in rows:
                (
                    store_id, store_name, pref, city, store_address,
                    did, title, source_name, source_url, resolved_source_url,
                    summary, detected_status, category, event_date, confidence
                ) = row

                scanned += 1
                relocation = relocate_source(title, source_name, source_url)

                item = {
                    "store_id":store_id,
                    "store_name":store_name,
                    "title":title,
                    "relocation":relocation
                }

                if not relocation.get("ok"):
                    if relocation.get("reason") == "unsupported_publisher":
                        unsupported += 1
                    else:
                        failed += 1
                    results.append(item)
                    continue

                relocated += 1
                real_url = relocation.get("url")
                facts = fetch_article_facts(real_url)

                addr = facts.get("address")
                facility = facts.get("facility_name")
                floor = facts.get("floor")
                postal = facts.get("postal_code")
                final_pref = pref or facts.get("prefecture")
                final_city = city or facts.get("city")

                item["facts"] = {
                    "address":addr,
                    "facility_name":facility,
                    "floor":floor,
                    "postal_code":postal,
                    "method":facts.get("method"),
                    "resolved_url":facts.get("resolved_url")
                }

                new_conf = calculate_confidence(
                    title or "", summary or "", detected_status,
                    final_pref, final_city, event_date, category,
                    addr, facility
                )
                confidence = max(int(confidence or 0), int(new_conf or 0))

                cur.execute("""
                    UPDATE discovery_items
                    SET resolved_source_url=%s,
                        address_candidate=COALESCE(address_candidate,%s),
                        facility_name_candidate=COALESCE(facility_name_candidate,%s),
                        floor_candidate=COALESCE(floor_candidate,%s),
                        postal_code_candidate=COALESCE(postal_code_candidate,%s),
                        confidence=GREATEST(confidence,%s)
                    WHERE id=%s
                """,(real_url,addr,facility,floor,postal,confidence,did))

                if addr:
                    address_found += 1
                    cur.execute("""
                        UPDATE stores
                        SET address=COALESCE(address,%s),
                            facility_name=COALESCE(facility_name,%s),
                            floor=COALESCE(floor,%s),
                            postal_code=COALESCE(postal_code,%s),
                            source_url=%s,
                            confidence=GREATEST(confidence,%s),
                            updated_at=NOW()
                        WHERE id=%s
                    """,(addr,facility,floor,postal,real_url,confidence,store_id))
                    store_updated += cur.rowcount

                results.append(item)

    return {
        "batch_size":batch_size,
        "scanned":scanned,
        "relocated":relocated,
        "address_found":address_found,
        "store_updated":store_updated,
        "unsupported_publisher":unsupported,
        "failed":failed,
        "results":results
    }
