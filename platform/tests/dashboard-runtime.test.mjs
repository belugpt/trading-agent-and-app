import {test} from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import {readFileSync} from 'node:fs';
const html=readFileSync('web/index.html','utf8'),script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
test('expanded dashboard renders aligned M15, management evidence and filters',async()=>{
 const elements=new Map();class Element{constructor(){this.value='';this.textContent='';this.dataset={};this.classList={toggle(){},add(){},remove(){}};}set innerHTML(s){this.html=s;if(this.select){const first=s.match(/<option(?: value="([^"]*)")?[^>]*>([^<]*)/);this.value=first?(first[1]??first[2]):'';}}get innerHTML(){return this.html||'';}insertAdjacentHTML(){} }
 for(const match of html.matchAll(/id="([^"]+)"/g))elements.set(match[1],new Element());
 for(const m of html.matchAll(/<select id="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)){const e=elements.get(m[1]);e.select=true;e.innerHTML=m[2];}
 const nav=[...html.matchAll(/<button data-page="([^"]+)"/g)].map(m=>Object.assign(new Element(),{dataset:{page:m[1]}}));
 const metric={return_percent:10,max_drawdown_percent:5,completed_trades:30,win_rate:.4};const baseline={instrument:'EURUSD',asset_class:'forex',metrics:metric,curve:[{time:'2020-01-01',equity:10000},{time:'2021-01-01',equity:11000}]};
 const research={};for(const key of ['swing','swingH4','swingM15','swingAligned','swingH4Aligned','swingM15Aligned'])research[key]={timeframe:key.includes('M15')?'M15':'H1',results:[baseline]};
 research.management={passes:0,results:[{instrument:'EURUSD',timeframe:'M15',exit:'original',filter:'higher',windows:3,cash_windows:0,baseline_return:1,selected_return:2,selected_dd:5,trades:30,double_cost_return:1,passes_screen:false}],behaviour:[{group:'M15 / all',n:30,win_rate:.4,mean_r:.1,median_mfe_r:1,p75_mfe_r:2,median_mae_r:.5,favorable_1R_percent:40,stopped_after_1R_percent:20}]};
 const document={querySelector:q=>q.startsWith('#')?elements.get(q.slice(1))||null:null,querySelectorAll:q=>q==='nav button'?nav:[],createElement:()=>new Element()};
 const ctx=vm.createContext({document,location:{origin:'https://test.invalid'},Intl,Date,Number,Math,Object,String,Set,Array,console,setTimeout:()=>{},setInterval:()=>{},fetch:async()=>({ok:true,json:async()=>({records:[],research})})});
 vm.runInContext(script,ctx);await new Promise(resolve=>setImmediate(resolve));
 assert.equal(elements.get('load-error').textContent,'');assert.ok(elements.get('research-table').innerHTML.includes('EURUSD'));
 assert.ok(elements.get('pnl-summary').textContent.includes('Confirmed alignment'));assert.ok(elements.get('management-profiles').innerHTML.includes('higher'));
 assert.ok(elements.get('behaviour-table').innerHTML.includes('M15 / all'));
 elements.get('pnl-source').value='adaptive';elements.get('pnl-source').onchange();
 assert.equal(elements.get('pnl-timeframe').disabled,true);assert.ok(elements.get('pnl-summary').textContent.includes('Frozen-profile'));
 assert.ok(elements.get('swing-report').innerHTML.includes('Frozen forward profile'));
 elements.get('research-sign').value='negative';elements.get('research-sign').onchange();assert.ok(!elements.get('research-table').innerHTML.includes('<td>EURUSD</td>'));
 elements.get('research-sign').value='positive';elements.get('research-sign').onchange();assert.ok(elements.get('research-table').innerHTML.includes('<td>EURUSD</td>'));
});
