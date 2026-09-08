def promote_candidates(database_url,min_confidence=80):
    import psycopg
    promoted=skipped=0
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,store_name_candidate,detected_status,category_candidate,prefecture,city,event_date_candidate,source_url,source_name,confidence
            FROM discovery_items WHERE processed=FALSE AND confidence >= %s AND detected_status IN ('opening','closing') AND store_name_candidate IS NOT NULL""",(min_confidence,))
            for row in cur.fetchall():
                did,name,ds,cat,pref,city,event,url,sname,conf=row
                status="opening" if ds=="opening" else "closing"; od=event if status=="opening" else None; cd=event if status=="closing" else None
                cur.execute("""SELECT id FROM stores WHERE name=%s AND COALESCE(prefecture,'')=COALESCE(%s,'') AND COALESCE(city,'')=COALESCE(%s,'') AND COALESCE(open_date,DATE '1900-01-01')=COALESCE(%s,DATE '1900-01-01') AND COALESCE(close_date,DATE '1900-01-01')=COALESCE(%s,DATE '1900-01-01') LIMIT 1""",(name,pref,city,od,cd))
                if cur.fetchone():
                    cur.execute("UPDATE discovery_items SET processed=TRUE WHERE id=%s",(did,)); skipped+=1; continue
                cur.execute("""INSERT INTO stores(name,status,category,prefecture,city,open_date,close_date,source_url,source_name,confidence,last_verified_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())""",(name,status,cat,pref,city,od,cd,url,sname,conf))
                cur.execute("UPDATE discovery_items SET processed=TRUE WHERE id=%s",(did,)); promoted+=1
    return {"promoted":promoted,"skipped":skipped,"min_confidence":min_confidence}
