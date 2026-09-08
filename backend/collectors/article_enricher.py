import re
import httpx
from bs4 import BeautifulSoup
from .text_rules import extract_address, extract_facility_name, extract_floor, extract_postal_code

HEADERS = {
    "User-Agent": "OpenCloseMapBot/1.0 (+public-store-information-index; contact-via-site)"
}

def fetch_article_facts(url: str):
    """
    ベストエフォート取得。
    ログイン・paywall・bot対策回避はしない。
    HTMLが普通に取得できる公開ページだけ処理する。
    """
    result = {
        "resolved_url": url,
        "address": None,
        "facility_name": None,
        "floor": None,
        "postal_code": None,
        "page_title": None,
    }
    if not url or not url.startswith(("http://","https://")):
        return result

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=8.0,
            headers=HEADERS
        ) as client:
            r = client.get(url)
            result["resolved_url"] = str(r.url)
            ctype = (r.headers.get("content-type") or "").lower()
            if r.status_code != 200 or "text/html" not in ctype:
                return result

            # 異常に大きいページを丸ごと解析しない
            html = r.text[:1_500_000]
    except Exception:
        return result

    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script","style","noscript","svg"]):
            tag.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else None
        result["page_title"] = title

        text = soup.get_text(" ", strip=True)
        text = re.sub(r'\s+',' ',text)[:250_000]

        address = extract_address(text)
        result["address"] = address
        result["postal_code"] = extract_postal_code(text)
        result["floor"] = extract_floor(text)
        result["facility_name"] = extract_facility_name(text, address)
    except Exception:
        pass

    return result
