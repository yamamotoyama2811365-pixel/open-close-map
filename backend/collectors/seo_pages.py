from __future__ import annotations

import html
import json
from datetime import date, datetime
from urllib.parse import quote

SITE_NAME = "開店閉店マップ"

CSS = """
:root{
  --navy:#132238;--ink:#243247;--muted:#6b7788;--line:#e5eaf0;
  --bg:#f5f7fa;--white:#fff;--green:#148a62;--green-bg:#eaf7f1;
  --orange:#b96c16;--orange-bg:#fff3e3;--red:#c24848;--red-bg:#fdeeee;
  --blue:#386aa8;--blue-bg:#edf4fc
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,sans-serif;background:var(--bg);color:var(--ink);line-height:1.7}
a{color:inherit;text-decoration:none}
.wrap{width:min(1160px,calc(100% - 32px));margin:0 auto}
.site-header{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}
.header-inner{height:72px;display:flex;align-items:center;gap:26px}
.brand{font-weight:800;font-size:22px;letter-spacing:-.04em;color:var(--navy);white-space:nowrap}
.brand small{display:block;font-size:10px;letter-spacing:.08em;color:#8691a0;font-weight:600;margin-top:-4px}
.nav{display:flex;gap:20px;margin-left:auto;font-size:13px;color:#4d5a6b}
.search-chip{padding:8px 13px;border:1px solid var(--line);border-radius:999px;background:#fafbfd}
.hero{background:linear-gradient(135deg,#15273e,#263d59);color:white;padding:44px 0 40px}
.crumbs{font-size:12px;color:#7b8796;margin:18px 0}
.hero .crumbs{color:#c7d2df;margin:0 0 15px}
h1{font-size:clamp(28px,4vw,42px);line-height:1.3;letter-spacing:-.04em;margin:0 0 12px}
.hero p{margin:0;color:#dce5ee;max-width:760px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:26px;max-width:760px}
.stat{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.16);border-radius:14px;padding:13px 16px}
.stat strong{font-size:22px;display:block}
.stat span{font-size:11px;color:#d4deea}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:28px;padding:28px 0 56px}
.panel{background:#fff;border:1px solid var(--line);border-radius:18px;padding:22px}
.panel+.panel{margin-top:18px}
.section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:15px;margin-bottom:15px}
.section-head h2{margin:0;color:var(--navy);font-size:22px;letter-spacing:-.03em}
.section-head p{margin:0;color:var(--muted);font-size:12px}
.store-list{display:grid;gap:12px}
.store-card{display:grid;grid-template-columns:110px 1fr auto;gap:16px;align-items:center;padding:16px;border:1px solid var(--line);border-radius:15px;background:#fff;transition:.15s}
.store-card:hover{border-color:#bdc9d6;transform:translateY(-1px);box-shadow:0 8px 24px rgba(30,48,72,.06)}
.store-date{font-size:12px;color:var(--muted)}
.store-main h3{font-size:17px;margin:4px 0 3px;line-height:1.45;color:var(--navy)}
.store-main p{font-size:12px;color:var(--muted);margin:0}
.badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;font-size:11px;font-weight:700;white-space:nowrap}
.badge.opening,.badge.open{background:var(--green-bg);color:var(--green)}
.badge.closing,.badge.closed{background:var(--red-bg);color:var(--red)}
.badge.tenant{background:var(--blue-bg);color:var(--blue)}
.arrow{font-size:20px;color:#a6afbb}
.facets{display:flex;flex-wrap:wrap;gap:8px}
.facet{display:inline-flex;padding:8px 11px;border:1px solid var(--line);background:#fff;border-radius:10px;font-size:12px}
.facet:hover{background:#f7f9fb;border-color:#c8d2dd}
.facet strong{margin-left:6px;color:var(--muted)}
.side-title{margin:0 0 12px;font-size:16px;color:var(--navy)}
.side-copy{font-size:12px;color:var(--muted);margin:-4px 0 13px}
.detail-grid{display:grid;grid-template-columns:160px 1fr;border-top:1px solid var(--line)}
.detail-grid dt,.detail-grid dd{margin:0;padding:12px 8px;border-bottom:1px solid var(--line);font-size:13px}
.detail-grid dt{color:var(--muted);font-weight:600}
.detail-grid dd{font-weight:500}
.source-link,.official-link{display:inline-flex;margin-top:12px;margin-right:8px;padding:9px 12px;border-radius:10px;border:1px solid var(--line);font-size:12px;background:#fff}
.official-link{background:var(--navy);color:#fff;border-color:var(--navy)}
.map{overflow:hidden;border-radius:14px;border:1px solid var(--line);margin-top:16px;height:320px}
.map iframe{border:0;width:100%;height:100%}
.notice{padding:13px 15px;background:#f7f9fb;border-radius:12px;color:#657284;font-size:12px;margin-top:16px}
.empty{padding:38px 18px;text-align:center;color:var(--muted);font-size:13px;border:1px dashed #ced6df;border-radius:14px}
.pagination{display:flex;justify-content:center;gap:8px;margin-top:18px}
.pagination a{padding:8px 12px;background:#fff;border:1px solid var(--line);border-radius:9px;font-size:12px}
.footer{background:#101d2e;color:#c6d0dc;padding:34px 0;margin-top:20px;font-size:12px}
.footer strong{display:block;color:white;font-size:17px;margin-bottom:6px}
.footer-links{display:flex;gap:18px;flex-wrap:wrap;margin-top:13px}
@media(max-width:820px){
  .nav{display:none}.header-inner{height:62px}.layout{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr 1fr}
  .store-card{grid-template-columns:1fr auto}.store-date{grid-column:1/-1;margin-bottom:-9px}
  .detail-grid{grid-template-columns:115px 1fr}.side{order:2}
}
@media(max-width:520px){
  .wrap{width:min(100% - 22px,1160px)}.hero{padding:32px 0}.stats{grid-template-columns:1fr}
  .panel{padding:16px;border-radius:14px}.store-card{padding:13px}.section-head{display:block}.section-head p{margin-top:4px}
}
"""

