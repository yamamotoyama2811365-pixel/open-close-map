/* OCM_APPROVED_FAVICON_20260911: shared server-rendered page icons. */
(function(){
  'use strict';
  if(!document.head)return;
  const icons=[
    {rel:'icon',href:'/favicon.ico',type:'image/x-icon',sizes:'16x16 32x32 48x48'},
    {rel:'icon',href:'/favicon-96x96.png',type:'image/png',sizes:'96x96'},
    {rel:'apple-touch-icon',href:'/apple-touch-icon.png',sizes:'180x180'}
  ];
  for(const item of icons){
    if(document.querySelector('link[rel="'+item.rel+'"][href="'+item.href+'"]'))continue;
    const link=document.createElement('link');
    for(const [key,value] of Object.entries(item))link[key]=value;
    document.head.appendChild(link);
  }
})();
/* One page view per document; public-config failures use the existing site ID. */
(function(){
  'use strict';
  if(window.__openCloseAnalyticsLoaded)return;
  window.__openCloseAnalyticsLoaded=true;

  // Start the independent counter before, and without waiting for, Google.
  if(!document.querySelector('script[data-ocm-pv]')){
    const counter=document.createElement('script');
    counter.src='/first-party-pv.js?v=20260916';
    counter.async=true;
    counter.dataset.ocmPv='1';
    document.head.appendChild(counter);
  }

  const ANALYTICS_API='https://buzz-now-1.onrender.com/open-close';
  const DEFAULT_GA_MEASUREMENT_ID='G-ZB4T13GM5P';
  const CONFIG_TIMEOUT_MS=3000;
  window.dataLayer=window.dataLayer||[];
  window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};
  window.gaEvent=function(name,params={}){
    try{window.gtag('event',name,params);}
    catch(e){console.warn('GA event skipped',e);}
  };

  async function measurementId(){
    let timer;
    const controller=typeof AbortController==='function'?new AbortController():null;
    try{
      const request=fetch(ANALYTICS_API+'/api/public-config',{
        cache:'no-store',...(controller?{signal:controller.signal}:{})
      }).then(async r=>{
        if(!r.ok)throw new Error('GA4 config HTTP '+r.status);
        const d=await r.json();
        const id=String(d?.ga_measurement_id||DEFAULT_GA_MEASUREMENT_ID).trim();
        if(!/^G-[A-Z0-9]+$/i.test(id))throw new Error('Invalid GA4 measurement ID');
        return id;
      });
      const timeout=new Promise((_,reject)=>{
        timer=setTimeout(()=>{
          reject(new Error('GA4 config timeout'));
          controller?.abort();
        },CONFIG_TIMEOUT_MS);
      });
      return await Promise.race([request,timeout]);
    }catch(e){
      console.warn('GA4 config unavailable; using site fallback ID',e);
      return DEFAULT_GA_MEASUREMENT_ID;
    }finally{clearTimeout(timer);}
  }

  async function initAnalytics(){
    const id=await measurementId();
    if(!document.querySelector(`script[data-ga4="${id}"]`)){
      const s=document.createElement('script');
      s.async=true;
      s.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(id);
      s.dataset.ga4=id;
      document.head.appendChild(s);
    }
    window.gtag('js',new Date());
    window.gtag('config',id,{send_page_view:true,anonymize_ip:true});
  }

  document.addEventListener('click',e=>{
    const el=e.target?.closest?.('[data-ga-event]');
    if(!el?.dataset.gaEvent)return;
    const params={};
    for(const [k,v] of Object.entries(el.dataset)){
      if(k==='gaEvent'||!k.startsWith('ga'))continue;
      const key=k.replace(/^ga/,'').replace(/^[A-Z]/,m=>m.toLowerCase())
        .replace(/[A-Z]/g,m=>'_'+m.toLowerCase());
      if(key)params[key]=v;
    }
    // Never prevent navigation, including Ctrl/Cmd-click and keyboard activation.
    window.gaEvent(el.dataset.gaEvent,params);
  });

  function loadAffiliateAds(){
    if(document.querySelector('script[data-a8-affiliate]'))return;
    const s=document.createElement('script');
    s.src='/affiliate-ads.js';s.defer=true;s.dataset.a8Affiliate='1';
    document.head.appendChild(s);
  }
  window.__openCloseAnalyticsReady=initAnalytics();
  loadAffiliateAds();
})();

/* i-mobile PC inventory. Approved PC tags are never rendered on mobile. */
(function(){
  'use strict';
  const mobile=/iphone|ipad|ipod|android|mobile|windows phone|blackberry|opera mini|opera mobi/i.test(navigator.userAgent||'');
  if(mobile || !window.matchMedia('(min-width: 769px)').matches)return;

  function mount(spec,position){
    if(document.getElementById(spec.elementId))return;
    const aside=document.createElement('aside');
    aside.setAttribute('aria-label','広告');
    aside.style.cssText='text-align:center;margin:20px auto;overflow:hidden;min-height:'+spec.minHeight+'px';
    const label=document.createElement('div');
    label.textContent='広告';
    label.style.cssText='font-size:12px;opacity:.62;margin-bottom:8px';
    const slot=document.createElement('div');
    slot.id=spec.elementId;
    aside.appendChild(label);aside.appendChild(slot);
    position(aside);
    const loader=document.createElement('script');
    loader.async=true;loader.src='https://imp-adedge.i-mobile.co.jp/script/v1/spot.js?20220104';
    const config=document.createElement('script');config.text=spec.config;
    slot.appendChild(loader);slot.appendChild(config);
  }

  // 728×90 PC上部: header immediately below.
  mount({
    elementId:'im-6a1d194545f249059691f7b8afbd07b1',
    minHeight:90,
    config:'(window.adsbyimobile=window.adsbyimobile||[]).push({pid:85420,mid:596384,asid:1944834,type:"banner",display:"inline",elementid:"im-6a1d194545f249059691f7b8afbd07b1"})'
  },aside=>{
    const header=document.querySelector('.site-header')||document.querySelector('header');
    if(header&&header.parentNode)header.parentNode.insertBefore(aside,header.nextSibling);
    else document.body.prepend(aside);
  });

  // Existing 300×250 PC lower slot: keep it separate so its performance can be measured independently.
  mount({
    elementId:'im-df4ffa2fa91a456c8de5e93bf43f081c',
    minHeight:250,
    config:'(window.adsbyimobile=window.adsbyimobile||[]).push({pid:85420,mid:596384,asid:1944822,type:"banner",display:"inline",elementid:"im-df4ffa2fa91a456c8de5e93bf43f081c"})'
  },aside=>{
    const footer=document.querySelector('.site-footer')||document.querySelector('footer');
    if(footer&&footer.parentNode)footer.parentNode.insertBefore(aside,footer);
    else document.body.appendChild(aside);
  });
})();
