/*BUILD_DATA*/
const json=(v,status=200)=>new Response(JSON.stringify(v),{status,headers:{'content-type':'application/json','cache-control':'no-store','x-content-type-options':'nosniff'}});
const fail=(message,status=400)=>Object.assign(new Error(message),{status});
function number(v,min,max){if(typeof v!=='number'||!Number.isFinite(v)||v<min||v>max)throw fail('Invalid numeric input');return v;}
function text(v,max=120){if(typeof v!=='string'||!v.trim()||v.length>max)throw fail('Invalid text input');return v.trim();}
export function sizing(b){
 const equity=number(b.equity,1,1e12),risk=number(b.risk,0.01,5),entry=number(b.entry,0.00000001,1e12),stop=number(b.stop,0.00000001,1e12);
 const tick=number(b.tick,0.000000001,1e9),tickValue=number(b.tickValue,0.000000001,1e9),step=number(b.step,0.00000001,100),min=number(b.min,0.00000001,100),max=number(b.max,min,1e6);
 const reserve=number(b.reserve,0,100),openRisk=number(b.openRisk,0,100),cap=number(b.cap,0.01,20);
 if(entry===stop)throw fail('Entry and stop must differ');
 const budget=equity*risk/100,lossPerLot=Math.abs(entry-stop)/tick*tickValue*(1+reserve/100);
 const lots=Number((Math.floor(Math.min(budget/lossPerLot,max)/step+1e-10)*step).toFixed(8));
 return {lots:lots<min?0:lots,budget,estimatedLoss:lots<min?0:lots*lossPerLot,blocked:lots<min||risk+openRisk>cap,reason:lots<min?'Minimum volume exceeds budget':risk+openRisk>cap?'Portfolio risk cap exceeded':'Sizing estimate ready — verify broker contract values'};
}
async function body(request){if(Number(request.headers.get('content-length')||0)>32768)throw fail('Payload too large',413);const s=await request.text();if(s.length>32768)throw fail('Payload too large',413);try{return JSON.parse(s);}catch{throw fail('Invalid JSON');}}
async function record(env,kind,payload,id=crypto.randomUUID()){
 if(!env.DB)throw fail('Database unavailable',503);
 const created=new Date().toISOString();
 const result=await env.DB.prepare('INSERT OR IGNORE INTO records(id,kind,payload,created_at) VALUES(?,?,?,?)').bind(id,kind,JSON.stringify(payload),created).run();
 return {id,duplicate:result.meta?.changes===0,created_at:created};
}
export default {async fetch(request,env){try{
 const u=new URL(request.url),path=u.pathname;
 if(path==='/health'){
   if(!env.DB)throw fail('Database unavailable',503);
   await env.DB.prepare('SELECT id FROM records LIMIT 1').all();
   return json({status:'ok',version:'0.1.0',execution:'disabled',database:true});
 }
 const user=request.headers.get('oai-authenticated-user-id');
 // Owner-private Sites dispatch authenticates service callers before this handler.
 // Bridge is append-only; it cannot issue trade instructions or read records.
 if(path==='/api/bridge'&&request.method==='POST'){
   const b=await body(request),kind=text(b.kind,30);
   if(!['heartbeat','setup','deal','error'].includes(kind))throw fail('Unsupported event kind');
   const id=text(b.eventId,180),account=text(b.account,80),terminal=text(b.terminal,80);
   const payload={account,terminal,symbol:b.symbol?text(b.symbol,32):'',message:b.message?text(b.message,2000):'',strategyVersion:b.strategyVersion?text(b.strategyVersion,80):'unknown',eventTime:b.eventTime?text(b.eventTime,50):null};
   if(kind==='heartbeat'){payload.equity=number(b.equity,0,1e12);payload.balance=number(b.balance,0,1e12);payload.mode=['demo','live'].includes(b.mode)?b.mode:'unknown';}
   return json(await record(env,kind,payload,id),201);
 }
 if(path.startsWith('/api/')&&!user)return json({error:'Sign in to access your operations workspace'},401);
 if(request.method==='POST'){
   const origin=request.headers.get('origin');if(origin&&origin!==u.origin)throw fail('Cross-origin request rejected',403);
   if(path==='/api/size')return json(sizing(await body(request)));
   if(path==='/api/journal'){
     const b=await body(request);return json(await record(env,'journal',{symbol:text(b.symbol,32).toUpperCase(),direction:['buy','sell'].includes(b.direction)?b.direction:'buy',notes:text(b.notes,4000),outcome:number(b.outcome,-1e9,1e9),strategyVersion:text(b.strategyVersion,80),source:'manual',actor:user}),201);
   }
 }
 if(path==='/api/state'&&request.method==='GET'){
   if(!env.DB)throw fail('Database unavailable',503);
   const {results}=await env.DB.prepare('SELECT id,kind,payload,created_at FROM records ORDER BY created_at DESC LIMIT 300').all();
   return json({records:results.map(r=>({...r,payload:JSON.parse(r.payload)})),execution:'disabled',research:RESEARCH});
 }
 if(path==='/specification'&&request.method==='GET')return new Response(SPEC,{headers:{'content-type':'text/plain; charset=utf-8','content-disposition':'inline; filename=PRODUCT_SPECIFICATION.md'}});
 if(path!=='/'||request.method!=='GET')return json({error:'Not found'},404);
 return new Response(HTML,{headers:{'content-type':'text/html; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff','content-security-policy':"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'"}});
 }catch(e){return json({error:e.status?e.message:'Service error; retry or inspect server logs'},e.status||500);}}};
