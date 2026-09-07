OPEN_KEYWORDS = ["オープン", "OPEN", "開店", "新店舗", "新店", "グランドオープン", "リニューアルオープン", "出店"]
CLOSE_KEYWORDS = ["閉店", "閉館", "営業終了", "撤退"]
TENANT_KEYWORDS = ["テナント募集", "居抜き", "空き店舗", "貸店舗"]
PREFECTURES = [
    "北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県",
    "茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
    "新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県",
    "滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県",
    "徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"
]

def classify_title(title: str):
    if any(k in title for k in TENANT_KEYWORDS):
        return "tenant", 65
    if any(k in title for k in CLOSE_KEYWORDS):
        return "closing", 60
    if any(k in title for k in OPEN_KEYWORDS):
        return "opening", 60
    return None, 0

def detect_prefecture(text: str):
    for p in PREFECTURES:
        if p in text:
            return p
    return None