def _connect(database_url):
    import psycopg
    return psycopg.connect(database_url)

def esc(value):
    return html.escape(str(value or ""), quote=True)

def qpath(value):
    return quote(str(value or ""), safe="")

def site_url(origin, path):
    return origin.rstrip("/") + path

def fmt_date(value):
    if not value:
        return "日付未確認"
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except Exception:
            return esc(value)
    return f"{value.year}年{value.month}月{value.day}日"

def event_date(row):
    status = row.get("status") or ""
    return row.get("close_date") if status in ("closed","closing") else row.get("open_date")

def status_info(status, event=None):
    today = date.today()
    d = event
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except Exception:
            d = None
    if status in ("closing","closed"):
        if d and d <= today:
            return "閉店", "closed"
        return "閉店予定", "closing"
    if status in ("opening","open"):
        if d and d <= today:
            return "開店", "open"
        return "開店予定", "opening"
    if status == "tenant":
        return "テナント募集", "tenant"
    return "店舗情報", "opening"

def row_to_dict(r):
    return {
        "id":r[0],"name":r[1],"status":r[2],"category":r[3],
        "prefecture":r[4],"city":r[5],"address":r[6],
        "facility_name":r[7],"floor":r[8],"postal_code":r[9],
        "open_date":r[10],"close_date":r[11],
        "source_url":r[12],"source_name":r[13],"official_url":r[14],
        "confidence":r[15],"last_verified_at":r[16]
    }

STORE_SELECT = """
    SELECT
        id,name,status,category,prefecture,city,address,
        facility_name,floor,postal_code,
        open_date,close_date,source_url,source_name,official_url,
        confidence,last_verified_at
    FROM stores
"""

