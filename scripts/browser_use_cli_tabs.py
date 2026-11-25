"""Run through browser-use stdin to discover existing Chrome jobs-group tabs."""

import json
import time
from urllib.parse import urlsplit


# Chrome derives this stable extension ID from the public key in manifest.json.
EXTENSION_ID = "dfacefnblmijogllnpnachcbopnkhhhh"
INVENTORY_ORIGIN = f"chrome-extension://{EXTENSION_ID}"
INVENTORY_WORKER = f"{INVENTORY_ORIGIN}/inventory-worker.js"
INVENTORY_PAGE = f"{INVENTORY_ORIGIN}/inventory.html"
UPLOAD_WORKER_PATH = "/autoapply-worker.js"

READ_INVENTORY = """
async () => {
  const [groups, tabs, targets, windows] = await Promise.all([
    chrome.tabGroups.query({}),
    chrome.tabs.query({}),
    chrome.debugger.getTargets(),
    chrome.windows.getAll({windowTypes: ["normal"]}),
  ]);
  const jobsGroups = groups.filter(group => group.title?.toLowerCase() === "jobs");
  const jobsById = new Map(jobsGroups.map(group => [group.id, group.title]));
  const targetByTab = new Map(
    targets.filter(target => target.type === "page" && Number.isInteger(target.tabId))
      .map(target => [target.tabId, target]),
  );
  const jobsTabs = tabs.filter(tab => jobsById.has(tab.groupId)).map(tab => {
    const target = targetByTab.get(tab.id);
    return {
      tabId: tab.id,
      windowId: tab.windowId,
      index: tab.index,
      group: jobsById.get(tab.groupId),
      url: tab.url,
      title: tab.title,
      targetId: target && target.url === tab.url ? target.id : null,
    };
  });
  jobsTabs.sort((a, b) => a.windowId - b.windowId || a.index - b.index);
  return {
    jobsGroups: jobsGroups.map(({id, title, windowId}) => ({id, title, windowId})),
    openTabIds: tabs.map(tab => tab.id),
    windows: windows.map(({id, state, focused}) => ({id, state, focused})),
    tabs: jobsTabs,
  };
}
"""


def inventory_contexts(targets):
    dedicated, upload = [], []
    for target in targets:
        address = target.get("url", "")
        if not address.startswith("chrome-extension://"):
            continue
        url = urlsplit(address)
        kind = target.get("type")
        if (kind, address) in {("service_worker", INVENTORY_WORKER), ("page", INVENTORY_PAGE)}:
            dedicated.append((target, url.netloc, False))
        elif kind == "service_worker" and url.path == UPLOAD_WORKER_PATH:
            upload.append((target, url.netloc, True))
    return dedicated + upload


def read_context(cdp, target, extension_id, upload_worker):
    session = cdp("Target.attachToTarget", targetId=target["targetId"],
                  flatten=True)["sessionId"]
    try:
        manifest_check = (
            'manifest.name === "File Upload Helper" && '
            'manifest.background?.service_worker === "autoapply-worker.js"'
            if upload_worker else "true"
        )
        expression = f"""(async () => {{
          if (location.href !== {json.dumps(target["url"])} ||
              globalThis.chrome?.runtime?.id !== {json.dumps(extension_id)}) return null;
          const manifest = chrome.runtime.getManifest();
          if (!({manifest_check}) ||
              !chrome.tabGroups?.query || !chrome.tabs?.query ||
              !chrome.debugger?.getTargets || !chrome.windows?.getAll) return null;
          return ({READ_INVENTORY})();
        }})()"""
        response = cdp("Runtime.evaluate", session_id=session, expression=expression,
                       awaitPromise=True, returnByValue=True, _response_timeout=4)
        if "exceptionDetails" in response:
            raise RuntimeError("Chrome could not read the jobs tab inventory.")
        value = response["result"].get("value")
        keys = ("jobsGroups", "openTabIds", "windows", "tabs")
        return value if isinstance(value, dict) and all(
            isinstance(value.get(key), list) for key in keys
        ) else None
    finally:
        try:
            cdp("Target.detachFromTarget", sessionId=session)
        except Exception:
            # Chrome may already have retired this extension context.
            pass


def read_inventory(cdp, wait_seconds=8):
    deadline = time.monotonic() + wait_seconds
    last_error = None
    while True:
        targets = cdp("Target.getTargets")["targetInfos"]
        for context in inventory_contexts(targets):
            try:
                inventory = read_context(cdp, *context)
            except Exception as error:
                last_error = error
                continue
            if inventory is not None:
                return inventory
        if time.monotonic() >= deadline:
            break
        time.sleep(0.25)
    raise RuntimeError(
        "No live AutoApply inventory context in the connected Chrome profile. "
        "Use the loaded File Upload Helper or the current AutoApply Path 2 Tab Inventory extension."
    ) from last_error


if "cdp" in globals():
    print(json.dumps(read_inventory(cdp), ensure_ascii=False, indent=2))
