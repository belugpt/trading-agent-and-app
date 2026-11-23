"""Package verified workspace builds; never install into a live terminal."""
import hashlib,json,zipfile
from pathlib import Path
root=Path('mt5');checks=[]
for name in ['SMAStrat','SME_Agent','SME_Monitor']:
    log=(root/(name+'.log')).read_text(encoding='utf-16')
    assert 'Result: 0 errors, 0 warnings' in log,name+' not cleanly compiled'
    source=root/(name+'.mq5');binary=root/(name+'.ex5');assert binary.exists() and binary.stat().st_mtime>=source.stat().st_mtime
    checks.append(dict(program=name,errors=0,warnings=0,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()))
(root/'COMPILATION.json').write_text(json.dumps(dict(checks=checks,terminal_execution_verified=False,live_installation=False),indent=2),encoding='utf-8')
names=['SMAStrat.mq5','SMAStrat.ex5','SME_Agent.mq5','SME_Agent.ex5','SME_Monitor.mq5','SME_Monitor.ex5','SME_Alignment.mqh','SME_Alerts.mqh','AGENT_SETUP.md','COMPILATION.json']
with zipfile.ZipFile(root/'SME_MT5_Package.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(root/name,name)
print('Packaged three cleanly compiled programs; no live installation.',flush=True)
