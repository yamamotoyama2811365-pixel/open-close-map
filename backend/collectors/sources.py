from urllib.parse import quote_plus

def google_news_rss(query: str):
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"

RSS_SOURCES = [
    {"name": "Google News - 開店", "url": google_news_rss('"開店" OR "オープン" 店舗'), "limit": 60},
    {"name": "Google News - 閉店", "url": google_news_rss('"閉店" 店舗'), "limit": 60},
    {"name": "Google News - 新店舗", "url": google_news_rss('"新店舗" OR "新店"'), "limit": 50},
    {"name": "Google News - テナント", "url": google_news_rss('"テナント募集" OR "居抜き"'), "limit": 40},
]
