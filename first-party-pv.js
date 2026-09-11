/* Open Close Map anonymous aggregate counter. No cookies or visitor IDs. */
(function(){
  'use strict';
  const ORIGIN='https://open-close-map.onrender.com';
  if(location.origin!==ORIGIN || window.__ocmFirstPartyPVLoaded)return;
  window.__ocmFirstPartyPVLoaded=true;
  const query=new URLSearchParams(location.search);
  if(query.get('ocm_pv')==='off' || navigator.doNotTrack==='1' || navigator.globalPrivacyControl===true)return;
  const test=query.get('ocm_pv_test')==='1';
  if(navigator.webdriver && !test)return;
  let sent=false;
  function sourceOf(ref){
    if(!ref)return 'direct_or_unknown';
    try{
      const host=new URL(ref).hostname.toLowerCase();
      if(host===new URL(ORIGIN).hostname)return 'internal';
      if(/(^|\.)google\.(com|co\.jp|co\.uk|de|fr|ca|com\.au)$/.test(host))return 'google';
      if(/(^|\.)yahoo\.(co\.jp|com)$/.test(host))return 'yahoo';
      if(/(^|\.)bing\.com$/.test(host))return 'bing';
      return 'referral';
    }catch(_){return 'direct_or_unknown';}
  }
  function count(){
    if(sent || document.visibilityState!=='visible' || document.prerendering)return;
    let page=location.pathname;
    if(page==='/detail.html'){
      const id=query.get('id');
      if(!/^[1-9][0-9]{0,17}$/.test(id||''))return;
      page='/store/'+id;
    }
    if(!/^\/(?:$|index\.html$|open\/?$|close\/?$|(?:about|privacy|contact)\.html$|store\/[1-9][0-9]*\/?$|(?:area|category)\/)/.test(page))return;
    sent=true;
    const payload={page,source:sourceOf(document.referrer),is_test:test};
    // Only the coarse source label leaves the browser, never the referrer URL.
    const request=fetch('https://buzz-now-1.onrender.com/open-close/api/page-view',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload),credentials:'omit',referrerPolicy:'no-referrer',
      keepalive:true,cache:'no-store'
    });
    // No retries: a lost response must not produce a duplicate count.
    window.__ocmFirstPartyPVResult=request.then(r=>({ok:r.status===204,status:r.status})).catch(()=>({ok:false,status:0}));
  }
  document.addEventListener('visibilitychange',count);
  document.addEventListener('prerenderingchange',count);
  count();
})();
