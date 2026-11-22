# Existing jobs tabs

The user supplies the application tabs in a Chrome group named **jobs**. Discover actual group names, window IDs and tab IDs; match the name case-insensitively and work left to right. Keep every tab in its existing group and window. There is no Working, Ready, Pending help, Saved drafts or AutoApply group workflow and no database synchronization.

Work on one existing jobs tab at a time. Use the supported browser inventory to find its exact tab and window. Use the draft guard to resume after interruptions. Record unanswered mandatory confirmations with `await-confirmation` and other unresolved tab-specific blockers with `defer` so the next tab can proceed. Do not move or regroup tabs. Re-query live tabs if a tab disappears. When healthy Chrome inventory confirms a tab closed, record it as closed. Report it as submitted only when the applicant confirms submission. Preserve the marker during a connection problem or when the tab is still open outside the group.

Recovery must preserve the employer draft. Do not reload, navigate to its current URL, restart Apply, clear cookies or create a replacement tab. Inspect the current form and fix the affected control. An interrupted command may already have changed the page: inspect its result and current values before deciding whether anything remains to do.

A login title, URL or stale gate flag does not establish a current account blocker. Inspect the exact form, especially after the applicant says he signed in. Fill accessible non-credential application fields while leaving credentials untouched; hand off only the actual remaining authentication action.

Workday can show a generic `VPS|…` save error while displaying the account email and populated form. If no field is identified as invalid, preserve the answers and check whether the session needs renewal. After the applicant signs in, resume the same draft and check which fields and attachments persisted before re-entering anything. If navigating Back opens a **Discard Application** dialog, cancel it.

Keep the user's work window and global keyboard/mouse alone. Use browser-scoped controls on the explicit tab. Do not create or activate windows to fill the group. Use the draft guard and the chat handoff to identify finished and unfinished drafts. Run the CLI with `BH_TAB_MARKER=0` to leave tab titles alone.

After a detached session, missed click or timeout, inspect the form for any result from the interrupted action. Recover control of the same tab and use the documented repair. Fill and save all accessible sections before preserving an unresolved draft. If a file is missing, try the applicable [attachment procedure](application-materials.md#resume-and-required-uploads), finish other fields, and verify any files already accepted. Defer only the remaining blocker and go on to the next jobs tab. Return to the deferred tab for an available retry after the first pass.

## Recover an embedded form before deferring

- After a transient input or connection error, check the original tab and rebind it if the handle is stale. Use the step and saved values the form shows now. The recovery marker is a checkpoint, and a wizard can return to an earlier step while retaining some answers. Confirm whether the résumé is present before retrying an attachment.
- If a readable form loses field focus during entry, inspect the current snapshot for the embedded application frame. Use a supported browser locator scoped to the observed frame and field label, then verify the committed value. Talemetry can expose its application in `iframe#talemetry_apply_iframe`. Reinspect the live frame and fields after advancing.
- Finish and verify the draft when same-tab input recovers. If a supported retry still fails, save the accessible fields and defer with the observed step, the exact remaining control, and the last error. Revisit the original tab once after the other accessible jobs if the connection has recovered.

## Connect with the Browser Use Path 2 CLI

Use the [Path 2 CLI](https://github.com/browser-use/browser-use#path-2-cli) with the already-running local Chrome profile that holds the supplied applications. Enable local remote debugging at `chrome://inspect/#remote-debugging` and use the [setup guide](setup.html) to load the Browser Use tab inventory extension in that profile. The inventory extension supplies Chrome group names, tab-strip order, and a direct mapping between Chrome tab IDs and the CLI's DevTools target IDs. It reads metadata only.

Run `browser-use --doctor` for setup or connection errors. If the CLI is missing and `uv` is available, use `uvx --python 3.12 --from browser-use==1.0.8 browser-use` in place of `browser-use`. Use the default local daemon throughout the batch so the CLI attaches to existing tabs. Keep Chrome open and handle any remote-debugging prompt through Chrome.

```sh
BU_NAME=default BH_TAB_MARKER=0 browser-use < "<skill-directory>/scripts/browser_use_cli_tabs.py"
```

Replace `<skill-directory>` with the actual skill directory. Match the `group` field to `jobs` case-insensitively and work by `windowId` and `index`. Use the numeric `tabId` for the draft guard and AutoApply PDF helper. Use the `targetId` to attach and interact through the CLI. A tab with no available target ID stays open for recovery.

```sh
BU_NAME=default BH_TAB_MARKER=0 browser-use <<'PY'
switch_tab("OBSERVED_TARGET_ID", activate=False)
print(page_info())
PY
```

Attach to the verified target at the start of each call. Use `cdp("Accessibility.getFullAXTree")` for accessible controls, `click_at_xy`, `fill_input`, and `press_key` for input, and `capture_screenshot("/absolute/path/to/screenshot.png")` for visual checks. Use the [CLI page workflow](https://github.com/browser-use/browser-use/blob/main/skills/browser-use/SKILL.md#page-workflow) for supported commands. Limit those commands to the existing job tab and its frames.

For recovery, rerun the tab inventory and match the original numeric tab ID, group, and application before reattaching to its current target ID. Only use an absent ID in `openTabIds` as evidence of closure after confirming the inventory is healthy and from the original Chrome profile. Keep the original employer page open throughout recovery.
