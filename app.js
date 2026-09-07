const stores = [
  {status:'NEW', cls:'green', date:'2026.09.07', name:'スターバックス 札幌すすきの店', place:'北海道 札幌市中央区'},
  {status:'NEW', cls:'green', date:'2026.09.10', name:'無印良品 イオンモール新潟南', place:'新潟県 新潟市江南区'},
  {status:'CLOSED', cls:'red', date:'2026.09.05', name:'サイゼリヤ なんばCITY店', place:'大阪府 大阪市中央区'},
  {status:'テナント募集', cls:'blue', date:'2026.09.06 確認', name:'旧ドトールコーヒー 店舗跡地', place:'東京都 渋谷区'}
];
function renderStores(){
  document.getElementById('storeCards').innerHTML = stores.map(s => `
    <article class="card">
      <div class="card-image"><span class="badge ${s.cls}" style="position:absolute;top:10px;left:10px">${s.status}</span></div>
      <div class="card-body"><div class="date">${s.date}</div><h3>${s.name}</h3><div class="place">⌖ ${s.place}</div></div>
    </article>`).join('');
}
function runSearch(id){const q=document.getElementById(id).value.trim(); if(!q) return; alert(`「${q}」の検索結果ページへ遷移する想定です。`)}
renderStores();
