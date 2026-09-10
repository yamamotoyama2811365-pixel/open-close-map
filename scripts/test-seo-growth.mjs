/** Dependency-free regression checks: node scripts/test-seo-growth.mjs */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const analytics=fs.readFileSync(path.join(root,'analytics.js'),'utf8');
const app=fs.readFileSync(path.join(root,'app.js'),'utf8');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
let passed=0;
async function check(name,fn){await fn();passed++;console.log('PASS',name);}
function environment(fetchImpl){
  const nodes=[],listeners={};let fetchCount=0;
  const context={
    console:{warn(){},error(){}},AbortController,Date,Promise,
    setTimeout:(fn,ms)=>setTimeout(fn,ms===3000?5:ms),clearTimeout,
    fetch:(...args)=>{fetchCount++;return fetchImpl(...args);},
    document:{
      head:{appendChild:node=>nodes.push(node)},
      createElement:()=>({dataset:{}}),
      querySelector(selector){
        if(selector==='script[data-a8-affiliate]')return nodes.find(n=>n.dataset.a8Affiliate);
        const id=/data-ga4="([^"]+)"/.exec(selector)?.[1];
        return nodes.find(n=>n.dataset.ga4===id);
      },
      addEventListener:(name,fn)=>{listeners[name]=fn;}
    }
  };
  context.window=context;vm.createContext(context);
  return {context,nodes,listeners,fetchCount:()=>fetchCount,
    run:()=>vm.runInContext(analytics,context),
    configs:()=>Array.from(context.dataLayer||[],x=>Array.from(x)).filter(x=>x[0]==='config')};
}
const response=id=>({ok:true,json:async()=>({ga_measurement_id:id})});
for(const [name,fetchImpl,expected] of [
  ['valid configuration',async()=>response('G-VALID123'),'G-VALID123'],
  ['missing ID uses existing ID',async()=>response(undefined),'G-ZB4T13GM5P'],
  ['HTTP 503 fallback',async()=>({ok:false,status:503}),'G-ZB4T13GM5P'],
  ['HTTP 404 fallback',async()=>({ok:false,status:404}),'G-ZB4T13GM5P'],
  ['invalid ID fallback',async()=>response('not-an-id'),'G-ZB4T13GM5P'],
  ['invalid JSON fallback',async()=>({ok:true,json:async()=>{throw new Error('bad JSON');}}),'G-ZB4T13GM5P'],
  ['network fallback',async()=>{throw new Error('offline');},'G-ZB4T13GM5P'],
  ['hanging request timeout',()=>new Promise(()=>{}),'G-ZB4T13GM5P']
]){
  await check(name,async()=>{
    const e=environment(fetchImpl);e.run();await e.context.__openCloseAnalyticsReady;
    assert.equal(e.configs().length,1);assert.equal(e.configs()[0][1],expected);
    assert.equal(e.configs()[0][2].send_page_view,true);
    assert.equal(e.nodes.filter(n=>n.dataset.ga4).length,1);
    assert.equal(e.nodes.filter(n=>n.dataset.a8Affiliate).length,1);
  });
}
await check('repeated script inclusion sends exactly one page view',async()=>{
  const e=environment(async()=>response('G-VALID123'));e.run();e.run();
  await e.context.__openCloseAnalyticsReady;e.run();
  assert.equal(e.fetchCount(),1);assert.equal(e.configs().length,1);
  assert.equal(e.nodes.filter(n=>n.dataset.a8Affiliate).length,1);
});
await check('late response does not configure another property',async()=>{
  let resolve;const e=environment(()=>new Promise(r=>{resolve=r;}));
  e.run();await e.context.__openCloseAnalyticsReady;
  resolve(response('G-LATE123'));await new Promise(r=>setImmediate(r));
  assert.equal(e.configs().length,1);assert.equal(e.configs()[0][1],'G-ZB4T13GM5P');
});
await check('delegated navigation event does not cancel modified click',async()=>{
  const e=environment(async()=>response('G-VALID123'));e.run();
  await e.context.__openCloseAnalyticsReady;
  const item={dataset:{gaEvent:'store_select',gaStoreId:'123',gaPlacement:'hero'}};
  let cancelled=false;e.listeners.click({ctrlKey:true,target:{closest:()=>item},preventDefault(){cancelled=true;}});
  const event=Array.from(e.context.dataLayer.at(-1));
  assert.equal(event[0],'event');assert.equal(event[1],'store_select');
  assert.equal(event[2].store_id,'123');assert.equal(event[2].placement,'hero');assert.equal(cancelled,false);
  e.listeners.click({target:{}}); // Non-Element event targets are safe.
});
await check('static finder links exist without JavaScript',()=>{
  assert.equal((html.match(/<a\b[^>]*href="\/area\//g)||[]).length,6);
  assert.equal((html.match(/<a\b[^>]*href="\/category\//g)||[]).length,6);
  assert.doesNotMatch(html,/<button[^>]+data-(pref|cat)=/);
  assert.match(html,/<button[^>]+data-status="opening"/); // Filtering stays a button.
  const ld=html.match(/<script type="application\/ld\+json">([^<]+)<\/script>/)[1];
  const site=JSON.parse(ld);assert.equal(site['@type'],'WebSite');
  assert.equal(site.url,'https://open-close-map.onrender.com/');
  assert.equal((html.match(/rel="canonical"/g)||[]).length,1);
  assert.match(html,/href="\/contact.html"/);assert.match(html,/ca-pub-5776658615046901/);
});
await check('rendered cards, hero and categories are real escaped links',async()=>{
  const elements={};const el=id=>elements[id]??={innerHTML:'',textContent:'',value:'',classList:{toggle(){}}};
  const sample={id:123,name:'店名 <script>unsafe</script>',status:'closing',category:'カフェ',prefecture:'北海道',city:'札幌市',close_date:'2026-09-20'};
  const c={console:{warn(){},error(){}},URLSearchParams,Date,Promise,encodeURIComponent,
    document:{getElementById:el,querySelectorAll:()=>[]},
    fetch:async url=>({ok:true,json:async()=>{
      if(url.includes('/api/stores'))return {items:[sample]};
      if(url.includes('/api/categories'))return {items:[{category:'カフェ',count:2}]};
      if(url.includes('/api/national-insights'))return {monthly:[],categories:[{category:'カフェ',net:1}]};
      return {stores_total:1};
    }})};c.window=c;vm.createContext(c);await vm.runInContext(app,c);
  assert.match(el('grid').innerHTML,/<a class="store-card" href="\/store\/123"/);
  assert.match(el('heroLatest').innerHTML,/<a class="hero-mini-row" href="\/store\/123"/);
  assert.match(el('categoryGrid').innerHTML,/<a href="\/category\//);
  assert.match(el('nationalCategories').innerHTML,/<a class="national-cat-row"/);
  assert.match(el('grid').innerHTML,/&lt;script&gt;unsafe&lt;\/script&gt;/);
  assert.doesNotMatch(el('grid').innerHTML,/<script>/);
  assert.doesNotMatch(app,/location\.href=`\/(store|category|area)\//);
  assert.match(app,/https:\/\/buzz-now-1\.onrender\.com\/open-close/);
});
console.log(`${passed} regression checks passed.`);
