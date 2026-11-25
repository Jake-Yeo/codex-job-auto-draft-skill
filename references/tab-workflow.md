# Existing jobs tabs

The user supplies the application tabs in a Chrome group named **jobs**. Discover actual group names, window IDs and tab IDs. Match the name case-insensitively. Keep every tab in its existing group and window. There is no Working, Ready, Pending help, Saved drafts or AutoApply group workflow and no database synchronization.

Work on one existing jobs tab at a time. Use the supported browser inventory to find its exact tab and window. Use the draft guard to resume after interruptions. Record unanswered mandatory confirmations with `await-confirmation` and other unresolved tab-specific blockers with `defer` so the next tab can proceed. Do not move or regroup tabs. Re-query live tabs if a tab disappears. When healthy Chrome inventory confirms a tab closed, record it as closed. Report it as submitted only when the applicant confirms submission. Preserve the marker during a connection problem or when the tab is still open outside the group.

Recovery must preserve the employer draft. Do not reload, navigate to its current URL, restart Apply, clear cookies or create a replacement tab. Inspect the current form and fix the affected control. An interrupted command may already have changed the page: inspect its result and current values before deciding whether anything remains to do.

A login title, URL or stale gate flag does not establish a current account blocker. Inspect the exact form, especially after the applicant says he signed in. Fill accessible non-credential application fields while leaving credentials untouched; hand off only the actual remaining authentication action.

Workday can show a generic `VPS|…` save error while displaying the account email and populated form. If no field is identified as invalid, preserve the answers and check whether the session needs renewal. After the applicant signs in, resume the same draft and check which fields and attachments persisted before re-entering anything. If navigating Back opens a **Discard Application** dialog, cancel it.

## Draft order

Briefly inspect the jobs tabs in the background for a usable signed-in form, a session-expiry notice, or an actual sign-in gate. Resume any active draft first. When choosing the next tab, follow any order the applicant specified. Otherwise, do accessible signed-in drafts first, with visible expiry warnings or freshly restored sessions ahead of other signed-in drafts. Examples include Workday, signed-in SAP SuccessFactors or iCIMS drafts, and UBC Scope. Use the live form to determine whether the draft relies on a session. Keep the original tab order within each priority, then work through public forms.

Check actual sign-in gates early and handle them through [the account workflow](employer-accounts.md). Continue with the next accessible draft while the applicant signs in. When sign-in is restored, resume the same draft before the remaining public forms once the current draft is finished or preserved. Use an observed **Stay signed in** control when available and save non-final progress early on session-sensitive portals.

## Keep the applicant's active tab

Attach to the existing job target with `switch_tab(targetId, activate=False)` at the start of each page interaction call. Use browser-scoped controls on that tab and its observed frames. Leave the applicant's active tab, window and desktop focus alone. Keep field focus within the attached page. Leave Chrome's existing windows and tabs in place during drafting and recovery. Avoid `activate_tab`, `Target.activateTarget`, `Page.bringToFront`, `Browser.setWindowBounds`, `Emulation.setFocusEmulationEnabled`, global keyboard or mouse input, and opening or closing even temporary Chrome targets. Use the draft guard and chat to identify finished and unfinished drafts. Run the CLI with `BH_TAB_MARKER=0` to leave tab titles alone and with debug clicks disabled.

If Chrome seems to disappear, read the inventory's window IDs and states and check whether the original tab remains accessible. Keep a minimized or unfocused window in its existing state. Reattach only to the known surviving tab. Use the existing setup or recovery workflow if the connection really disappeared and avoid restarting Chrome as part of a draft run.

