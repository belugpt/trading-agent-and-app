from pathlib import Path
p=Path('platform/web/index.html');s=p.read_text()
s=s.replace('<button data-page="setups">','<button data-page="alerts">Alerts</button><button data-page="setups">')
s=s.replace("setups:'Setups & events',","alerts:'Setup & crossover alerts',setups:'Setups & events',")
s=s.replace('<option>setup</option>','<option>setup</option><option>crossover</option>')
s=s.replace('<section id="setups"', '''<section id="alerts" class="section page hidden"><div class="row"><h2>Setup &amp; crossover alerts <span id="alert-count" class="badge">0</span></h2><button id="mark-alerts-read">Mark all read on this device</button></div><p>Confirmed setup alerts are separate from crossover observations. Crossovers alone do not authorize an entry. The app checks for updates every 15 seconds while open; phone push is configured in MT5. Run the monitor in the same terminal to forward indicator/EA alerts.</p><div class="card scroll" id="alert-inbox"></div></section><section id="setups"''')
s=s.replace('renderManagement();}','renderManagement();renderAlerts();}')
s=s.replace('setInterval(load,60000)','setInterval(load,15000)')
js='''
let alertInitialized=false,announcedAlerts=new Set();
function readAlertTime(){try{return localStorage.getItem('sme-alert-read')||'';}catch{return '';}}
function renderAlerts(){
 const rows=state.records.filter(r=>r.kind==='setup'||r.kind==='crossover'),read=readAlertTime();
 $('#alert-count').textContent=rows.filter(r=>r.created_at>read).length+' unread';
 $('#alert-inbox').innerHTML=rows.length?table(['Received','Type','Symbol','Message'],rows.map(r=>[new Date(r.created_at).toLocaleString(),r.kind,r.payload.symbol,r.payload.message])):'<div class="empty">No setup or crossover alerts received yet.</div>';
 const fresh=rows.filter(r=>!announcedAlerts.has(r.id));if(alertInitialized&&fresh.length)toast(fresh[0].payload.message);
 rows.forEach(r=>announcedAlerts.add(r.id));alertInitialized=true;
}
$('#mark-alerts-read').onclick=()=>{try{localStorage.setItem('sme-alert-read',new Date().toISOString());renderAlerts();}catch{toast('This browser cannot store the read preference.');}};
'''
s=s.replace('</script>',js+'</script>');p.write_text(s,encoding='utf-8')
