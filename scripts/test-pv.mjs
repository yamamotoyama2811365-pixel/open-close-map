import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const code=fs.readFileSync(process.argv[2]||new URL('../first-party-pv.js',import.meta.url),'utf8');
function env({search='',referrer='',navigator={},visible='visible',origin='https://open-close-map.onrender.com',pathname='/'}={}){
  const calls=[],listeners={};
  const c={URL,URLSearchParams,Promise,location:{origin,pathname,search},navigator,
    document:{referrer,visibilityState:visible,addEventListener:(n,f)=>{listeners[n]=f;}},
    fetch:(url,opts)=>{calls.push([url,opts]);return Promise.resolve({status:204});}};
  c.window=c;vm.createContext(c);return {c,calls,listeners,run:()=>vm.runInContext(code,c)};
}
let checks=0;
for(const [referrer,source] of [['https://www.google.co.jp/search?q=private','google'],['https://search.yahoo.co.jp/search?p=secret','yahoo'],['https://google.com.evil.example/','referral'],['https://open-close-map.onrender.com/store/1','internal'],['','direct_or_unknown']]){
  const e=env({referrer,search:'?utm_source=secret'});e.run();e.run();
  assert.equal(e.calls.length,1);const [u,o]=e.calls[0];
  assert.deepEqual(JSON.parse(o.body),{page:'/',source,is_test:false});
  assert.equal(o.credentials,'omit');assert.equal(o.referrerPolicy,'no-referrer');checks++;
}
for(const params of [{navigator:{doNotTrack:'1'}},{navigator:{globalPrivacyControl:true}},{navigator:{webdriver:true}},{search:'?ocm_pv=off'},{origin:'https://buzz-now-1.onrender.com'},{pathname:'/corporate/'},{pathname:'/api/anything'}]){
  const e=env(params);e.run();assert.equal(e.calls.length,0);checks++;
}
const e=env({visible:'hidden'});e.run();assert.equal(e.calls.length,0);e.c.document.visibilityState='visible';e.listeners.visibilitychange();e.listeners.visibilitychange();assert.equal(e.calls.length,1);checks++;
const probe=env({search:'?ocm_pv_test=1',navigator:{webdriver:true}});probe.run();assert.equal(JSON.parse(probe.calls[0][1].body).is_test,true);checks++;
const detail=env({pathname:'/detail.html',search:'?id=42&q=secret'});detail.run();assert.equal(JSON.parse(detail.calls[0][1].body).page,'/store/42');checks++;
console.log(`${checks} client checks passed`);
