const API='https://open-close-map-api.onrender.com';
const $=id=>document.getElementById(id);

const esc=s=>String(s??'')
  .replaceAll('&','&amp;')
  .replaceAll('<','&lt;')
  .replaceAll('>','&gt;')
  .replaceAll('"','&quot;');

const fallbackMap={
  'ラーメン':'assets/ramen.png',
  'カフェ':'assets/cafe.png',
  '居酒屋':'assets/izakaya.png',
  '焼肉':'assets/yakiniku.png',
  '美容':'assets/beauty.png',
  'コンビニ':'assets/convenience.png',
  'テナント':'assets/tenant.png'
};

let currentMode='all';

function imageFor(x){
  return x.image_url||fallbackMap[x.category]||fallbackMap['テナント'];
}

function label(s){
  return {
    opening:'開店予定',
    open:'開店',
    closing:'閉店予定',
    closed:'閉店',
    tenant:'テナント'
  }[s]||s||'店舗情報';
}

function render(items){
  $('grid').innerHTML=items?.length
    ?items.map(x=>`
      <article class="store-card" data-id="${x.id}">
        <div class="store-image" style="background-image:url('${esc(imageFor(x))}')">
          <span class="badge ${esc(x.status)}">${esc(label(x.status))}</span>
        </div>
        <div class="store-body">
          <div class="store-name">${esc(x.name||'店舗名未確認')}</div>
          <div class="store-meta">
            ${esc(x.open_date||x.close_date||'日付未確認')}<br>
            ${esc([x.prefecture,x.city].filter(Boolean).join(' ')||'エリア未確認')}
          </div>
          <div class="store-tags">
            ${x.category?`<span class="store-tag">${esc(x.category)}</span>`:''}
            ${x.confidence?`<span class="store-tag">確度 ${esc(x.confidence)}%</span>`:''}
          </div>
        </div>
      </article>
    `).join('')
    :'<div class="empty">表示できる店舗情報がありません。</div>';

  document.querySelectorAll('.store-card').forEach(c=>{
    c.onclick=()=>location.href=`/store/${encodeURIComponent(c.dataset.id)}`;
  });
}

async function getJSON(u){
  const r=await fetch(u);
  if(!r.ok)throw new Error(r.status);
  return r.json();
}

async function stats(){
  const d=await getJSON(API+'/api/stats');
  $('storesTotal').textContent=d.stores_total??0;
  $('discoveryTotal').textContent=d.discovery_unprocessed??0;
  $('todayOpen').textContent=d.today_open??0;
  $('weekOpen').textContent=d.week_open??0;
  $('weekClose').textContent=d.week_close??0;
  $('tenant').textContent=d.tenant_detected??0;
}

async function fetchStores(params={}){
  const q=new URLSearchParams({limit:'200'});
  Object.entries(params).forEach(([k,v])=>{
    if(v!==undefined&&v!==null&&v!=='')q.set(k,v);
  });
  const d=await getJSON(API+'/api/stores?'+q);
  return d.items||[];
}

function filterByMode(items,mode){
  if(mode==='opening'){
    return items.filter(x=>x.status==='opening'||x.status==='open');
  }
  if(mode==='closing'){
    return items.filter(x=>x.status==='closing'||x.status==='closed');
  }
  return items;
}

function updateTabUI(mode){
  currentMode=mode;

  document.querySelectorAll('.status-tab').forEach(btn=>{
    const active=btn.dataset.status===mode;
    btn.classList.toggle('active',active);
    btn.setAttribute('aria-selected',active?'true':'false');
  });

  $('latestTitle').textContent=
    mode==='opening'?'最新の開店情報':
    mode==='closing'?'最新の閉店情報':
    '最新の開店・閉店情報';
}

async function stores(mode=currentMode){
  $('grid').innerHTML='<div class="empty">読み込み中...</div>';

  try{
    const items=await fetchStores({limit:'200'});
    const filtered=filterByMode(items,mode).slice(0,40);
    render(filtered);
  }catch(e){
    console.error(e);
    $('grid').innerHTML='<div class="empty">店舗情報を読み込めませんでした。</div>';
  }
}

async function search(){
  const keyword=$('q').value.trim();

  if(!keyword){
    return stores(currentMode);
  }

  $('grid').innerHTML='<div class="empty">検索中...</div>';

  try{
    const items=await fetchStores({limit:'200'});
    const normalized=keyword.toLowerCase();

    let result=items.filter(x=>
      [x.name,x.category,x.prefecture,x.city,x.address]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(normalized)
    );

    result=filterByMode(result,currentMode);
    render(result.slice(0,80));
  }catch(e){
    console.error(e);
    $('grid').innerHTML='<div class="empty">検索に失敗しました。</div>';
  }
}

$('search').onclick=search;
$('q').onkeydown=e=>{
  if(e.key==='Enter')search();
};

document.querySelectorAll('.status-tab').forEach(btn=>{
  btn.onclick=()=>{
    updateTabUI(btn.dataset.status);
    stores(btn.dataset.status);
  };
});

/* SEOページへ直接つなぐ */
document.querySelectorAll('[data-pref]').forEach(b=>{
  b.onclick=()=>location.href=`/area/${encodeURIComponent(b.dataset.pref)}`;
});

function bindCategoryButtons(){
  document.querySelectorAll('[data-cat]').forEach(b=>{
    b.onclick=()=>location.href=`/category/${encodeURIComponent(b.dataset.cat)}`;
  });
}

async function loadCategories(){
  try{
    const d=await getJSON(API+'/api/categories');
    const excluded=new Set([
      '業種未分類','未分類','小売','飲食店'
    ]);

    const items=(d.items||[])
      .filter(x=>x.category&&!excluded.has(x.category))
      .slice(0,6);

    if(items.length){
      $('categoryGrid').innerHTML=items.map(x=>
        `<button data-cat="${esc(x.category)}">${esc(x.category)} <small>${esc(x.count)}</small></button>`
      ).join('');
    }
  }catch(e){
    console.warn('category list fallback',e);
  }

  bindCategoryButtons();
}

bindCategoryButtons();
Promise.all([stats(),stores(),loadCategories()]);
