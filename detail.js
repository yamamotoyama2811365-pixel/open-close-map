
const API='https://open-close-map-api.onrender.com';
const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const fallbackMap={'ラーメン':'assets/ramen.png','カフェ':'assets/cafe.png','居酒屋':'assets/izakaya.png','焼肉':'assets/yakiniku.png','美容':'assets/beauty.png','コンビニ':'assets/convenience.png','テナント':'assets/tenant.png'};
const label=s=>({opening:'開店予定',open:'OPEN',closing:'閉店予定',closed:'閉店',tenant:'テナント'}[s]||s||'店舗情報');
const id=new URLSearchParams(location.search).get('id');

async function getJSON(url){const r=await fetch(url);if(!r.ok)throw new Error(r.status);return r.json()}

function mapHtml(x){
  const address=x.address||[x.prefecture,x.city].filter(Boolean).join(' ');
  if(!address) return '<div class="map-placeholder">住所情報が確認でき次第、地図を表示します。</div>';
  const src='https://www.google.com/maps?q='+encodeURIComponent(address)+'&output=embed';
  return `<iframe class="map-frame" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="${src}"></iframe>`;
}

async function load(){
  const root=document.getElementById('detailRoot');
  if(!id){root.textContent='店舗IDが指定されていません。';return}
  try{
    const [x, nearby, tenant, area] = await Promise.all([
      getJSON(`${API}/api/stores/${encodeURIComponent(id)}`),
      getJSON(`${API}/api/stores/${encodeURIComponent(id)}/nearby`),
      getJSON(`${API}/api/stores/${encodeURIComponent(id)}/tenant`),
      getJSON(`${API}/api/stores/${encodeURIComponent(id)}/area-summary`)
    ]);

    const img=x.image_url||fallbackMap[x.category]||fallbackMap['テナント'];
    document.title=`${x.name||'店舗詳細'}｜開店閉店マップ`;

    const nearbyHtml=(nearby.items||[]).length
      ? `<div class="nearby-list">${nearby.items.map(n=>`<a class="nearby-item" href="detail.html?id=${n.id}"><b>${esc(n.name)}</b><span>${esc(label(n.status))} / ${esc(n.category||'業種未確認')}</span></a>`).join('')}</div>`
      : '<p>同一エリアの店舗情報はまだありません。</p>';

    const tenantHtml=(tenant.items||[]).length
      ? tenant.items.map(t=>`<div class="tenant-card"><b>${esc(t.source_name||'テナント情報')}</b><div>${esc(t.status||'確認中')}</div>${t.source_url?`<a href="${esc(t.source_url)}" target="_blank" rel="noopener">募集情報を見る →</a>`:''}</div>`).join('')
      : '<p>現在、確認できるテナント募集情報はありません。</p>';

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
        <h2>所在地・地図</h2>
        <p>${esc(x.address||[x.prefecture,x.city].filter(Boolean).join(' ')||'住所情報は未確認です。')}</p>
        ${mapHtml(x)}
      </section>

      <section class="detail-section">
        <h2>周辺店舗動向</h2>
        <div class="metric-grid">
          <div class="metric"><span>同一エリア登録店舗</span><strong>${esc(area.total??0)}</strong></div>
          <div class="metric"><span>開店・開店予定</span><strong>${esc(area.opening??0)}</strong></div>
          <div class="metric"><span>閉店・閉店予定</span><strong>${esc(area.closing??0)}</strong></div>
        </div>
      </section>

      <section class="detail-section">
        <h2>同一エリアの店舗情報</h2>
        ${nearbyHtml}
      </section>

      <section class="detail-section">
        <h2>跡地・テナント情報</h2>
        ${tenantHtml}
      </section>

      <section class="detail-section">
        <h2>情報元</h2>
        <p>${esc(x.source_name||'情報元名称未確認')}</p>
        ${x.source_url?`<a class="source-btn" href="${esc(x.source_url)}" target="_blank" rel="noopener">情報元を確認する</a>`:'<p>情報元URLは未登録です。</p>'}
      </section>`;
  }catch(e){
    root.textContent='店舗情報の取得に失敗しました。';
    console.error(e);
  }
}
load();
