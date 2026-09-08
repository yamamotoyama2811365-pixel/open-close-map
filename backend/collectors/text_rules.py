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

FACILITY_KEYWORDS = [
    "イオンモール","イオン","アリオ","ステラプレイス","パルコ","PARCO","ルミネ","マルイ",
    "丸井今井","三越","大丸","東急","ロフト","ミーナ","ココノススキノ","COCONO SUSUKINO",
    "サッポロファクトリー","赤れんがテラス","moyuk SAPPORO","モユクサッポロ",
    "BiVi","ビビ","イトーヨーカドー","ショッピングセンター","ショッピングモール",
    "モール","プラザ","タワー","ビル","館","センター"
]

def classify_title(title):
    if any(k in title for k in TENANT_KEYWORDS): return "tenant",65
    if any(k in title for k in CLOSE_KEYWORDS): return "closing",60
    if any(k in title for k in OPEN_KEYWORDS): return "opening",60
    return None,0

def detect_prefecture(text):
    return next((p for p in PREFECTURES if p in text),None)

def detect_city(text):
    # 政令市の区まで拾える場合は「札幌市中央区」のように保持
    m=re.search(r'([一-龥ぁ-んァ-ヶー]{1,10}市[一-龥ぁ-んァ-ヶー]{1,10}区)',text)
    if m: return m.group(1)
    m=re.search(r'([一-龥ぁ-んァ-ヶー]{1,12}(?:市|区|町|村))',text)
    return m.group(1) if m else None

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

def normalize_space(text):
    return re.sub(r'\s+',' ',text or '').strip()

def extract_postal_code(text):
    m=re.search(r'〒?\s*(\d{3})[-ー－](\d{4})', text or '')
    return f"{m.group(1)}-{m.group(2)}" if m else None

def extract_floor(text):
    patterns = [
        r'([地下Bｂ]?\s*\d{1,2}\s*[階FＦ])',
        r'(B\d{1,2}F)',
        r'(\d{1,2}F)',
    ]
    for p in patterns:
        m=re.search(p,text or '',re.I)
        if m:
            return re.sub(r'\s+','',m.group(1))
    return None

def extract_address(text):
    """
    公開記事内に明示された日本住所を事実情報として抽出。
    推測補完はしない。
    """
    if not text: return None
    t = normalize_space(text)
    pref = detect_prefecture(t)
    if not pref:
        return None

    start = t.find(pref)
    if start < 0:
        return None

    tail = t[start:start+160]

    # 句読点、改行相当、ラベル終端になりやすい文字で切る
    tail = re.split(r'[。．\n\r<>]|(?:TEL|電話|営業時間|アクセス|店舗名|店名|公式)', tail, maxsplit=1)[0]

    # 都道府県 + 市区町村 + 町域 + 番地程度まで
    # 例: 北海道札幌市中央区南1条西3丁目3-27
    addr_re = re.compile(
        r'(' + re.escape(pref) +
        r'[一-龥ぁ-んァ-ヶー0-9０-９\-ー丁目番地号ノの\s]{2,90}?' +
        r'(?:\d+[丁目番地号\-ー]\d*(?:[\-ー]\d+)*|\d+丁目))'
    )
    m = addr_re.search(tail)
    if m:
        addr = normalize_space(m.group(1))
        addr = addr.replace('  ',' ')
        return addr[:140]

    # 番地がなくても市区町村＋町域まで明示なら保存
    simple = re.match(
        r'(' + re.escape(pref) + r'[一-龥ぁ-んァ-ヶー]{1,20}(?:市|区|町|村)[一-龥ぁ-んァ-ヶー0-9０-９\-ー丁目\s]{1,50})',
        tail
    )
    return normalize_space(simple.group(1))[:140] if simple else None

def extract_facility_name(text, address=None):
    if not text: return None
    t=normalize_space(text)

    # 「○○ビル」「○○モール」「○○館」など
    patterns = [
        r'([A-Za-z0-9一-龥ぁ-んァ-ヶー・＆&\-\s]{2,35}(?:ショッピングセンター|ショッピングモール|モール|プラザ|タワー|ビル|館|センター))',
        r'((?:イオンモール|アリオ|ルミネ|PARCO|パルコ|大丸|三越|丸井今井|東急|COCONO SUSUKINO|ココノススキノ|サッポロファクトリー|赤れんがテラス|moyuk SAPPORO|モユクサッポロ)[A-Za-z0-9一-龥ぁ-んァ-ヶー・＆&\-\s]{0,20})'
    ]
    for p in patterns:
        m=re.search(p,t,re.I)
        if m:
            name=normalize_space(m.group(1)).strip("、。:：")
            # 住所本文を丸ごと拾ったようなものを除外
            if address and name in address:
                continue
            if 2 <= len(name) <= 60:
                return name
    return None

def calculate_confidence(title,summary,status,prefecture,city,event_date,category,address=None,facility=None):
    s=55
    if status in ("opening","closing"):s+=5
    if prefecture:s+=5
    if city:s+=5
    if event_date:s+=10
    if category:s+=5
    if address:s+=8
    if facility:s+=3
    if any(k in (title+" "+summary) for k in ["公式","発表","プレスリリース"]):s+=10
    return min(s,98)
