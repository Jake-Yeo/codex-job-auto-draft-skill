// Keep an extension context available for read-only Path 2 inventory.
// Chrome wakes this worker on the alarm without opening a tab or window.
const wakeAlarm = "path2-inventory-wake";

async function scheduleWake() {
  if (!(await chrome.alarms.get(wakeAlarm))) {
    await chrome.alarms.create(wakeAlarm, {periodInMinutes: 0.5});
  }
}

chrome.alarms.onAlarm.addListener(() => {});
chrome.runtime.onInstalled.addListener(scheduleWake);
chrome.runtime.onStartup.addListener(scheduleWake);
scheduleWake();
