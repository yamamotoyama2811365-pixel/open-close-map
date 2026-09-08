import re
from datetime import date
OPEN_KEYWORDS=["オープン","OPEN","開店","新店舗","新店","グランドオープン","リニューアルオープン","出店"]
CLOSE_KEYWORDS=["閉店","閉館","営業終了","撤退"]
TENANT_KEYWORDS=["テナント募集","居抜き","空き店舗","貸店舗"]
PREFECTURES=["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"]
CATEGORY_RULES={"ラーメン":["ラーメン","中華そば"],"カフェ":["カフェ","喫茶","コーヒー","珈琲"],"居酒屋":["居酒屋","酒場","バル"],"焼肉":["焼肉","焼き肉"],"寿司":["寿司","鮨","すし"],"コンビニ":["セブン-イレブン","セブンイレブン","ローソン","ファミリーマート","コンビニ"],"スーパー":["スーパー","スーパーマーケット","食品スーパー"],"ドラッグストア":["ドラッグストア","薬局","ツルハ","サツドラ","マツモトキヨシ"],"美容":["美容室","美容院","ヘアサロン","ネイル","エステ"],"ホテル":["ホテル","宿泊施設"],"小売":["ショップ","専門店","ストア"],"飲食店":["レストラン","食堂","飲食店"]}
def classify_title(title):
    if any(k in title for k in TENANT_KEYWORDS): return "tenant",65
    if any(k in title for k in CLOSE_KEYWORDS): return "closing",60
    if any(k in title for k in OPEN_KEYWORDS): return "opening",60
    return None,0
def detect_prefecture(text):
    return next((p for p in PREFECTURES if p in text),None)
def detect_city(text):
    m=re.search(r'([一-龥ぁ-んァ-ヶー]{1,12}(?:市|区|町|村))',text); return m.group(1) if m else None
def detect_category(text):
    for c,ks in CATEGORY_RULES.items():
        if any(k in text for k in ks): return c
    return None
def extract_date(text):
    m=re.search(r'(20\d{2})[年/.\-]\s*(\d{1,2})[月/.\-]\s*(\d{1,2})日?',text)
    if m:
        try:return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
        except:return None
    m=re.search(r'(\d{1,2})月\s*(\d{1,2})日',text)
    if m:
        try:return date(date.today().year,int(m.group(1)),int(m.group(2)))
        except:return None
    return None
def clean_store_name(title):
    t=re.sub(r'\s*[-｜|]\s*[^-｜|]+$','',title).strip()
    t=re.sub(r'【[^】]+】','',t)
    t=re.sub(r'(が|を|は)?\s*(新規)?(オープン|OPEN|開店|閉店|閉館|営業終了|出店).*$','',t,flags=re.I)
    return t.strip(' 「」『』【】:：')[:120] or title[:120]
def calculate_confidence(title,summary,status,prefecture,city,event_date,category):
    s=55
    if status in ("opening","closing"):s+=5
    if prefecture:s+=5
    if city:s+=5
    if event_date:s+=10
    if category:s+=5
    if any(k in (title+" "+summary) for k in ["公式","発表","プレスリリース"]):s+=10
    return min(s,95)
