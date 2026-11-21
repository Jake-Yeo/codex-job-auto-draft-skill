/* Only the document attachment operation is available to the local bridge. */
importScripts("bridge-config.js");
const config = globalThis.JOB_APPLICATIONS_BRIDGE;
const isJobs = group => group?.title?.trim().toLowerCase() === "jobs";
const clean = url => {
  const parsed = new URL(url);
  return parsed.origin + parsed.pathname;
};
function forbidden(url) {
  try {
    const parsed = new URL(url);
    return !["http:", "https:"].includes(parsed.protocol) ||
      !!parsed.username || !!parsed.password ||
      ["mail.google.com", "gmail.com", "accounts.google.com", "discord.com"].includes(parsed.hostname);
  } catch {
    return true;
  }
}
async function bridge(path, body) {
  const response = await fetch(config.base + path, {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-AutoApply-Pipeline": config.token},
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(2500)
  });
  if (!response.ok) throw Error("The local attachment bridge is unavailable");
  return response.json();
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
        target,files:['attachment.js'],
      });
      await requireEmployerTab();
      const [receipt]=await chrome.scripting.executeScript({
        target,func:async request=>{
          try {return await globalThis.JobApplicationsAttachPDF(request);}
          catch(error) {return {status:'blocked',detail:error.message};}
        },
        args:[{...document,expectedHref:frame.result}],
      });
      if(!receipt?.result?.status) throw Error('The frame did not report the upload; inspect it before retrying');
      receipts.push({field:document.label,file:document.name,...receipt.result});
    } catch(error) {
      receipts.push({field:document.label,file:document.name,status:'blocked',detail:error.message});
    }
  }
  return {receipts};
}

let polling = false;
async function poll() {
  if (polling) return;
  polling = true;
  try {
    const command = await bridge("/poll", {extension_id: chrome.runtime.id, ...config.protocol});
    if (!command) return;
    let result;
    try {
      if (command.op !== "attach-documents") throw Error("This extension only attaches PDFs");
      result = await attachDocuments(command.data);
    } catch (error) {
      result = {error: error.message};
    }
    await bridge("/result", {id: command.id, result});
  } catch {
    // No bridge is listening between uploads.
  } finally {
    polling = false;
  }
}
const alarm = "job-applications-attachment";
chrome.alarms.onAlarm.addListener(entry => { if (entry.name === alarm) poll(); });
chrome.action.onClicked.addListener(() => poll());
async function start() {
  if (!await chrome.alarms.get(alarm)) await chrome.alarms.create(alarm, {periodInMinutes: 0.5});
  await poll();
}
chrome.runtime.onStartup.addListener(start);
chrome.runtime.onInstalled.addListener(start);
poll();
