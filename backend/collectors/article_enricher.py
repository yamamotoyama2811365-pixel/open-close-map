import json
import re
import httpx
from bs4 import BeautifulSoup
from .text_rules import (
    extract_address,extract_facility_name,extract_floor,extract_postal_code,
    detect_prefecture,detect_city,norm
)

HEADERS={
    "User-Agent":"Mozilla/5.0 (compatible; OpenCloseMap/1.0; +https://open-close-map.onrender.com)",
    "Accept-Language":"ja,en;q=0.8",
}

def _jsonld_candidates(soup):
    out=[]
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        raw=tag.string or tag.get_text(" ",strip=True)
        if not raw:continue
        try:
            data=json.loads(raw)
            out.append(data)
        except Exception:
            continue
    return out

def _walk_jsonld(obj, found):
    if isinstance(obj,dict):
        addr=obj.get("address")
        if isinstance(addr,dict):
            pieces=[
                addr.get("postalCode"),addr.get("addressRegion"),
                addr.get("addressLocality"),addr.get("streetAddress")
            ]
            value=" ".join(str(x) for x in pieces if x)
            if value:found["addresses"].append(value)
        elif isinstance(addr,str):
            found["addresses"].append(addr)

        name=obj.get("name")
        typ=obj.get("@type")
        if name and typ in ("LocalBusiness","Store","Restaurant","Hotel","Organization","Place"):
            found["names"].append(str(name))

        for v in obj.values():_walk_jsonld(v,found)

    elif isinstance(obj,list):
        for x in obj:_walk_jsonld(x,found)

def _extract_from_tables(soup):
    pairs={}
    labels={"所在地","住所","店舗所在地","施設所在地","名称","名 称","店舗名","施設名","ホテル名","店名"}

    for tr in soup.find_all("tr"):
        cells=tr.find_all(["th","td"])
        if len(cells)>=2:
            key=norm(cells[0].get_text(" ",strip=True)).strip("［］【】[]")
            val=norm(" ".join(c.get_text(" ",strip=True) for c in cells[1:]))
            if key in labels and val:pairs[key]=val

    for dl in soup.find_all("dl"):
        dts=dl.find_all("dt")
        for dt in dts:
            key=norm(dt.get_text(" ",strip=True)).strip("［］【】[]")
            dd=dt.find_next_sibling("dd")
            if key in labels and dd:
                val=norm(dd.get_text(" ",strip=True))
                if val:pairs[key]=val

    return pairs

def fetch_article_facts(url):
    result={
        "requested_url":url,
        "resolved_url":url,
        "address":None,
        "facility_name":None,
        "floor":None,
        "postal_code":None,
        "prefecture":None,
        "city":None,
        "page_title":None,
        "method":None,
    }

    if not url or not url.startswith(("http://","https://")):
        return result

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=12.0,
            headers=HEADERS
        ) as client:
            r=client.get(url)
            result["resolved_url"]=str(r.url)
            ctype=(r.headers.get("content-type") or "").lower()
            if r.status_code!=200 or "text/html" not in ctype:
                return result
            html=r.text[:2_000_000]
    except Exception:
        return result

    try:
        soup=BeautifulSoup(html,"html.parser")
        result["page_title"]=soup.title.get_text(" ",strip=True) if soup.title else None

        # JSON-LD
        found={"addresses":[],"names":[]}
        for obj in _jsonld_candidates(soup):
            _walk_jsonld(obj,found)

        for raw_addr in found["addresses"]:
            addr=extract_address(raw_addr) or norm(raw_addr)
            if detect_prefecture(addr):
                result["address"]=addr
                result["postal_code"]=extract_postal_code(raw_addr)
                result["facility_name"]=found["names"][0] if found["names"] else None
                result["method"]="jsonld"
                break

        # table/dl overview
        pairs=_extract_from_tables(soup)
        if not result["address"]:
            for k in ["所在地","店舗所在地","施設所在地","住所"]:
                if k in pairs:
                    raw=pairs[k]
                    addr=extract_address(f"［所在地］ {raw}") or raw
                    if detect_prefecture(addr):
                        result["address"]=addr
                        result["postal_code"]=extract_postal_code(raw)
                        result["method"]="table"
                        break

        if not result["facility_name"]:
            for k in ["名称","名 称","店舗名","施設名","ホテル名","店名"]:
                if k in pairs:
                    result["facility_name"]=pairs[k]
                    break

        # Visible text: preserve line breaks because PR TIMES overview often relies on them
        for tag in soup(["script","style","noscript","svg"]):
            tag.decompose()
        text=soup.get_text("\n",strip=True)
        text=re.sub(r'\n{3,}','\n\n',text)[:350_000]

        if not result["address"]:
            result["address"]=extract_address(text)
            if result["address"]:result["method"]="visible-text"

        if not result["postal_code"]:
            result["postal_code"]=extract_postal_code(text)

        if not result["facility_name"]:
            result["facility_name"]=extract_facility_name(text,result["address"])

        result["floor"]=extract_floor(
            (result["address"] or "")+" "+(result["facility_name"] or "")+" "+text[:50000]
        )
        result["prefecture"]=detect_prefecture(result["address"] or text)
        result["city"]=detect_city(result["address"] or text)

    except Exception:
        pass

    return result
