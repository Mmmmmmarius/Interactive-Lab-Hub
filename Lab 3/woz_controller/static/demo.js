const $ = id => document.getElementById(id);
const fmt = (value, options) => new Date(value).toLocaleString('en-US', {timeZone:'America/New_York', ...options});
let sending = false;
async function refresh(){
  try{
    const response = await fetch('/api/demo');
    if(!response.ok) throw new Error('Demo service is not connected');
    const {now,state:s} = await response.json();
    $('clock').textContent = fmt(now,{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
    $('day').textContent = fmt(now,{month:'short',day:'numeric',year:'numeric'});
    document.body.dataset.status=s.status;
    $('status').textContent=s.status.charAt(0).toUpperCase()+s.status.slice(1);
    $('phase').textContent={speaking:'The box is speaking',listening:'Waiting for your reply',thinking:'A little dramatic pause',quiet:'Just sitting here for now',paused:'Paused'}[s.status];
    $('line').textContent=s.last_spoken || 'Before 10:30, silence is a talent too.';
    $('heard').textContent=s.transcript ? 'Last simulated user reply: '+s.transcript : '';
    const busy=Boolean(s.active_action)||s.schedule.busy;
    $('next').disabled=busy||sending||!s.schedule.next_at;
    $('quiet').disabled=busy||sending;
    $('reset').disabled=sending;
    $('next').textContent=s.schedule.next_kind==='morning' ? 'Start the morning at 10:30' : 'Skip to the next random remark';
    $('next-event').textContent=s.schedule.next_at ? 'Next: '+fmt(s.schedule.next_at,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}) : 'The next event is scheduled after this exchange ends.';
    $('events').replaceChildren(...s.events.map(e=>{const li=document.createElement('li');li.textContent=e.message;return li;}));
  }catch(error){$('error').textContent=error.message+'. Please run python demo.py.';}
}
async function step(action){
  if(sending)return;
  sending=true;$('error').textContent='';
  try{
    const response=await fetch('/api/demo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,transcript:action==='next'&&$('respond').checked ? $('reply').value : ''})});
    const result=await response.json();if(!result.ok)throw new Error(result.error);
  }catch(error){$('error').textContent=error.message;}
  finally{sending=false;await refresh();}
}
for(const action of ['next','quiet','reset'])$(action).addEventListener('click',()=>step(action));
refresh();setInterval(refresh,200);
