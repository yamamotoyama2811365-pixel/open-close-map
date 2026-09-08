開店閉店マップ 住所・商業施設名対応 v1【完全差し替え版】

今回は部分追記なしです。

【1】GitHub直下
- detail.js を差し替え
- styles.css を差し替え

【2】GitHub backend
- backend フォルダをこのZIP内の backend で丸ごと差し替え

その後:
1. Commit changes
2. Render → open-close-map-api → Manual Deploy → Deploy latest commit
3. APIデプロイ完了後、/docs を開く
4. POST /api/collect を実行
5. POST /api/enrich-addresses?limit=30 を実行
6. POST /api/process?min_confidence=80&enrich_limit=30 を実行
7. Render → open-close-map → Manual Deploy → Deploy latest commit

今回の対応:
- 番地までの住所
- 郵便番号
- 商業施設・ビル名
- 階数
- 情報元の実URL
- Google Maps表示精度向上

※ STYLES_ADD.txt は不要です。styles.css に反映済みです。