def page_shell(origin, title, description, canonical_path, body, json_ld=None, noindex=False):
    canonical = site_url(origin, canonical_path)
    robot = "noindex,follow" if noindex else "index,follow,max-image-preview:large"
    json_ld_html = ""
    if json_ld:
        json_ld_html = '<script type="application/ld+json">' + json.dumps(
            json_ld, ensure_ascii=False, separators=(",",":")
        ).replace("</","<\\/") + "</script>"
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="{robot}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary">
<style>{CSS}</style>
{json_ld_html}
</head>
<body>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/">{SITE_NAME}<small>OPEN / CLOSE DATABASE</small></a>
    <nav class="nav">
      <a href="/area/北海道">エリアから探す</a>
      <a href="/category/飲食">業種から探す</a>
      <a href="/#latest">最新情報</a>
      <a class="search-chip" href="/">店舗を検索</a>
    </nav>
  </div>
</header>
{body}
<footer class="footer">
  <div class="wrap">
    <strong>{SITE_NAME}</strong>
    全国の開店・閉店・店舗情報をエリア・業種ごとに確認できる店舗情報データベースです。
    <div class="footer-links">
      <a href="/">トップ</a><a href="/area/北海道">エリア</a><a href="/category/飲食">業種</a>
    </div>
  </div>
</footer>
</body>
</html>"""

def store_cards(rows):
    if not rows:
        return '<div class="empty">現在掲載できる店舗情報はありません。</div>'
    out = ['<div class="store-list">']
    for r in rows:
        d = row_to_dict(r)
        ev = event_date(d)
        label, cls = status_info(d["status"], ev)
        area = " ".join(x for x in [d["prefecture"], d["city"]] if x)
        cat = d["category"] or "業種未分類"
        out.append(f"""
<a class="store-card" href="/store/{d['id']}">
  <div class="store-date">{fmt_date(ev)}</div>
  <div class="store-main">
    <span class="badge {cls}">{esc(label)}</span>
    <h3>{esc(d['name'])}</h3>
    <p>{esc(area)}　・　{esc(cat)}</p>
  </div>
  <div class="arrow">›</div>
