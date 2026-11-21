const input=await new Promise(resolve=>{let value='';if(process.stdin.isTTY)process.stdin.setRawMode(true);process.stdin.setEncoding('utf8');process.stdin.on('data',chunk=>{value+=chunk;if(/[\r\n]/.test(value)){if(process.stdin.isTTY)process.stdin.setRawMode(false);process.stdin.pause();resolve(value);}});process.stdin.resume();console.log('Ready for private check input (hidden).');});
const {origin,token}=JSON.parse(input);
const headers={'OAI-Sites-Authorization':'Bearer '+token};
for(const path of ['/health','/','/specification','/m15-report','/management-report','/downloads/SME_MT5_Package.zip']){
 const r=await fetch(origin+path,{headers});if(!r.ok)throw Error(path+' HTTP '+r.status);
 if(path.endsWith('.zip')){const bytes=new Uint8Array(await r.arrayBuffer());if(bytes[0]!==80||bytes[1]!==75)throw Error('Invalid ZIP download');}
 else {const value=await r.text();if(path==='/health'){const h=JSON.parse(value);if(!h.database)throw Error('DB binding missing');}if(path==='/'){if(!value.includes('pnl-alignment')||!value.includes('swingM15Aligned'))throw Error('Updated UI missing');}}
 console.log('PASS',path,r.status);
}
// Service access has no browser user identity, so private browser-data APIs must reject it.
const state=await fetch(origin+'/api/state',{headers});if(state.status!==401)throw Error('Browser API service isolation failed: '+state.status);
console.log('PASS browser identity required');
