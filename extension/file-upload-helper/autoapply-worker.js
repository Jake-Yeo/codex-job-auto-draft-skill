/* AutoApply's local bridge. No OS input, global focus, passwords or Submit command. */
importScripts('autoapply-config.js');
const AA = globalThis.AutoApplyBridge = {};
const C = globalThis.AUTOAPPLY_CONFIG;
const WORKER_REVISION=4;
let running=false;
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const api=async(path,body)=>{
  const response=await fetch(C.base+path,{method:'POST',headers:{'Content-Type':'application/json','X-AutoApply-Pipeline':C.token},body:JSON.stringify(body)});
  const result=await response.json(); if(!response.ok) throw Error(result.detail||'Local pipeline unavailable'); return result;
};
const state=async()=> (await chrome.storage.local.get('autoapplyFormBinding')).autoapplyFormBinding;
const isJobs=group=>group?.title?.trim().toLowerCase()==='jobs';
const clean=url=>{try{const u=new URL(url);return u.origin+u.pathname;}catch{return '';}};
const forbidden=url=>{try{const u=new URL(url);return !['http:','https:'].includes(u.protocol)||['mail.google.com','gmail.com','discord.com','accounts.google.com'].includes(u.hostname);}catch{return true;}};
async function tabCheck() {
  const s=await state(); if(!s) throw Error('Bind an application first');
  const tab=await chrome.tabs.get(s.tab_id); if(forbidden(tab.url)) throw Error('This is not an employer application');
  if(tab.windowId!==s.window_id) throw Error('The application tab moved to another window; rebind it');
  if(tab.groupId!==s.group_id || !isJobs(await chrome.tabGroups.get(tab.groupId))) throw Error('Only the bound tab in the jobs group may be edited');
  return {s,tab};
}
async function inventory() {
  const groups=(await chrome.tabGroups.query({})).filter(isJobs);
  const tabs=(await chrome.tabs.query({})).filter(t=>groups.some(g=>g.id===t.groupId)&&!forbidden(t.url));
  return {observed_at:new Date().toISOString(),groups:groups.map(g=>({id:g.id,window_id:g.windowId,title:g.title})),
    tabs:tabs.sort((a,b)=>a.windowId-b.windowId||a.index-b.index).map(t=>({ref:'chrome:'+t.id,
      tab_id:t.id,window_id:t.windowId,group_id:t.groupId,index:t.index,group:'jobs',url:clean(t.url),title:t.title}))};
}
async function page(op,data={},frameIds) {
  const {tab}=await tabCheck();
  const target={tabId:tab.id,...(frameIds?{frameIds}:{allFrames:true})};
  await chrome.scripting.executeScript({target,files:['widget-runtime.js','form-widgets.js','autoapply-page.js']});
  return chrome.scripting.executeScript({target,func:async request=>globalThis.AutoApplyPage(request),args:[{op,...data}]});
}
async function scans() {
  return (await page('scan')).map(r=>({...r.result,frame_id:r.frameId}));
}
function comparable(frames) {return JSON.stringify(frames.map(f=>({frame_id:f.frame_id,url:f.url,url_key:f.url_key,title:f.title,gate:f.gate,authentication_pending:f.authentication_pending,busy:f.busy,fields:f.fields,buttons:f.buttons,errors:f.errors})).sort((a,b)=>a.frame_id-b.frame_id));}
async function stable() {
  let previous=await scans();
  for(let i=0;i<12;i++) {await wait(350);const next=await scans();if(comparable(previous)===comparable(next)) return next;previous=next;}
  throw Error('The page is still changing. Inspect it again before continuing.');
}
async function capture(attempt=0) {
  const frames=await stable();
  const {tab}=await tabCheck();
  const target={tabId:tab.id};
  const screenshots=[];
  await chrome.debugger.attach(target,'1.3');
  try {
    const layout=await chrome.debugger.sendCommand(target,'Page.getLayoutMetrics');
    const size=layout.cssContentSize||layout.contentSize;
    if(size.height>30000) throw Error('Page is too long for one review; use section screenshots before verifying');
    for(let y=0;y<size.height;y+=1400) {
      const shot=await chrome.debugger.sendCommand(target,'Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:true,
        clip:{x:0,y,width:Math.min(size.width,1600),height:Math.min(1400,size.height-y),scale:1}});
      screenshots.push(shot.data);
    }
  } finally {await chrome.debugger.detach(target);}
  // A screenshot is only evidence for the exact settled form captured alongside it.
  const after=await scans();
  if(comparable(frames)!==comparable(after)) {
    // Recapture only; never rerun filling or reload the employer draft.
    if(attempt<2)return capture(attempt+1);
    throw Error('The form changed during screenshot capture; inspect again');
  }
  return {frames:after,screenshots,url:clean(tab.url),inventory:await inventory()};
}
async function noGate() {
  const frames=await scans();
  if(frames.some(f=>f.gate)) throw Error('Account access required; leave the original tab in jobs for Jake');
  return frames;
}
async function attachDocuments({tab_id,expected_url,frame_url,documents}) {
  const original=await chrome.tabs.get(tab_id);
  const requireEmployerTab=async()=>{
    const tab=await chrome.tabs.get(tab_id);
    if(forbidden(tab.url)||tab.url.split('#')[0]!==expected_url.split('#')[0]) {
      throw Error('The exact employer tab URL changed');
    }
    if(tab.windowId!==original.windowId || tab.groupId!==original.groupId ||
      tab.groupId<0 || !isJobs(await chrome.tabGroups.get(tab.groupId))) {
      throw Error('The original employer tab must stay in its jobs group');
    }
  };
  const receipts=[];
  for(const document of documents) {
    try {
      await requireEmployerTab();
      const frames=await chrome.scripting.executeScript({
        target:{tabId:tab_id,...(frame_url?{allFrames:true}:{frameIds:[0]})},
        func:expected=>(location.origin+location.pathname===expected?location.href:null),
        args:[frame_url||clean(expected_url)],
      });
      const matches=frames.filter(({result})=>result && !forbidden(result));
      if(matches.length!==1 || !matches[0].documentId) {
        throw Error('One matching application frame was not found');
      }
      const frame=matches[0];
      const target={tabId:tab_id,documentIds:[frame.documentId]};
      await chrome.scripting.executeScript({
        target,files:['widget-runtime.js','form-widgets.js','autoapply-page.js'],
      });
      await requireEmployerTab();
      const [receipt]=await chrome.scripting.executeScript({
        target,func:async request=>{
          try {return await globalThis.AutoApplyPage(request);}
          catch(error) {return {status:'blocked',detail:error.message};}
        },
        args:[{op:'attach-document',expectedHref:frame.result,...document}],
      });
      if(!receipt?.result?.status) throw Error('The frame did not report the upload; inspect it before retrying');
      receipts.push({field:document.label,file:document.name,...receipt.result});
    } catch(error) {
      receipts.push({field:document.label,file:document.name,status:'blocked',detail:error.message});
    }
  }
  return {receipts};
}
async function execute(command) {
  const d=command.data;
  if(command.op==='inventory') return {inventory:await inventory()};
  if(command.op==='attach-documents') return attachDocuments(d);
  if(command.op==='bind') {
    const tab=await chrome.tabs.get(d.tab_id);
    if(forbidden(tab.url)||tab.url.split('#')[0]!==d.expected_url.split('#')[0]) throw Error('The exact employer tab URL does not match');
    if(tab.groupId<0 || !isJobs(await chrome.tabGroups.get(tab.groupId))) throw Error('Choose an existing employer tab in the jobs group');
    await chrome.storage.local.set({autoapplyFormBinding:{tab_id:d.tab_id,window_id:tab.windowId,group_id:tab.groupId}});
    return capture();
  }
  if(command.op==='inspect') return capture();
  if(command.op==='fill') {
    await noGate();
    // Run JobWizard components against local profile answers on this exact tab.
    let report=[], failed=new Set();
    for(let pass=0;pass<12;pass++) {
      const current=await noGate();
      const plan=await api('/plan',{frames:current});
      const key=item=>JSON.stringify([item.frame_id,item.field,Array.isArray(item.value)?'multi-choice':item.value,
        current.find(f=>f.frame_id===item.frame_id)?.fields.find(f=>f.id===item.field)?.options]);
      plan.plan=plan.plan.filter(item=>!failed.has(key(item)));
      if(!plan.plan.length) break;
      for(const frameId of [...new Set(plan.plan.map(f=>f.frame_id))]) {
        const results=await page('fill',{plan:plan.plan.filter(f=>f.frame_id===frameId)},[frameId]);
        report.push(...results.map(r=>r.result));
        for(const result of results) for(const failure of result.result.failures||[]) {
          const item=plan.plan.find(f=>f.frame_id===frameId&&f.field===failure.field);
          if(item) failed.add(key(item));
        }
      }
      await wait(250);
    }
    const pending=await api('/plan',{frames:await noGate()});
    const unresolved=[...pending.unresolved,...pending.plan.map(f=>({...f,reason:'answer_not_committed'}))];
    let observation;
    try {observation=await capture();}
    catch(error) {observation={capture_error:error.message,inventory:await inventory()};}
    return {...observation,engine:C.engine,fill_report:report,unresolved};
  }
  if(command.op==='repair') {
    await noGate();
    const result=await page('fill',{plan:d.plan},[d.frame_id]);
    return {...await capture(),repair_report:result.map(r=>r.result)};
  }
  if(command.op==='upload') {
    await noGate();
    const receipts=await page('upload',d,[d.frame_id]);
    return {...await capture(),upload_report:receipts.map(r=>r.result)};
  }
  if(command.op==='edit') {
    await noGate();await page('click',{button:d.button,mode:'edit'},[d.frame_id]);await wait(500);return capture();
  }
  if(command.op==='advance'||command.op==='release') {
    const current=await noGate();
    if(current.some(f=>f.authentication_pending)) throw Error('Account completion stays with Jake; only application fields may be prepared here');
    if(comparable(current)!==comparable(d.expected_frames)) throw Error('Form changed after visual verification; inspect and verify again');
    const {tab}=await tabCheck();
    if(clean(tab.url)!==d.expected_url) throw Error('The tab navigated after verification');
    if(command.op==='release') {
      await chrome.storage.local.remove('autoapplyFormBinding');return {inventory:await inventory(),ready:true,tab_id:tab.id};
    }
    const choices=current.flatMap(f=>f.buttons.filter(b=>b.kind==='next'&&!b.disabled).map(b=>({...b,frame_id:f.frame_id})));
    const choice=d.button?choices.find(b=>b.id===d.button):choices.length===1?choices[0]:null;
    if(!choice) throw Error('Choose one observed non-final Next/Continue/Review control');
    await page('click',{button:choice.id,mode:'advance'},[choice.frame_id]);
    await wait(800);
    const result=await capture();
    const identifiers=frames=>JSON.stringify(frames.map(f=>({url:f.url,fields:f.fields.map(x=>x.id),buttons:f.buttons.map(x=>x.id)})));
    result.advanced=identifiers(current)!==identifiers(result.frames) && !result.frames.some(f=>f.errors.length);
    return result;
  }
  if(command.op==='handoff') {
    const frames=await scans();if(!frames.some(f=>f.gate||f.authentication_pending)) throw Error('Handoff is for an observed account gate only');
    const {tab}=await tabCheck();await chrome.storage.local.remove('autoapplyFormBinding');return {inventory:await inventory(),needs_sign_in:true,tab_id:tab.id};
  }
  if(command.op==='end') {
    if(!['closed','duplicate','skipped'].includes(d.outcome)||!d.reason) throw Error('Record the observed terminal reason first');
    await tabCheck();await chrome.storage.local.remove('autoapplyFormBinding');
    return {inventory:await inventory(),outcome:d.outcome,reason:d.reason};
  }
  throw Error('Unknown pipeline command');
}
async function tick() {
  if(running) return;running=true;
  try {
    const command=await api('/poll',{extension_id:chrome.runtime.id,engine:C.engine,worker_revision:WORKER_REVISION});
    if(command) {
      let result;
      try {result=await execute(command);}catch(error){result={error:error.message};}
      await api('/result',{id:command.id,result});
    }
  } catch {} finally {running=false;}
}
chrome.alarms.create('autoapply-poll',{periodInMinutes:0.5});
chrome.alarms.onAlarm.addListener(a=>{if(a.name==='autoapply-poll') tick();});
setInterval(tick,1000);tick();
