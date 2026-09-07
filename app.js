const API='https://open-close-map-api.onrender.com';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function label(s){return {opening:'開店予定',open:'OPEN',closing:'閉店予定',closed:'閉店',tenant:'テナント'}[s]||s||'店舗情報'}
function dateOf(x){return x.open_date||x.close_date||'日付未確認'}
function render(items){$('grid').innerHTML=items?.length?items.map(x=>`<article class="store"><div class="cover">${label(x.status)}</div><div class="body"><div class="name">${esc(x.name||'店舗名未確認')}</div><div class="meta">${esc(dateOf(x))}<br>${esc([x.prefecture,x.city].filter(Boolean).join(' ')||'エリア未確認')}${x.confidence?`<br>確度 ${x.confidence}%`:''}</div></div></article>`).join(''):'<div>表示できる店舗情報がありません。</div>'}
async function stats(){try{const d=await (await fetch(API+'/api/stats')).json();$('storesTotal').textContent=d.stores_total??'-';$('discoveryTotal').textContent=d.discovery_unprocessed??'-';$('todayOpen').textContent=d.today_open??0;$('weekOpen').textContent=d.week_open??0;$('weekClose').textContent=d.week_close??0;$('tenant').textContent=d.tenant_detected??0}catch(e){console.error(e)}}
async function stores(pref){let u=API+'/api/stores?limit=20'+(pref?'&prefecture='+encodeURIComponent(pref):'');try{const d=await (await fetch(u)).json();render(d.items||[])}catch(e){$('grid').textContent='取得に失敗しました';console.error(e)}}
document.querySelectorAll('[data-pref]').forEach(b=>b.onclick=()=>stores(b.dataset.pref));
$('search').onclick=async()=>{const q=$('q').value.trim();const d=await (await fetch(API+'/api/stores?limit=100')).json();render((d.items||[]).filter(x=>[x.name,x.category,x.prefecture,x.city].filter(Boolean).join(' ').includes(q)).slice(0,20))};
Promise.all([stats(),stores()]);