</a>""")
    out.append("</div>")
    return "".join(out)

def breadcrumb_json(origin, items):
    return {
        "@context":"https://schema.org",
        "@type":"BreadcrumbList",
        "itemListElement":[
            {"@type":"ListItem","position":i+1,"name":name,"item":site_url(origin,path)}
            for i,(name,path) in enumerate(items)
        ]
    }

def render_area(database_url, origin, prefecture, city=None, page=1, per_page=40):
    prefecture = (prefecture or "").strip()
    city = (city or "").strip() or None
    page = max(1,int(page))
    offset = (page-1)*per_page

    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            clauses = ["COALESCE(status,'') <> 'excluded'","prefecture=%s"]
            params = [prefecture]
            if city:
                clauses.append("city=%s")
                params.append(city)
            where = " AND ".join(clauses)

            cur.execute(f"""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER(WHERE status IN('open','opening')),
                    COUNT(*) FILTER(WHERE status IN('closed','closing'))
                FROM stores WHERE {where}
            """,params)
            total,opens,closes = cur.fetchone()

            cur.execute(STORE_SELECT + f"""
                WHERE {where}
                ORDER BY COALESCE(open_date,close_date,created_at::date) DESC NULLS LAST,id DESC
                LIMIT %s OFFSET %s
            """,params+[per_page,offset])
            rows = cur.fetchall()

            if city:
                cur.execute("""
                    SELECT COALESCE(category,'業種未分類'),COUNT(*)
                    FROM stores
                    WHERE COALESCE(status,'') <> 'excluded'
                      AND prefecture=%s AND city=%s
                    GROUP BY COALESCE(category,'業種未分類')
                    ORDER BY COUNT(*) DESC,1
                    LIMIT 18
                """,(prefecture,city))
                facets = cur.fetchall()
                facet_type = "category"
            else:
                cur.execute("""
                    SELECT city,COUNT(*)
                    FROM stores
                    WHERE COALESCE(status,'') <> 'excluded'
                      AND prefecture=%s
                      AND city IS NOT NULL AND city<>''
                    GROUP BY city
                    ORDER BY COUNT(*) DESC,city
                    LIMIT 30
                """,(prefecture,))
                facets = cur.fetchall()
                facet_type = "city"

    area_name = f"{prefecture}{city or ''}"
    if city:
        title = f"{city}の開店・閉店情報｜最新店舗一覧｜{SITE_NAME}"
        desc = f"{prefecture}{city}の開店・閉店情報を掲載。新規オープン、閉店予定、閉店した店舗を住所・日付・業種から確認できます。"
        canonical_path = f"/area/{qpath(prefecture)}/{qpath(city)}"
        crumbs = [("トップ","/"),(prefecture,f"/area/{qpath(prefecture)}"),(city,canonical_path)]
    else:
        title = f"{prefecture}の開店・閉店情報｜新店・閉店一覧｜{SITE_NAME}"
        desc = f"{prefecture}の開店・閉店情報を市区町村別に掲載。新規オープン、閉店予定、閉店した店舗の最新情報を確認できます。"
        canonical_path = f"/area/{qpath(prefecture)}"
        crumbs = [("トップ","/"),(prefecture,canonical_path)]

    if page > 1:
        title = f"{title}（{page}ページ）"
        canonical_path += f"?page={page}"

    facet_html = []
    for name,count in facets:
        if not name:
            continue
        href = f"/area/{qpath(prefecture)}/{qpath(name)}" if facet_type=="city" else f"/category/{qpath(name)}"
        facet_html.append(f'<a class="facet" href="{href}">{esc(name)} <strong>{count}</strong></a>')

    prev_next = []
    base_path = f"/area/{qpath(prefecture)}" + (f"/{qpath(city)}" if city else "")
    if page > 1:
        p = page-1
        prev_next.append(f'<a href="{base_path}' + (f'?page={p}' if p>1 else '') + '">‹ 前へ</a>')
    if offset + len(rows) < total:
        prev_next.append(f'<a href="{base_path}?page={page+1}">次へ ›</a>')

    body = f"""
<section class="hero">
  <div class="wrap">
    <div class="crumbs">トップ　›　{esc(prefecture)}{('　›　'+esc(city)) if city else ''}</div>
    <h1>{esc(area_name)}の開店・閉店情報</h1>
    <p>{esc(area_name)}で確認された新規オープン、開店予定、閉店予定、閉店店舗の情報をまとめています。</p>
    <div class="stats">
      <div class="stat"><strong>{total}</strong><span>掲載店舗情報</span></div>
      <div class="stat"><strong>{opens}</strong><span>開店・開店予定</span></div>
      <div class="stat"><strong>{closes}</strong><span>閉店・閉店予定</span></div>
    </div>
  </div>
</section>
<div class="wrap layout">
  <main>
    <section class="panel">
      <div class="section-head">
        <div><h2>最新の店舗情報</h2><p>{esc(area_name)}の開店・閉店情報</p></div>
        <p>{total}件中 {offset+1 if total else 0}〜{min(offset+len(rows),total)}件</p>
      </div>
      {store_cards(rows)}
      <div class="pagination">{''.join(prev_next)}</div>
    </section>
  </main>
  <aside class="side">
    <section class="panel">
      <h2 class="side-title">{'業種から探す' if city else '市区町村から探す'}</h2>
      <p class="side-copy">{esc(area_name)}の情報をさらに絞り込めます。</p>
      <div class="facets">{''.join(facet_html) if facet_html else '<span class="side-copy">分類データを蓄積中です。</span>'}</div>
    </section>
    <section class="panel">
      <h2 class="side-title">掲載情報について</h2>
      <p class="side-copy">店舗の開店・閉店状況は変更される場合があります。最終確認は店舗公式情報・掲載元をご確認ください。</p>
    </section>
  </aside>
