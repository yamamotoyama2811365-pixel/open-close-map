const STATUS_API='https://buzz-now-1.onrender.com/open-close';
const pageMode=document.body.dataset.statusPage||'opening';
const isOpening=pageMode==='opening';
const allowed=isOpening?new Set(['opening','open']):new Set(['closing','closed']);
const escStatus=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const statusLabel=s=>isOpening?(s==='opening'?'開店予定':'開店'):(s==='closing'?'閉店予定':'閉店');
(async()=>{
  try{
    const r=await fetch(STATUS_API+'/api/stores?limit=200');
    if(!r.ok)throw new Error(r.status);
    const d=await r.json();
    const items=(d.items||[]).filter(x=>allowed.has(x.status));
    document.getElementById('statusTotal').textContent=items.length>=200?'200+':items.length;
    const latest=items.slice(0,18);
    document.getElementById('statusLatest').innerHTML=latest.length?latest.map(x=>`<a class="status-latest-item" href="/store/${encodeURIComponent(x.id)}" data-ga-event="store_select" data-ga-store-id="${escStatus(x.id)}"><span class="mini-badge ${isOpening?'open':'close'}">${statusLabel(x.status)}</span><strong>${escStatus(x.name||'店舗名未確認')}</strong><small>${escStatus(x.open_date||x.close_date||'日付未確認')}</small></a>`).join(''):'<div class="empty">現在掲載できる情報がありません。</div>';
  }catch(e){
    console.error(e);
    document.getElementById('statusTotal').textContent='-';
    document.getElementById('statusLatest').innerHTML='<div class="empty">最新情報を読み込めませんでした。</div>';
  }
})();
