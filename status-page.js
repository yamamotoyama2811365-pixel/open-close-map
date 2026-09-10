/* Fetch each status BEFORE applying the API limit, not after a mixed 200 rows. */
(function(){
  'use strict';
  const API='https://buzz-now-1.onrender.com/open-close';
  const opening=document.body.dataset.statusPage!=='closing';
  const statuses=opening?['opening','open']:['closing','closed'];
  const allowed=new Set(statuses);
  const limit=200;
  const visibleLimit=18;
  const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;')
    .replaceAll('>','&gt;').replaceAll('"','&quot;');
  const total=document.getElementById('statusTotal');
  const list=document.getElementById('statusLatest');
  if(!total||!list)return;

  // The endpoint returns a limited list, not a database-wide total.
  const countLabel=document.querySelector('.status-page-count span');
  if(countLabel)countLabel.textContent='取得した掲載情報';
  total.setAttribute('title','開店・閉店の区分ごとに最大200件を取得。全国の総店舗数ではありません。');
  list.setAttribute('aria-live','polite');

  const dateFor=x=>opening?x.open_date:x.close_date;
  function labelFor(x){
    if(x.quality_pending)return '情報確認中';
    const d=dateFor(x);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(d||''))return opening?'開店情報':'閉店情報';
    // Calendar dates are compared in Japan, regardless of the visitor timezone.
    const today=new Date(Date.now()+9*60*60*1000).toISOString().slice(0,10);
    return opening?(d>today?'開店予定':'開店'):(d>today?'閉店予定':'閉店');
  }

  async function fetchStatus(status){
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),15000);
    try{
      const query=new URLSearchParams({status,limit:String(limit)});
      const r=await fetch(API+'/api/stores?'+query,{signal:controller.signal});
      if(!r.ok)throw new Error('Store list HTTP '+r.status);
      const d=await r.json();
      if(!Array.isArray(d.items))throw new Error('Invalid store list response');
      // Do not silently accept a server that ignores the status filter.
      if(d.items.some(x=>!x||x.status!==status))throw new Error('Unexpected store status');
      return d.items;
    }finally{clearTimeout(timer);}
  }

  async function load(){
    list.setAttribute('aria-busy','true');
    try{
      // A failed half must not masquerade as a complete/zero-result list.
      const batches=await Promise.all(statuses.map(fetchStatus));
      const seen=new Set();
      const items=batches.flat().filter(x=>{
        if(!allowed.has(x.status)||!/^\d+$/.test(String(x.id??'')))return false;
        const key=String(x.id);
        if(seen.has(key))return false;
        seen.add(key);
        return true;
      });
      items.sort((a,b)=>{
        const ad=String(dateFor(a)||'');
        const bd=String(dateFor(b)||'');
        return bd.localeCompare(ad)||Number(b.id)-Number(a.id);
      });
      const capped=batches.some(rows=>rows.length>=limit);
      total.textContent=String(items.length)+(capped?'+':'');
      const latest=items.slice(0,visibleLimit);
      list.innerHTML=latest.length?latest.map(x=>
        `<a class="status-latest-item" href="/store/${encodeURIComponent(x.id)}" data-ga-event="store_select" data-ga-store-id="${esc(x.id)}"><span class="mini-badge ${opening?'open':'close'}">${esc(labelFor(x))}</span><strong>${esc(x.name||'店舗名未確認')}</strong><small>${esc(dateFor(x)||'日付未確認')}</small></a>`
      ).join(''):'<div class="empty">現在掲載できる情報がありません。</div>';
      if(latest.length){
        list.innerHTML+=`<p class="status-panel-copy">取得した情報のうち${latest.length}件を表示。日付がある情報を日程の新しい順に表示しています。各地域の一覧は都道府県リンクからご確認ください。${capped?'取得上限に達しているため、件数は全国の掲載総数ではありません。':''}</p>`;
      }
    }catch(e){
      console.error('Status page could not load',e);
      total.textContent='-';
      list.innerHTML='<div class="empty">最新情報を読み込めませんでした。時間をおいて再読み込みするか、都道府県のリンクからご確認ください。</div>';
    }finally{list.setAttribute('aria-busy','false');}
  }
  window.__ocmStatusPageReady=load();
})();
