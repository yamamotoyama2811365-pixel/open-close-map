import re
from datetime import date

OPEN_KEYWORDS=["オープン","OPEN","開店","新店舗","新店","グランドオープン","リニューアルオープン","出店"]
CLOSE_KEYWORDS=["閉店","閉館","営業終了","撤退"]
TENANT_KEYWORDS=["テナント募集","居抜き","空き店舗","貸店舗"]

PREFECTURES=[
"北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県",
"埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県",
"岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県",
"鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県",
"佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"
]

CATEGORY_RULES={
"ラーメン":["ラーメン","中華そば"],
"カフェ":["カフェ","喫茶","コーヒー","珈琲"],
"居酒屋":["居酒屋","酒場","バル"],
"焼肉":["焼肉","焼き肉"],
"寿司":["寿司","鮨","すし"],
"コンビニ":["セブン-イレブン","セブンイレブン","ローソン","ファミリーマート","コンビニ"],
"スーパー":["スーパー","スーパーマーケット","食品スーパー"],
"ドラッグストア":["ドラッグストア","薬局","ツルハ","サツドラ","マツモトキヨシ"],
"美容":["美容室","美容院","ヘアサロン","ネイル","エステ"],
"ホテル":["ホテル","宿泊施設"],
"小売":["ショップ","専門店","ストア"],
"飲食店":["レストラン","食堂","飲食店"]
}

def norm(text):
    if not text:
        return ""
    text = text.replace("\u3000"," ")
    text = re.sub(r'[ \t]+',' ',text)
    return text.strip()

def classify_title(title):
    if any(k in title for k in TENANT_KEYWORDS): return "tenant",65
    if any(k in title for k in CLOSE_KEYWORDS): return "closing",60
    if any(k in title for k in OPEN_KEYWORDS): return "opening",60
    return None,0

def detect_prefecture(text):
    return next((p for p in PREFECTURES if p in (text or "")),None)

def detect_city(text):
    t=text or ""
    m=re.search(r'([一-龥ぁ-んァ-ヶー]{1,10}市[一-龥ぁ-んァ-ヶー]{1,10}区)',t)
    if m:return m.group(1)
    m=re.search(r'([一-龥ぁ-んァ-ヶー]{1,15}(?:市|区|町|村))',t)
    return m.group(1) if m else None

def detect_category(text):
    for c,ks in CATEGORY_RULES.items():
        if any(k in (text or "") for k in ks): return c
    return None

def extract_date(text):
    t=text or ""
    m=re.search(r'(20\d{2})[年/.\-]\s*(\d{1,2})[月/.\-]\s*(\d{1,2})日?',t)
    if m:
        try:return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
        except:return None
    m=re.search(r'(\d{1,2})月\s*(\d{1,2})日',t)
    if m:
        try:return date(date.today().year,int(m.group(1)),int(m.group(2)))
        except:return None
    return None

def clean_store_name(title):
    t=re.sub(r'\s*[-｜|]\s*[^-｜|]+$','',title or '').strip()
    t=re.sub(r'【[^】]+】','',t)
    t=re.sub(r'(が|を|は)?\s*(新規)?(オープン|OPEN|開店|閉店|閉館|営業終了|出店).*$','',t,flags=re.I)
    return t.strip(' 「」『』【】:：')[:120] or (title or "")[:120]

def extract_postal_code(text):
    m=re.search(r'〒?\s*(\d{3})[-ー－](\d{4})',text or '')
    return f"{m.group(1)}-{m.group(2)}" if m else None

def extract_floor(text):
    t=text or ""
    for p in [
        r'((?:地下|B|Ｂ)\s*\d{1,2}\s*(?:階|F|Ｆ))',
        r'(\d{1,2}\s*(?:階|F|Ｆ))'
    ]:
        m=re.search(p,t,re.I)
        if m:return re.sub(r'\s+','',m.group(1))
    return None

def clean_address_candidate(value):
    if not value:return None
    v=norm(value)
    v=re.sub(r'^〒?\s*\d{3}[-ー－]\d{4}\s*','',v)
    # trailing labels/noise
    v=re.split(r'(?:TEL|電話|営業時間|アクセス|URL|公式|定休日|客室数|開業日|予約)',v,maxsplit=1)[0]
    v=v.strip("　 ,、。;；|｜[]［］")
    if not detect_prefecture(v):
        return None
    return v[:160]

