周辺活力度 v1 追加版

今回は完全差し替えではなく、追加・差し替えが3点です。

1) GitHub直下の detail.js を今回の detail.js に差し替え

2) GitHub直下の styles.css の一番下に
   STYLES_ADD.txt の内容をそのまま追加

3) backend/main.py の一番下に
   BACKEND_ADD.txt の内容をそのまま追加

その後:
Commit changes
→ Render open-close-map-api を Deploy latest commit
→ Render open-close-map を Deploy latest commit

追加されるAPI:
GET /api/stores/{store_id}/activity-score

スコアは現段階では当サイト内データのみを使用する暫定指標です。