After a detached session, missed click or timeout, inspect the form for any result from the interrupted action. Recover control of the same tab and use the documented repair. Fill and save all accessible sections before preserving an unresolved draft. If a file is missing, try the applicable [attachment procedure](application-materials.md#resume-and-required-uploads), finish other fields, and verify any files already accepted. Defer only the remaining blocker and go on to the next accessible jobs tab. Prioritize a newly signed-in draft as described in [draft order](#draft-order). Return to other deferred tabs for an available retry after the first pass.

## Preserve unsaved changes

Verify existing attachments from the filenames and statuses on the form. Use a saved local copy to inspect or preserve a document. A portal control labeled **Download** or **Preview** can navigate away from an unsaved draft. If a portal download is necessary, verify a non-final save first and use a control that keeps the original draft open.

Avoid actions that can open Chrome’s **Leave site?** or **Changes you made may not be saved** dialog. If one appears unexpectedly, choose **Stay** or **Cancel** and verify the current draft before continuing.

## Recover an embedded form before deferring

- After a transient input or connection error, check the original tab and rebind it if the handle is stale. Use the step and saved values the form shows now. The recovery marker is a checkpoint, and a wizard can return to an earlier step while retaining some answers. Confirm whether the résumé is present before retrying an attachment.
- If a readable form loses field focus during entry, inspect the current snapshot for the embedded application frame. Use a supported browser locator scoped to the observed frame and field label, then verify the committed value. Talemetry can expose its application in `iframe#talemetry_apply_iframe`. Reinspect the live frame and fields after advancing.
- Finish and verify the draft when same-tab input recovers. If a supported retry still fails, save the accessible fields and defer with the observed step, the exact remaining control, and the last error. Revisit the original tab once after the other accessible jobs if the connection has recovered.

## Connect with the Browser Use Path 2 CLI

Use the [Path 2 CLI](https://github.com/browser-use/browser-use#path-2-cli) with the already-running local Chrome profile that holds the supplied applications. Enable local remote debugging at `chrome://inspect/#remote-debugging`. Reuse the File Upload Helper when it is already loaded in that profile, or load the AutoApply Path 2 Tab Inventory extension using the [setup guide](setup.html). The inventory script attaches briefly to a loaded extension context to read existing groups, tabs, window states, and DevTools target IDs. It does not create or close Chrome targets.

Run `browser-use --doctor` during setup. If the CLI is missing and `uv` is available, use `uvx --python 3.12 --from browser-use==1.0.8 browser-use` in place of `browser-use`. Use the default local daemon throughout the batch so the CLI attaches to existing tabs. If the inventory worker is temporarily idle, retry discovery against the same running profile. Keep the current Chrome window in place when handling a connection or remote-debugging prompt.

```sh
BU_NAME=default BH_TAB_MARKER=0 BH_DEBUG_CLICKS= browser-use < "<skill-directory>/scripts/browser_use_cli_tabs.py"
```

Replace `<skill-directory>` with the actual skill directory. Match the `group` field to `jobs` case-insensitively. Use `windowId` and `index` to preserve tab order within each priority. Use the numeric `tabId` for the draft guard and AutoApply PDF helper. Use the `targetId` to attach and interact through the CLI. A tab with no available target ID stays open for recovery.

```sh
BU_NAME=default BH_TAB_MARKER=0 BH_DEBUG_CLICKS= browser-use <<'PY'
switch_tab("OBSERVED_TARGET_ID", activate=False)
print(page_info())
PY
```

Use `cdp("Accessibility.getFullAXTree")` for accessible controls and scope input to the verified job tab or frame. For visual checks, pass the returned DevTools session ID explicitly to `Page.captureScreenshot`. Browser Use's `capture_screenshot()` and unscoped screenshot commands can activate a hidden tab when capture times out.

```sh
BU_NAME=default BH_TAB_MARKER=0 BH_DEBUG_CLICKS= browser-use <<'PY'
from base64 import b64decode
from pathlib import Path

session_id = switch_tab("OBSERVED_TARGET_ID", activate=False)
shot = cdp("Page.captureScreenshot", session_id=session_id, format="png", _response_timeout=8)
Path("/absolute/path/to/screenshot.png").write_bytes(b64decode(shot["data"]))
PY
```

If background capture stalls, use the DOM or accessibility tree and the observed field's controls. If a control still needs the foreground after a same-tab retry, save the accessible work and defer that control without changing the active tab. Try the attachment extension first for PDFs, then use the [tab-scoped file input](application-materials.md#resume-and-required-uploads) for fallback without opening a native file dialog.

For recovery, rerun the tab inventory and match the original numeric tab ID, group, and application before reattaching to its current target ID. Only use an absent ID in `openTabIds` as evidence of closure after confirming the inventory is healthy and from the original Chrome profile. Keep the original employer page open throughout recovery.
