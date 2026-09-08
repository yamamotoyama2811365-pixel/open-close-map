店舗詳細ページ対応版

フロント:
- index.html 差し替え
- styles.css 差し替え
- app.js 差し替え
- detail.html 追加
- detail.js 追加

backend:
- backend/main.py の末尾に BACKEND_ADD.txt のコードを追加

手順:
1. GitHub直下に index.html / styles.css / app.js を差し替え
2. detail.html / detail.js を追加
3. backend/main.py の一番下に BACKEND_ADD.txt の内容を追加
4. Commit changes
5. Renderの open-close-map-api を Deploy latest commit
6. Renderの open-close-map も Deploy latest commit

完了するとトップの店舗カードをクリックして detail.html?id=店舗ID で詳細ページへ遷移します。
