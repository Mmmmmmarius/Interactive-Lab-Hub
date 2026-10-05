const $ = id => document.getElementById(id);
const fmt = (value, options) => new Date(value).toLocaleString('en-US', {timeZone:'America/New_York', ...options});
let sending = false;
async function refresh(){
  try{
    const response = await fetch('/api/demo');
    if(!response.ok) throw new Error('演示服务未连接');
    const {now,state:s} = await response.json();
    $('clock').textContent = fmt(now,{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
    $('day').textContent = fmt(now,{month:'short',day:'numeric',year:'numeric'});
    document.body.dataset.status=s.status;
    $('status').textContent=s.status.charAt(0).toUpperCase()+s.status.slice(1);
    $('phase').textContent={speaking:'盒子在说话',listening:'等待你搭话',thinking:'一点戏剧性的停顿',quiet:'此刻只负责摆着',paused:'已暂停'}[s.status];
    $('line').textContent=s.last_spoken || '在 10:30 之前，安静也是一种才华。';
    $('heard').textContent=s.transcript ? '上一条模拟用户：'+s.transcript : '';
    const busy=Boolean(s.active_action)||s.schedule.busy;
    $('next').disabled=busy||sending||!s.schedule.next_at;
    $('quiet').disabled=busy||sending;
    $('reset').disabled=sending;
    $('next').textContent=s.schedule.next_kind==='morning' ? '到 10:30，开始早晨' : '跳到下一次随机闲聊';
    $('next-event').textContent=s.schedule.next_at ? '下一次：'+fmt(s.schedule.next_at,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}) : '当前交流结束后再安排下一次。';
    $('events').replaceChildren(...s.events.map(e=>{const li=document.createElement('li');li.textContent=e.message;return li;}));
  }catch(error){$('error').textContent=error.message+'。请运行 python demo.py。';}
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
