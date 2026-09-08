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

NEGATIVE_ADDRESS_LABELS=[
    "本社所在地","本社住所","会社所在地","会社住所","運営会社","会社概要",
    "問い合わせ先","お問い合わせ先","連絡先","本部所在地","事務局所在地"
]

POSITIVE_ADDRESS_LABELS=[
    "店舗所在地","施設所在地","会場","開催場所","所在地","住所","アクセス"
]

POSITIVE_NAME_LABELS=[
    "店舗名","施設名","会場名","名称","名 称","ホテル名","店名"
]

def norm(text):
    if not text:
        return ""
    text=text.replace("\u3000"," ")
    text=re.sub(r'[ \t]+',' ',text)
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

def extract_source_name_from_title(title):
    if not title:return None
    # last suffix after dash / pipe, common in Google News titles
    m=re.search(r'\s*[-｜|]\s*([^-｜|]{2,60})\s*$',title)
    if m:
        s=norm(m.group(1))
        if s and "Google News" not in s:
            return s
    return None

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

def _label_value(text, labels):
    if not text:return None
    t=text.replace('\r','\n')
    alt='|'.join(re.escape(x) for x in labels)
    patterns=[
        rf'[［【\[]\s*(?:{alt})\s*[］】\]]\s*[:：]?\s*([^\n\r]+)',
        rf'(?:^|\n)\s*(?:{alt})\s*[:：]\s*([^\n\r]+)',
        rf'(?:^|\n)\s*(?:{alt})\s+([^\n\r]+)',
    ]
    for p in patterns:
        m=re.search(p,t,re.I|re.M)
        if m:return norm(m.group(1))
    return None

def contains_negative_context(text):
    t=text or ""
    return any(x in t for x in NEGATIVE_ADDRESS_LABELS)

def clean_address_candidate(value):
    if not value:return None
    v=norm(value)
    v=re.sub(r'^〒?\s*\d{3}[-ー－]\d{4}\s*','',v)
    v=re.split(r'(?:TEL|電話|営業時間|アクセス|URL|公式|定休日|予約|問い合わせ|お問い合わせ)',v,maxsplit=1)[0]
    v=v.strip("　 ,、。;；|｜[]［］")
    if not detect_prefecture(v):return None
    return v[:160]

def address_matches_expected_prefecture(address, expected_prefecture):
    if not address or not expected_prefecture:
        return True
    return detect_prefecture(address) == expected_prefecture

def extract_labeled_address_block(text):
    """
    Returns value + context label.
    Avoids company/head-office blocks.
    """
    if not text:return (None,None)
    t=text.replace('\r','\n')
    lines=[norm(x) for x in t.split('\n') if norm(x)]

    for i,line in enumerate(lines):
        # Skip obvious negative labels/sections
        if any(lbl in line for lbl in NEGATIVE_ADDRESS_LABELS):
            continue

        for label in POSITIVE_ADDRESS_LABELS:
            if label in line:
                # If same line contains value
                after=re.split(re.escape(label),line,maxsplit=1)[-1]
                after=after.lstrip("：: ]］】")
                if detect_prefecture(after):
                    return clean_address_candidate(after),label

                # Try next line
                if i+1 < len(lines):
                    nxt=lines[i+1]
                    if not contains_negative_context(nxt) and detect_prefecture(nxt):
                        return clean_address_candidate(nxt),label
    return (None,None)

def extract_address(text, expected_prefecture=None):
    if not text:return None

    # 1) Positive labels / block
    addr,label=extract_labeled_address_block(text)
    if addr and address_matches_expected_prefecture(addr,expected_prefecture):
        return addr

    # 2) Postal + address, but reject negative contexts around it
    t=text.replace('\r','\n')
    for m in re.finditer(
        r'〒?\s*\d{3}[-ー－]\d{4}\s*('
        + '|'.join(map(re.escape,PREFECTURES))
        + r')[一-龥ぁ-んァ-ヶー0-9０-９\-ー丁目番地号ノの\s]{3,120}',
        t
    ):
        start=max(0,m.start()-80)
        context=t[start:m.start()+len(m.group(0))+30]
        if contains_negative_context(context):
            continue
        full=re.sub(r'^〒?\s*\d{3}[-ー－]\d{4}\s*','',m.group(0))
        full=re.split(r'(?:TEL|電話|営業時間|アクセス|URL|公式|定休日)',full,maxsplit=1)[0]
        addr=clean_address_candidate(full)
        if addr and address_matches_expected_prefecture(addr,expected_prefecture):
            return addr

    # 3) Prefecture-starting numbered address
    flat=norm(t)
    prefs=[expected_prefecture] if expected_prefecture else PREFECTURES
    for pref in prefs:
        if not pref:continue
        for m in re.finditer(re.escape(pref),flat):
            start=max(0,m.start()-70)
            precontext=flat[start:m.start()]
            if contains_negative_context(precontext):
                continue
            tail=flat[m.start():m.start()+180]
            mm=re.match(
                re.escape(pref)
                + r'[一-龥ぁ-んァ-ヶー]{1,20}(?:市|区|町|村)'
                + r'[一-龥ぁ-んァ-ヶー0-9０-９\-ー丁目番地号ノの\s]{1,90}',
                tail
            )
            if mm and re.search(r'\d',mm.group(0)):
                candidate=re.split(r'(?:TEL|電話|営業時間|アクセス|URL|公式|定休日)',mm.group(0),maxsplit=1)[0]
                addr=clean_address_candidate(candidate)
                if addr and address_matches_expected_prefecture(addr,expected_prefecture):
                    return addr
    return None

def extract_facility_name(text, address=None):
    if not text:return None

    labeled=_label_value(text,POSITIVE_NAME_LABELS)
    if labeled:
        v=re.split(r'(?:所在地|住所|TEL|電話|営業時間|開業日)',labeled,maxsplit=1)[0]
        v=norm(v).strip("、。:：")
        if 2<=len(v)<=80:return v

    # Prefer known venue-like names
    t=norm(text)
    patterns=[
        r'([A-Za-z0-9一-龥ぁ-んァ-ヶー・＆&\-\s]{2,50}(?:ショッピングセンター|ショッピングモール|モール|プラザ|タワー|ビル|ホテル|館|センター|百貨店|店))'
    ]
    for p in patterns:
        for m in re.finditer(p,t,re.I):
            v=norm(m.group(1)).strip("、。:：")
            if address and v in address:continue
            if contains_negative_context(v):continue
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