</div>"""
    return page_shell(origin,title,desc,canonical_path,body,breadcrumb_json(origin,crumbs),noindex=(total==0))

def render_category(database_url, origin, category, page=1, per_page=40):
    category = (category or "").strip()
    page = max(1,int(page))
    offset = (page-1)*per_page

    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER(WHERE status IN('open','opening')),
                    COUNT(*) FILTER(WHERE status IN('closed','closing'))
                FROM stores
                WHERE COALESCE(status,'') <> 'excluded'
                  AND COALESCE(category,'業種未分類')=%s
            """,(category,))
            total,opens,closes = cur.fetchone()

            cur.execute(STORE_SELECT + """
                WHERE COALESCE(status,'') <> 'excluded'
                  AND COALESCE(category,'業種未分類')=%s
                ORDER BY COALESCE(open_date,close_date,created_at::date) DESC NULLS LAST,id DESC
                LIMIT %s OFFSET %s
            """,(category,per_page,offset))
            rows = cur.fetchall()

            cur.execute("""
                SELECT prefecture,COUNT(*)
                FROM stores
                WHERE COALESCE(status,'') <> 'excluded'
                  AND COALESCE(category,'業種未分類')=%s
                  AND prefecture IS NOT NULL AND prefecture<>''
                GROUP BY prefecture
                ORDER BY COUNT(*) DESC,prefecture
                LIMIT 30
            """,(category,))
            prefs = cur.fetchall()

    canonical_path = f"/category/{qpath(category)}"
    title = f"{category}の開店・閉店情報｜全国の新店・閉店一覧｜{SITE_NAME}"
    if page > 1:
        title += f"（{page}ページ）"
        canonical_path += f"?page={page}"
    desc = f"全国の「{category}」に関する開店・閉店情報。新規オープン、開店予定、閉店予定、閉店店舗をエリア別に確認できます。"

    facets = "".join(
        f'<a class="facet" href="/area/{qpath(pref)}">{esc(pref)} <strong>{count}</strong></a>'
        for pref,count in prefs if pref
    )
    prev_next=[]
    if page>1:
        prev_next.append(f'<a href="/category/{qpath(category)}' + (f'?page={page-1}' if page-1>1 else '') + '">‹ 前へ</a>')
    if offset+len(rows)<total:
        prev_next.append(f'<a href="/category/{qpath(category)}?page={page+1}">次へ ›</a>')

    body=f"""
<section class="hero">
  <div class="wrap">
    <div class="crumbs">トップ　›　業種　›　{esc(category)}</div>
    <h1>{esc(category)}の開店・閉店情報</h1>
    <p>全国の{esc(category)}に関する新規オープン、開店予定、閉店予定、閉店店舗を一覧で確認できます。</p>
    <div class="stats">
      <div class="stat"><strong>{total}</strong><span>掲載店舗情報</span></div>
      <div class="stat"><strong>{opens}</strong><span>開店・開店予定</span></div>
      <div class="stat"><strong>{closes}</strong><span>閉店・閉店予定</span></div>
    </div>
  </div>
</section>
<div class="wrap layout">
  <main>
    <section class="panel">
      <div class="section-head">
        <div><h2>最新の{esc(category)}情報</h2><p>全国の店舗動向</p></div>
        <p>{total}件中 {offset+1 if total else 0}〜{min(offset+len(rows),total)}件</p>
      </div>
      {store_cards(rows)}
      <div class="pagination">{''.join(prev_next)}</div>
    </section>
  </main>
  <aside class="side">
    <section class="panel">
      <h2 class="side-title">エリアから探す</h2>
      <p class="side-copy">{esc(category)}の掲載件数がある都道府県です。</p>
      <div class="facets">{facets or '<span class="side-copy">地域データを蓄積中です。</span>'}</div>
    </section>
  </aside>
</div>"""
    crumbs=[("トップ","/"),("業種","/"),(category,canonical_path.split("?")[0])]
    return page_shell(origin,title,desc,canonical_path,body,breadcrumb_json(origin,crumbs),noindex=(total==0))

