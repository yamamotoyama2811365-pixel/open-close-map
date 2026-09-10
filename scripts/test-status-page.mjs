import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const script=fs.readFileSync(new URL('../status-page.js',import.meta.url),'utf8');
let passed=0;
async function check(name,fn){await fn();console.log('PASS '+name);passed++;}
const row=(id,status,extra={})=>({id,status,name:'店舗 '+id,open_date:'2026-09-10',close_date:'2026-09-10',...extra});
async function run(mode,fixtures={},customFetch){
 const urls=[];
 const make=()=>({textContent:'',innerHTML:'',attrs:{},setAttribute(k,v){this.attrs[k]=v;}});
 const elements={statusTotal:make(),statusLatest:make(),label:make()};
 const ctx={URLSearchParams,AbortController,setTimeout,clearTimeout,Date,console:{error(){}},
  document:{body:{dataset:{statusPage:mode}},getElementById:id=>elements[id],querySelector:()=>elements.label},
  fetch:async(url,options)=>{urls.push(url);const status=new URL(url).searchParams.get('status');
   if(customFetch)return customFetch(status,url,options);
   assert.ok(status,'Must filter before limiting');
   return {ok:true,json:async()=>({items:fixtures[status]||[]})};
  }};
 ctx.window=ctx;vm.createContext(ctx);vm.runInContext(script,ctx);
 await ctx.__ocmStatusPageReady;
 return {urls,...elements};
}
await check('closing queries both exact statuses before limit',async()=>{
 const r=await run('closing',{closing:[row(1,'closing')],closed:[row(999,'closed')]});
 assert.equal(r.urls.length,2);assert.ok(r.urls.some(u=>u.includes('status=closed')));assert.ok(r.urls.some(u=>u.includes('status=closing')));
 assert.equal(r.statusTotal.textContent,'2');assert.match(r.statusLatest.innerHTML,/\/store\/999/);
});
await check('opening queries both statuses and preserves native links',async()=>{
 const r=await run('opening',{open:[row(1,'open')],opening:[row(2,'opening')]});
 assert.equal(r.statusTotal.textContent,'2');assert.ok(r.urls.every(u=>['open','opening'].includes(new URL(u).searchParams.get('status'))));
 assert.match(r.statusLatest.innerHTML,/<a class="status-latest-item" href="\/store\/2"/);
});
await check('count explicitly describes fetched records, not nationwide total',async()=>{
 const r=await run('closing',{closed:Array.from({length:21},(_,i)=>row(i+1,'closed'))});
 assert.equal(r.statusTotal.textContent,'21');assert.equal(r.label.textContent,'取得した掲載情報');
 assert.equal((r.statusLatest.innerHTML.match(/class="status-latest-item"/g)||[]).length,18);
 assert.match(r.statusLatest.innerHTML,/18件を表示/);
});
await check('capped batch adds a lower-bound indicator and notice',async()=>{
 const r=await run('closing',{closed:Array.from({length:200},(_,i)=>row(i+1,'closed'))});
 assert.equal(r.statusTotal.textContent,'200+');assert.match(r.statusLatest.innerHTML,/取得上限/);
});
await check('legitimate empty results show zero',async()=>{
 const r=await run('closing');assert.equal(r.statusTotal.textContent,'0');
 assert.match(r.statusLatest.innerHTML,/現在掲載できる情報がありません/);assert.equal(r.statusLatest.attrs['aria-busy'],'false');
});
await check('one failed batch does not show a false zero or partial count',async()=>{
 const r=await run('closing',{},async s=>s==='closed'?{ok:false,status:503}:{ok:true,json:async()=>({items:[row(1,'closing')]})});
 assert.equal(r.statusTotal.textContent,'-');assert.match(r.statusLatest.innerHTML,/読み込めません/);
});
await check('ignored filters are not silently accepted',async()=>{
 const r=await run('closing',{closing:[row(1,'open')]});assert.equal(r.statusTotal.textContent,'-');
});
await check('bad JSON shape fails visibly',async()=>{
 const r=await run('opening',{},async()=>({ok:true,json:async()=>({unexpected:[]})}));assert.equal(r.statusTotal.textContent,'-');
});
await check('source strings are HTML-escaped',async()=>{
 const r=await run('closing',{closed:[row(1,'closed',{name:'<img src=x onerror="evil()">'})]});
 assert.match(r.statusLatest.innerHTML,/&lt;img/);assert.doesNotMatch(r.statusLatest.innerHTML,/<img/);
});
await check('dates use the status-specific field; missing dates are neutral',async()=>{
 const r=await run('closing',{closing:[row(1,'closing',{open_date:'2024-01-01',close_date:null})]});
 assert.match(r.statusLatest.innerHTML,/日付未確認/);assert.match(r.statusLatest.innerHTML,/>閉店情報</);assert.doesNotMatch(r.statusLatest.innerHTML,/2024-01-01/);
});
await check('quality-pending records are not asserted as confirmed events',async()=>{
 const r=await run('closing',{closed:[row(1,'closed',{quality_pending:true})]});assert.match(r.statusLatest.innerHTML,/情報確認中/);
});
await check('deduplication is by ID only, not by store name',async()=>{
 const a=row(1,'closed',{name:'同じ名前'}),b=row(2,'closed',{name:'同じ名前'});
 const r=await run('closing',{closed:[a,a,b]});assert.equal(r.statusTotal.textContent,'2');
});
await check('event dates descending order and Japan-based future label',async()=>{
 const r=await run('closing',{closing:[row(1,'closing',{close_date:'2099-01-01'}),row(2,'closing',{close_date:'2000-01-01'})]});
 assert.ok(r.statusLatest.innerHTML.indexOf('/store/1')<r.statusLatest.innerHTML.indexOf('/store/2'));
 assert.match(r.statusLatest.innerHTML,/>閉店予定</);assert.match(r.statusLatest.innerHTML,/>閉店</);
});
console.log(`${passed} checks passed.`);
