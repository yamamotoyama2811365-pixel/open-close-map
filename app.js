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
      <article class="store-card" data-id="${x.id}" data-status="${esc(x.status||'')}" data-category="${esc(x.category||'')}">
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
    c.onclick=()=>{
      window.gaEvent?.('store_select',{
        store_id:c.dataset.id,
        status:c.dataset.status||'',
        category:c.dataset.category||''
      });
      location.href=`/store/${encodeURIComponent(c.dataset.id)}`;
    };
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
    window.gaEvent?.('search_reset',{status_mode:currentMode});
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
    window.gaEvent?.('search_submit',{
      result_count:result.length,
      status_mode:currentMode
    });
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
    window.gaEvent?.('status_filter',{status_mode:btn.dataset.status});
    updateTabUI(btn.dataset.status);
    stores(btn.dataset.status);
  };
});

/* SEOページへ直接つなぐ */
document.querySelectorAll('[data-pref]').forEach(b=>{
  b.onclick=()=>{
    window.gaEvent?.('area_select',{prefecture:b.dataset.pref});
    location.href=`/area/${encodeURIComponent(b.dataset.pref)}`;
  };
});

function bindCategoryButtons(){
  document.querySelectorAll('[data-cat]').forEach(b=>{
    b.onclick=()=>{
      window.gaEvent?.('category_select',{category:b.dataset.cat});
      location.href=`/category/${encodeURIComponent(b.dataset.cat)}`;
    };
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

function renderNationalComboChart(items){
  if(!items||!items.length){
    $('nationalChart').innerHTML='<div class="empty">表示できる全国動向データがありません。</div>';
    return;
  }

  const W=760,H=250,L=34,R=18,T=18,B=36;
  const PW=W-L-R,PH=H-T-B;
  const ymaxRaw=Math.max(1,...items.flatMap(x=>[Number(x.open||0),Number(x.close||0)]));
  let ymax=Math.max(4,ymaxRaw);
  ymax=ymax<=10?Math.ceil(ymax/2)*2:Math.ceil(ymax/5)*5;

  const step=PW/items.length;
  const group=Math.min(36,step*.72);
  const bw=Math.max(5,(group-4)/2);
  const sy=v=>T+PH-(PH*(Number(v||0)/ymax));

  const grids=[];
  const ylabels=[];
  for(let j=0;j<5;j++){
    const val=Math.round(ymax*(4-j)/4);
    const y=T+PH*j/4;
    grids.push(`<line class="nat-grid" x1="${L}" y1="${y}" x2="${W-R}" y2="${y}"></line>`);
    ylabels.push(`<text class="nat-axis" x="${L-7}" y="${y+3}" text-anchor="end">${val}</text>`);
  }

  const bars=[],dots=[],xlabels=[],op=[],cl=[];
  items.forEach((row,i)=>{
    const x=L+step*(i+.5);
    const o=Number(row.open||0), c=Number(row.close||0);
    const yo=sy(o), yc=sy(c), base=T+PH;
    const ox=x-bw-2, cx=x+2;
    const opx=ox+bw/2, cpx=cx+bw/2;
    const d=new Date(row.month);
    const m=d.getMonth()+1;

    bars.push(`<rect class="nat-open-bar" x="${ox}" y="${yo}" width="${bw}" height="${Math.max(1,base-yo)}" rx="2"><title>${m}月 開店 ${o}件</title></rect>`);
    bars.push(`<rect class="nat-close-bar" x="${cx}" y="${yc}" width="${bw}" height="${Math.max(1,base-yc)}" rx="2"><title>${m}月 閉店 ${c}件</title></rect>`);
    op.push(`${opx},${yo}`);
    cl.push(`${cpx},${yc}`);
    dots.push(`<circle class="nat-open-dot" cx="${opx}" cy="${yo}" r="3.5"><title>${m}月 開店 ${o}件</title></circle>`);
    dots.push(`<circle class="nat-close-dot" cx="${cpx}" cy="${yc}" r="3.5"><title>${m}月 閉店 ${c}件</title></circle>`);
    xlabels.push(`<text class="nat-axis" x="${x}" y="${H-11}" text-anchor="middle">${m}月</text>`);
  });

  $('nationalChart').innerHTML=`
    <svg class="national-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="全国の直近12か月の開店・閉店動向">
      ${grids.join('')}
      ${ylabels.join('')}
      ${xlabels.join('')}
      ${bars.join('')}
      <polyline class="nat-open-line" points="${op.join(' ')}"></polyline>
      <polyline class="nat-close-line" points="${cl.join(' ')}"></polyline>
      ${dots.join('')}
    </svg>
    <div class="national-legend">
      <span><i class="open"></i>開店</span>
      <span><i class="close"></i>閉店</span>
      <span style="margin-left:auto">棒＝件数 / 線＝推移</span>
    </div>
  `;
}

async function nationalInsights(){
  try{
    const d=await getJSON(API+'/api/national-insights');
    $('nationalTrendBadge').textContent=d.trend||'全国動向';
    $('nationalOpen').textContent=d.open??0;
    $('nationalClose').textContent=d.close??0;
    $('nationalNet').textContent=(Number(d.net)>0?'+':'')+(d.net??0);

    renderNationalComboChart(d.monthly||[]);

    const cats=(d.categories||[]).slice(0,6);
    $('nationalCategories').innerHTML=cats.length
      ?cats.map(x=>{
          const net=Number(x.net||0);
          const cls=net>0?'up':net<0?'down':'flat';
          const txt=(net>0?'+':'')+net;
          return `<div class="national-cat-row"><span>${esc(x.category)}</span><strong class="${cls}">${txt}</strong></div>`;
        }).join('')
      :'<div class="empty">業種別データを蓄積中です。</div>';
  }catch(e){
    console.error(e);
    $('nationalTrendBadge').textContent='データ準備中';
    $('nationalChart').innerHTML='<div class="empty">全国動向を読み込めませんでした。</div>';
    $('nationalCategories').innerHTML='<div class="empty">業種別データを読み込めませんでした。</div>';
  }
}

Promise.all([stats(),stores(),loadCategories(),nationalInsights()]);