def render_store(database_url, origin, store_id):
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(STORE_SELECT + """
                WHERE id=%s AND COALESCE(status,'') <> 'excluded'
            """,(store_id,))
            r=cur.fetchone()
            if not r:
                return None
            d=row_to_dict(r)

            cur.execute("""
                SELECT id,name,status,category,prefecture,city,address,
                       facility_name,floor,postal_code,open_date,close_date,
                       source_url,source_name,official_url,confidence,last_verified_at
                FROM stores
                WHERE id<>%s
                  AND COALESCE(status,'') <> 'excluded'
                  AND COALESCE(prefecture,'')=COALESCE(%s,'')
                  AND COALESCE(city,'')=COALESCE(%s,'')
                ORDER BY COALESCE(open_date,close_date,created_at::date) DESC NULLS LAST,id DESC
                LIMIT 6
            """,(store_id,d["prefecture"],d["city"]))
            nearby=cur.fetchall()

    ev=event_date(d)
    label,cls=status_info(d["status"],ev)
    area="".join(x for x in [d["prefecture"],d["city"]] if x)
    title=f"{d['name']}の開店・閉店情報｜{area or '店舗情報'}｜{SITE_NAME}"
    desc=f"{area}の「{d['name']}」の{label}情報。所在地、日付、業種、掲載元などを確認できます。"
    canonical_path=f"/store/{d['id']}"

    rows=[
        ("店舗名",d["name"]),("状況",label),("日付",fmt_date(ev)),
        ("業種",d["category"] or "未分類"),("所在地",d["address"] or area or "未確認")
    ]
    if d["facility_name"]: rows.append(("施設名",d["facility_name"]))
    if d["floor"]: rows.append(("階",d["floor"]))
    if d["postal_code"]: rows.append(("郵便番号",d["postal_code"]))
    if d["last_verified_at"]:
        v=d["last_verified_at"]
        rows.append(("最終確認",v.strftime("%Y年%m月%d日") if hasattr(v,"strftime") else str(v)[:10]))

    detail_html="".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k,v in rows)

    links=""
    if d["official_url"]:
        links += f'<a class="official-link" href="{esc(d["official_url"])}" target="_blank" rel="noopener">公式情報を確認 ↗</a>'
    if d["source_url"]:
        links += f'<a class="source-link" href="{esc(d["source_url"])}" target="_blank" rel="noopener">掲載元：{esc(d["source_name"] or "掲載元")} ↗</a>'

    map_html=""
    if d["address"]:
        map_src="https://www.google.com/maps?q="+quote(d["address"])+"&output=embed"
        map_html=f'<div class="map"><iframe loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="{esc(map_src)}" title="{esc(d["name"])}の地図"></iframe></div>'

    area_links=[]
    if d["prefecture"]:
        area_links.append(f'<a class="facet" href="/area/{qpath(d["prefecture"])}">{esc(d["prefecture"])}</a>')
    if d["prefecture"] and d["city"]:
        area_links.append(f'<a class="facet" href="/area/{qpath(d["prefecture"])}/{qpath(d["city"])}">{esc(d["city"])}</a>')
    if d["category"]:
        area_links.append(f'<a class="facet" href="/category/{qpath(d["category"])}">{esc(d["category"])}</a>')

    body=f"""
<section class="hero">
  <div class="wrap">
    <div class="crumbs">トップ　›　{esc(d["prefecture"] or "全国")}　›　{esc(d["city"] or "")}</div>
    <span class="badge {cls}">{esc(label)}</span>
    <h1 style="margin-top:12px">{esc(d["name"])}</h1>
    <p>{esc(area)}の店舗情報。{fmt_date(ev)}の{esc(label)}情報として掲載しています。</p>
  </div>
</section>
<div class="wrap layout">
  <main>
    <section class="panel">
      <div class="section-head"><div><h2>店舗情報</h2><p>{esc(d["name"])}</p></div></div>
      <dl class="detail-grid">{detail_html}</dl>
      {links}
      {map_html}
      <div class="notice">掲載内容は確認時点の情報です。営業状況・開閉店日などは変更される場合があるため、必要に応じて公式情報・掲載元をご確認ください。</div>
    </section>
    <section class="panel">
      <div class="section-head"><div><h2>周辺の開店・閉店情報</h2><p>{esc(area)}の関連店舗</p></div></div>
      {store_cards(nearby)}
    </section>
  </main>
  <aside class="side">
    <section class="panel">
      <h2 class="side-title">この店舗を絞り込み</h2>
      <div class="facets">{''.join(area_links)}</div>
    </section>
  </aside>
</div>"""

    crumbs=[("トップ","/")]
    if d["prefecture"]:
        crumbs.append((d["prefecture"],f'/area/{qpath(d["prefecture"])}'))
    if d["prefecture"] and d["city"]:
        crumbs.append((d["city"],f'/area/{qpath(d["prefecture"])}/{qpath(d["city"])}'))
    crumbs.append((d["name"],canonical_path))

    ld={
      "@context":"https://schema.org",
      "@graph":[
        breadcrumb_json(origin,crumbs),
        {
          "@type":"WebPage",
          "@id":site_url(origin,canonical_path),
          "url":site_url(origin,canonical_path),
          "name":title,
          "description":desc,
          "isPartOf":{"@type":"WebSite","name":SITE_NAME,"url":origin.rstrip("/")+"/"},
          "about":{"@type":"Thing","name":d["name"]}
        }
      ]
    }
    return page_shell(origin,title,desc,canonical_path,body,ld)

