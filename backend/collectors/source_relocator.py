import re
from difflib import SequenceMatcher
from urllib.parse import quote_plus, urljoin
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent":"Mozilla/5.0 (compatible; OpenCloseMap/1.0; +https://open-close-map.onrender.com)",
    "Accept-Language":"ja,en;q=0.8",
}

def clean_news_title(title: str):
    if not title:
        return ""
    t = re.sub(r'\s*[-｜|]\s*PR TIMES\s*$', '', title, flags=re.I)
    t = re.sub(r'\s*[-｜|]\s*[^-｜|]{1,40}$', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def compact(s: str):
    return re.sub(r'[\s　「」『』【】\[\]（）()・,，。.!！?？:：\-ー_]', '', s or '').lower()

def similarity(a: str, b: str):
    aa, bb = compact(a), compact(b)
    if not aa or not bb:
        return 0.0
    if aa in bb or bb in aa:
        return 0.93
    return SequenceMatcher(None, aa, bb).ratio()

def prtimes_search(title: str):
    """
    PR TIMES public keyword search.
    Finds /main/html/rd/p/... candidates and chooses best title similarity.
    """
    target = clean_news_title(title)
    if not target:
        return {"ok":False,"reason":"empty_title"}

    # Use distinctive chunks rather than entire long headline
    q = target[:70]
    url = "https://prtimes.jp/main/action.php?page=searchkey&search_word=" + quote_plus(q)

    try:
        with httpx.Client(follow_redirects=True, timeout=12.0, headers=HEADERS) as client:
            r = client.get(url)
            if r.status_code != 200:
                return {"ok":False,"reason":f"http_{r.status_code}","search_url":url}
            soup = BeautifulSoup(r.text[:1_500_000], "html.parser")
    except Exception as e:
        return {"ok":False,"reason":"request_failed","error":str(e)[:180],"search_url":url}

    candidates = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href","")
        if "/main/html/rd/p/" not in href:
            continue
        full = urljoin("https://prtimes.jp", href)
        if full in seen:
            continue
        seen.add(full)
        text = re.sub(r'\s+',' ',a.get_text(" ",strip=True))
        if not text:
            # Sometimes title is in surrounding parent
            parent = a.parent
            text = re.sub(r'\s+',' ',parent.get_text(" ",strip=True)) if parent else ""
        score = similarity(target, text)
        candidates.append({"url":full,"title":text[:250],"score":round(score,4)})

    candidates.sort(key=lambda x:x["score"], reverse=True)

    if not candidates:
        return {"ok":False,"reason":"no_candidates","search_url":url}

    best = candidates[0]
    # Conservative threshold to avoid attaching a wrong article.
    if best["score"] < 0.52:
        return {
            "ok":False,
            "reason":"low_similarity",
            "search_url":url,
            "best":best,
            "candidates":candidates[:3]
        }

    return {
        "ok":True,
        "method":"prtimes_search",
        "url":best["url"],
        "matched_title":best["title"],
        "score":best["score"],
        "search_url":url
    }

def relocate_source(title: str, source_name: str = "", source_url: str = ""):
    hay = f"{title or ''} {source_name or ''}"
    if "PR TIMES" in hay.upper():
        return prtimes_search(title)

    # Other publishers will be added source-by-source.
    return {
        "ok":False,
        "reason":"unsupported_publisher",
        "publisher":source_name,
        "source_url":source_url
    }
