import {mkdir,readFile,writeFile,cp} from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
await mkdir('dist/server',{recursive:true}); await mkdir('dist/.openai',{recursive:true});
let source=await readFile('worker/index.js','utf8');
const html=await readFile('web/index.html','utf8');
const spec=await readFile('PRODUCT_SPECIFICATION.md','utf8');
let research;
try{research=JSON.parse(gunzipSync(await readFile('research.json.gz')).toString('utf8'));}
catch(error){if(error.code!=='ENOENT')throw error;research=JSON.parse(await readFile('research.json','utf8'));}
const report=await readFile('UPDATED_BACKTEST.md','utf8');
const h4=await readFile('H4_BACKTEST.md','utf8');
const management=await readFile('MANAGEMENT_REPORT.md','utf8');
const m15=await readFile('M15_BACKTEST.md','utf8');
const mt5=await readFile('MT5_PACKAGE.txt','utf8');
source=source.replace('/*BUILD_DATA*/',`const HTML=${JSON.stringify(html)};const SPEC=${JSON.stringify(spec)};const RESEARCH=${JSON.stringify(research)};const REPORT=${JSON.stringify(report)};const H4REPORT=${JSON.stringify(h4)};const MANAGEMENT=${JSON.stringify(management)};const M15REPORT=${JSON.stringify(m15)};const MT5PACKAGE=${JSON.stringify(mt5)};`);
await writeFile('dist/server/index.js',source);await cp('.openai/hosting.json','dist/.openai/hosting.json');
await cp('drizzle','dist/.openai/drizzle',{recursive:true});
console.log('Built Worker, UI, research and schema migrations.');
