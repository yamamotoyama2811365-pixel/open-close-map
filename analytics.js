const ANALYTICS_API='https://open-close-map-api.onrender.com';
const DEFAULT_GA_MEASUREMENT_ID='G-ZB4T13GM5P';

window.dataLayer=window.dataLayer||[];
window.gtag=window.gtag||function(){window.dataLayer.push(arguments);};

window.gaEvent=function(name,params={}){
  try{
    window.gtag('event',name,params);
  }catch(e){
    console.warn('GA event skipped',e);
  }
};

async function initAnalytics(){
  try{
    const r=await fetch(ANALYTICS_API+'/api/public-config',{cache:'no-store'});
    if(!r.ok)return;
    const d=await r.json();
    const id=String(d.ga_measurement_id||DEFAULT_GA_MEASUREMENT_ID).trim();

    if(!/^G-[A-Z0-9]+$/i.test(id))return;

    if(!document.querySelector(`script[data-ga4="${id}"]`)){
      const s=document.createElement('script');
      s.async=true;
      s.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(id);
      s.dataset.ga4=id;
      document.head.appendChild(s);
    }

    window.gtag('js',new Date());
    window.gtag('config',id,{
      send_page_view:true,
      anonymize_ip:true
    });
  }catch(e){
    console.warn('GA4 config endpoint unavailable; using fallback ID',e);
    const id=DEFAULT_GA_MEASUREMENT_ID;
    if(!document.querySelector(`script[data-ga4="${id}"]`)){
      const s=document.createElement('script');
      s.async=true;
      s.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(id);
      s.dataset.ga4=id;
      document.head.appendChild(s);
    }
    window.gtag('js',new Date());
    window.gtag('config',id,{
      send_page_view:true,
      anonymize_ip:true
    });
  }
}

document.addEventListener('click',e=>{
  const el=e.target.closest('[data-ga-event]');
  if(!el)return;

  const eventName=el.dataset.gaEvent;
  if(!eventName)return;

  const params={};
  for(const [k,v] of Object.entries(el.dataset)){
    if(k==='gaEvent')continue;
    if(k.startsWith('ga')){
      const key=k
        .replace(/^ga/,'')
        .replace(/^[A-Z]/,m=>m.toLowerCase())
        .replace(/[A-Z]/g,m=>'_'+m.toLowerCase());
      if(key)params[key]=v;
    }
  }

  window.gaEvent(eventName,params);
});

initAnalytics();