def sitemap_xml(database_url, origin, max_urls=45000):
    urls=[origin.rstrip("/")+"/"]
    with _connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT prefecture FROM stores
                WHERE COALESCE(status,'') <> 'excluded'
                  AND prefecture IS NOT NULL AND prefecture<>''
                ORDER BY prefecture
            """)
            for (pref,) in cur.fetchall():
                urls.append(site_url(origin,f"/area/{qpath(pref)}"))

            cur.execute("""
                SELECT DISTINCT prefecture,city FROM stores
                WHERE COALESCE(status,'') <> 'excluded'
                  AND prefecture IS NOT NULL AND prefecture<>''
                  AND city IS NOT NULL AND city<>''
                ORDER BY prefecture,city
            """)
            for pref,city in cur.fetchall():
                urls.append(site_url(origin,f"/area/{qpath(pref)}/{qpath(city)}"))

            cur.execute("""
                SELECT DISTINCT COALESCE(category,'業種未分類') FROM stores
                WHERE COALESCE(status,'') <> 'excluded' ORDER BY 1
            """)
            for (cat,) in cur.fetchall():
                urls.append(site_url(origin,f"/category/{qpath(cat)}"))

            remain=max(0,max_urls-len(urls))
            cur.execute("""
                SELECT id,updated_at FROM stores
                WHERE COALESCE(status,'') <> 'excluded'
                ORDER BY updated_at DESC NULLS LAST,id DESC
                LIMIT %s
            """,(remain,))
            store_rows=cur.fetchall()

    entries=[f"<url><loc>{html.escape(u)}</loc></url>" for u in urls[:max_urls]]
    for sid,updated in store_rows:
        u=site_url(origin,f"/store/{sid}")
        lm=f"<lastmod>{updated.date().isoformat()}</lastmod>" if updated else ""
        entries.append(f"<url><loc>{html.escape(u)}</loc>{lm}</url>")

    return '<?xml version="1.0" encoding="UTF-8"?>' + \
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + \
           "".join(entries[:max_urls]) + '</urlset>'

def robots_txt(origin):
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        f"Sitemap: {origin.rstrip('/')}/sitemap.xml\n"
    )
