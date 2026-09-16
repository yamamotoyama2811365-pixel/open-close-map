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
    // Simple no-CORS text/plain POST avoids a browser preflight while the server
    // still verifies the Origin header and validates the JSON body and path.
    const request=fetch('https://buzz-now-1.onrender.com/open-close/api/page-view',{
      method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},
      body:JSON.stringify(payload),credentials:'omit',referrerPolicy:'no-referrer',
      keepalive:true,cache:'no-store'
    });
    // Opaque no-CORS responses have status 0; completion only means the browser sent it.
    window.__ocmFirstPartyPVResult=request.then(()=>({sent:true})).catch(()=>({sent:false}));
  }
  document.addEventListener('visibilitychange',count);
  document.addEventListener('prerenderingchange',count);
  count();
})();
