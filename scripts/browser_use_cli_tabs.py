"""Run through browser-use stdin to discover existing Chrome jobs-group tabs."""

import json
import time


# Chrome derives this stable extension ID from the public key in manifest.json.
EXTENSION_ID = "dfacefnblmijogllnpnachcbopnkhhhh"
INVENTORY_URL = f"chrome-extension://{EXTENSION_ID}/inventory.html"

READ_INVENTORY = """
async () => {
  const [groups, tabs, targets] = await Promise.all([
    chrome.tabGroups.query({}),
    chrome.tabs.query({}),
    chrome.debugger.getTargets(),
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
    tabs: jobsTabs,
  };
}
"""


def read_inventory(cdp):
    target = cdp("Target.createTarget", url=INVENTORY_URL, hidden=True,
                 background=True)["targetId"]
    try:
        session = cdp("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]
        expression = (
            f"location.href === {json.dumps(INVENTORY_URL)} && "
            f"globalThis.chrome?.runtime?.id === {json.dumps(EXTENSION_ID)} "
            f"? ({READ_INVENTORY})() : null"
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            response = cdp("Runtime.evaluate", session_id=session, expression=expression,
                           awaitPromise=True, returnByValue=True, _response_timeout=5)
            if "exceptionDetails" in response:
                raise RuntimeError("Chrome could not read the jobs tab inventory.")
            inventory = response["result"].get("value")
            if inventory is not None:
                return inventory
            time.sleep(0.1)
        raise RuntimeError("Load AutoApply Path 2 Tab Inventory in the connected Chrome profile.")
    finally:
        cdp("Target.closeTarget", targetId=target)


print(json.dumps(read_inventory(cdp), ensure_ascii=False, indent=2))
