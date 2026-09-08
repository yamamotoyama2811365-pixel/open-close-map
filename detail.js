
const API='https://open-close-map-api.onrender.com';
const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const fallbackMap={'ラーメン':'assets/ramen.png','カフェ':'assets/cafe.png','居酒屋':'assets/izakaya.png','焼肉':'assets/yakiniku.png','美容':'assets/beauty.png','コンビニ':'assets/convenience.png','テナント':'assets/tenant.png'};
const label=s=>({opening:'開店予定',open:'OPEN',closing:'閉店予定',closed:'閉店',tenant:'テナント'}[s]||s||'店舗情報');
const id=new URLSearchParams(location.search).get('id');

async function load(){
  const root=document.getElementById('detailRoot');
  if(!id){root.textContent='店舗IDが指定されていません。';return}
  try{
    const r=await fetch(`${API}/api/stores/${encodeURIComponent(id)}`);
    if(!r.ok) throw new Error(r.status);
    const x=await r.json();
    const img=x.image_url||fallbackMap[x.category]||fallbackMap['テナント'];
    document.title=`${x.name||'店舗詳細'}｜開店閉店マップ`;
    root.className='';
    root.innerHTML=`
      <section class="detail-hero">
        <div class="detail-image" style="background-image:url('${esc(img)}')"></div>
        <div class="detail-main">
          <span class="detail-status ${esc(x.status)}">${esc(label(x.status))}</span>
          <h1>${esc(x.name||'店舗名未確認')}</h1>
          <div class="detail-grid">
            <div class="detail-info"><span>開店日</span><strong>${esc(x.open_date||'未確認')}</strong></div>
            <div class="detail-info"><span>閉店日</span><strong>${esc(x.close_date||'未確認')}</strong></div>
            <div class="detail-info"><span>エリア</span><strong>${esc([x.prefecture,x.city].filter(Boolean).join(' ')||'未確認')}</strong></div>
            <div class="detail-info"><span>業種</span><strong>${esc(x.category||'未確認')}</strong></div>
            <div class="detail-info"><span>確度</span><strong>${esc(x.confidence??'-')}%</strong></div>
            <div class="detail-info"><span>最終確認</span><strong>${esc(x.last_verified_at?new Date(x.last_verified_at).toLocaleString('ja-JP'):'未確認')}</strong></div>
          </div>
        </div>
      </section>
      <section class="detail-section">
        <h2>所在地</h2>
        <p>${esc(x.address||[x.prefecture,x.city].filter(Boolean).join(' ')||'住所情報は未確認です。')}</p>
        <div class="map-box">地図表示は次の実装で追加します。<br>住所が確定した店舗からGoogle Maps連携予定です。</div>
      </section>
      <section class="detail-section">
        <h2>情報元</h2>
        <p>${esc(x.source_name||'情報元名称未確認')}</p>
        ${x.source_url?`<a class="source-btn" href="${esc(x.source_url)}" target="_blank" rel="noopener">情報元を確認する</a>`:'<p>情報元URLは未登録です。</p>'}
      </section>
      <section class="detail-section">
        <h2>跡地・テナント情報</h2>
        <p>現在のテナント募集状況や、次に入る店舗情報が確認できた場合にここへ表示します。</p>
      </section>`;
  }catch(e){root.textContent='店舗情報の取得に失敗しました。';console.error(e)}
}
load();