def extract_labeled_value(text, labels):
    """
    ［所在地］ xxx / 【所在地】xxx / 所在地：xxx / 所在地 xxx
    などを最優先で取得。
    """
    if not text:return None
    t=text.replace('\r','\n')
    label_alt='|'.join(re.escape(x) for x in labels)
    patterns=[
        rf'[［【\[]\s*(?:{label_alt})\s*[］】\]]\s*[:：]?\s*([^\n\r]+)',
        rf'(?:^|\n)\s*(?:{label_alt})\s*[:：]\s*([^\n\r]+)',
        rf'(?:^|\n)\s*(?:{label_alt})\s+([^\n\r]+)',
    ]
    for p in patterns:
        m=re.search(p,t,re.I|re.M)
        if m:
            return norm(m.group(1))
    return None

def extract_address(text):
    if not text:return None

    # 1) ラベル形式を最優先
    labeled=extract_labeled_value(
        text,
        ["所在地","住所","店舗所在地","施設所在地","本社所在地","開業地"]
    )
    addr=clean_address_candidate(labeled)
    if addr:return addr

    # 2) 本文全体から郵便番号＋住所
    t=norm(text)
    m=re.search(
        r'〒?\s*\d{3}[-ー－]\d{4}\s*('
        + '|'.join(map(re.escape,PREFECTURES))
        + r')[一-龥ぁ-んァ-ヶー0-9０-９\-ー丁目番地号ノの\s]{3,120}',
        t
    )
    if m:
        full=m.group(0)
        full=re.sub(r'^〒?\s*\d{3}[-ー－]\d{4}\s*','',full)
        full=re.split(r'(?:TEL|電話|営業時間|アクセス|URL|公式|定休日)',full,maxsplit=1)[0]
        return clean_address_candidate(full)

    # 3) 都道府県から始まる番地住所
    for pref in PREFECTURES:
        idx=t.find(pref)
        if idx<0:continue
        tail=t[idx:idx+180]
        m=re.match(
            re.escape(pref)
            + r'[一-龥ぁ-んァ-ヶー]{1,20}(?:市|区|町|村)'
            + r'[一-龥ぁ-んァ-ヶー0-9０-９\-ー丁目番地号ノの\s]{1,90}',
            tail
        )
        if m:
            candidate=re.split(r'(?:TEL|電話|営業時間|アクセス|URL|公式|定休日)',m.group(0),maxsplit=1)[0]
            # 番号要素があるものを優先
            if re.search(r'\d',candidate):
                return clean_address_candidate(candidate)
    return None

def extract_facility_name(text, address=None):
    if not text:return None

    # 名称ラベル最優先
    labeled=extract_labeled_value(
        text,
        ["名称","名 称","店舗名","施設名","ホテル名","店名"]
    )
    if labeled:
        v=re.split(r'(?:所在地|住所|TEL|電話|営業時間|開業日)',labeled,maxsplit=1)[0]
        v=norm(v).strip("、。:：")
        if 2<=len(v)<=80:
            return v

    t=norm(text)
    patterns=[
        r'([A-Za-z0-9一-龥ぁ-んァ-ヶー・＆&\-\s]{2,50}(?:ショッピングセンター|ショッピングモール|モール|プラザ|タワー|ビル|ホテル|館|センター))'
    ]
    for p in patterns:
        m=re.search(p,t,re.I)
        if m:
            v=norm(m.group(1)).strip("、。:：")
            if address and v in address:continue
            if 2<=len(v)<=80:return v
    return None

def calculate_confidence(title,summary,status,prefecture,city,event_date,category,address=None,facility=None):
    s=55
    if status in ("opening","closing"):s+=5
    if prefecture:s+=5
    if city:s+=5
    if event_date:s+=10
    if category:s+=5
    if address:s+=10
    if facility:s+=4
    if any(k in ((title or "")+" "+(summary or "")) for k in ["公式","発表","プレスリリース"]):s+=10
    return min(s,98)
