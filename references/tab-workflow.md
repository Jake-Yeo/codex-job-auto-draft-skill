# Existing jobs tabs

The user supplies the application tabs in a Chrome group named **jobs**. Discover actual group, window and tab IDs; match the name case-insensitively and work left to right. Keep every tab in its existing group and window. There is no Working, Ready, Pending help, Saved drafts or AutoApply group workflow and no database synchronization.

Work on one existing jobs tab at a time. Use the supported browser inventory to find its exact tab and window. Use the draft guard to resume after interruptions. Record unanswered mandatory confirmations with `await-confirmation` and other unresolved tab-specific blockers with `defer` so the next tab can proceed. Do not move or regroup tabs. Re-query live tabs if a tab disappears. When healthy Chrome inventory confirms a tab closed, record it as closed. Report it as submitted only when the applicant confirms submission. Preserve the marker during a connection problem or when the tab is still open outside the group.

Recovery must preserve the employer draft. Do not reload, navigate to its current URL, restart Apply, clear cookies or create a replacement tab. Inspect the current form and fix the affected control. An interrupted command may already have changed the page: inspect its result and current values before deciding whether anything remains to do.

A login title, URL or stale gate flag does not establish a current account blocker. Inspect the exact form, especially after the applicant says he signed in. Fill accessible non-credential application fields while leaving credentials untouched; hand off only the actual remaining authentication action.

Workday can show a generic `VPS|…` save error while displaying the account email and populated form. If no field is identified as invalid, preserve the answers and check whether the session needs renewal. After the applicant signs in, resume the same draft and check which fields and attachments persisted before re-entering anything. If navigating Back opens a **Discard Application** dialog, cancel it.

Keep the user's work window and global keyboard/mouse alone. Use browser-scoped controls on the explicit tab. Do not create or activate windows to fill the group. Preserve live finished forms as deliverables and unfinished/sign-in tabs as handoffs using the supported browser lifecycle methods before ending.

Chrome's browser-control tool has reported that an extension panel is open when the applicant says none is open. Inspect the current tab and use the browser tool's documented troubleshooting. If the tab connection is stale, rebind the same existing tab without reloading it and continue from the fields actually present.

If reattaching repeatedly returns `Debugger unattached`, verify that the original tab is still open and defer it with `defer --reason browser`. Continue accessible jobs. When the browser can claim the tab again, reclaim the original from Chrome's user-tab list and inspect its current state before continuing.

After a detached session, missed click or timeout, inspect the form for any result from the interrupted action. Recover control of the same tab and use the documented repair. Fill and save all accessible sections before preserving an unresolved draft. If a file is missing, try the applicable [attachment procedure](application-materials.md#resume-and-required-uploads), finish other fields, and verify any files already accepted. Defer only the remaining blocker and go on to the next jobs tab. Return to the deferred tab for an available retry after the first pass.

## Recover an embedded form before deferring

- After a transient input or connection error, check the original tab and rebind it if the handle is stale. Use the step and saved values the form shows now. The recovery marker is a checkpoint, and a wizard can return to an earlier step while retaining some answers. Confirm whether the résumé is present before retrying an attachment.
- If a readable form loses field focus during entry, inspect the current snapshot for the embedded application frame. Use a supported browser locator scoped to the observed frame and field label, then verify the committed value. Talemetry can expose its application in `iframe#talemetry_apply_iframe`. Reinspect the live frame and fields after advancing.
- Finish and verify the draft when same-tab input recovers. If a supported retry still fails, save the accessible fields and defer with the observed step, the exact remaining control, and the last error. Revisit the original tab once after the other accessible jobs if the connection has recovered.
