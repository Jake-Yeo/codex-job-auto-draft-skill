/* AutoApply file-field matching, scoped to document attachment. */
globalThis.JobApplicationsAttachPDF = async function (request) {
  const visible = el => !!el?.isConnected && !el.closest('[hidden],[inert],[aria-hidden=true]') && !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  const text = el => (el?.innerText || el?.textContent || '').trim().replace(/\s+/g, ' ');
  const labelText = el => {
    if(!el) return '';
    const direct=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim();
    if(direct) return direct.replace(/\s+/g,' ');
    const clone=el.cloneNode(true);
    clone.querySelectorAll('input,select,textarea,button,[role=listbox],[role=status]').forEach(e=>e.remove());
    return text(clone);
  };
  const roots = [document];
  for (let i=0; i<roots.length; i++) for (const e of roots[i].querySelectorAll('*')) if (e.shadowRoot && !e.matches('.simplify-jobs-shadow-root,#simplify-panel-restore-shell')) roots.push(e.shadowRoot);
  const all = selector => roots.flatMap(r => [...r.querySelectorAll(selector)]);
  const label = e => {
    if(!e) return '';
    const linked = (e.getAttribute('aria-labelledby') || '').split(/\s+/).map(id => e.getRootNode().getElementById?.(id)).filter(Boolean);
    return labelText(e.labels?.[0]) || e.getAttribute('aria-label') || linked.map(labelText).join(' ') ||
      labelText(e.closest('label')) || e.getAttribute('placeholder') || e.name || e.id || '';
  };
  const groupSelector='[role=group],fieldset,section';
  const groupName = e => e?.getAttribute('aria-label') || (e?.getAttribute('aria-labelledby')||'').split(/\s+/).map(id=>text(e?.getRootNode().getElementById?.(id))).filter(Boolean).join(' ') || text(e?.querySelector(':scope > legend,:scope > h2,:scope > h3,:scope > h4'));
  const section = e => groupName(e.closest(groupSelector)) || '';
  const fileOwner=e=>e.closest('[data-automation-id^="formField-"],.field,.form-group,[role=group],fieldset')||e.closest('label')?.parentElement||e.parentElement;
  const inputs = all("input[type=file]");
  const fatalError = all("h1,h2,[role=heading]").filter(visible)
    .some(element => /^something went wrong$/i.test(text(element)));
  if(location.href!==request.expectedHref || fatalError) throw Error('Inspect the current application before uploading');
  const exact = value => String(value || '').trim().replace(/\s*\*$/, '').trim().replace(/\s+/g, ' ').toLowerCase();
  const matches = inputs.filter(e => e.type==='file' && !e.matches(':disabled,[aria-disabled=true]') &&
    visible(fileOwner(e)) &&
    [label(e),section(e)].some(name => exact(name)===exact(request.label)));
  if(matches.length!==1) throw Error('Expected one matching file input; inspect the field in Chrome');
  const input=matches[0], owner=fileOwner(input);
  const documents = [request, ...(request.additionalFiles || [])];
  const names = documents.map(file => file.name);
  if (documents.length > 1 && !input.multiple) {
    throw Error('The observed field accepts one file at a time');
  }

  const filenameRows = () => [...owner.querySelectorAll('[data-automation-id="file-upload-item-name"]')]
    .filter(visible).map(text);
  const staged = [...input.files];
  const displayed = filenameRows();
  const remaining = documents.filter(file =>
    !displayed.includes(file.name) && !staged.some(existing => existing.name === file.name));
  if (!remaining.length) {
    return {status:'check-in-chrome',detail:'The requested filenames are already present',files:names};
  }
  if(staged.length && !input.multiple) {
    throw Error('A different file is already selected; inspect it before replacing');
  }
  // A site can retain an attachment in its UI after clearing its file input.
  const existing=[...owner.querySelectorAll('button,[role=button]')].some(button=>
    visible(button) && !button.matches(':disabled,[aria-disabled=true]') &&
    /^(?:remove|delete|replace)\s+(?:the\s+)?(?:attached\s+)?(?:file|attachment|résumé|resume|cover letter)\b/i.test(button.getAttribute('aria-label')||text(button)));
  if(existing && !input.multiple) return {status:'check-in-chrome',detail:'The form already shows attachment controls'};
  if(input.accept && !input.accept.split(',').some(type=>
    ['.pdf','application/pdf','application/*','*/*'].includes(type.trim().toLowerCase()))) {
    throw Error('The observed field does not accept PDFs');
  }
  const transfer = new DataTransfer();
  for (const file of staged) {
    if (!displayed.includes(file.name)) transfer.items.add(file);
  }
  for (const file of remaining) {
    const bytes = Uint8Array.from(atob(file.data), char => char.charCodeAt(0));
    transfer.items.add(new File([bytes], file.name, {type: "application/pdf"}));
  }
  input.files = transfer.files;
  input.dispatchEvent(new Event("change", {bubbles: true}));

  // A FileList confirms selection. Look for evidence from the form itself.
  const deadline = Date.now() + 6000;
  while (Date.now() < deadline && location.href === request.expectedHref && owner.isConnected) {
    const receipt = text(owner);
    if (input.getAttribute("aria-invalid") === "true" ||
        /upload failed|invalid file|file too large|unsupported file/i.test(receipt)) {
      return {status: "blocked", detail: "The employer form rejected the upload"};
    }
    if (names.every(name => receipt.includes(name)) && !/uploading|processing|parsing/i.test(receipt)) {
      return {status: "accepted", detail: "The employer form shows the filenames", files:names};
    }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  return {status: "check-in-chrome", detail: "Check the attachments on the original form", files:names};
};
