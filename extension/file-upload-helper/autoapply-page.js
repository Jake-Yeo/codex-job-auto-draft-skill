/* Runs in an isolated extension world. Values are replaced, never appended. */
globalThis.AutoApplyPage = async function(request = {}) {
  if(request.op==='attach-document' && location.href!==request.expectedHref) {
    throw Error('The application frame changed before the upload');
  }
  const urlKey=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(location.href)))].map(b=>b.toString(16).padStart(2,'0')).join('');
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
  const widgets = globalThis.AutoApplyWidgets;
  if(!widgets) throw Error('The JobWizard runtime is missing');
  const roots = [document];
  for (let i=0; i<roots.length; i++) for (const e of roots[i].querySelectorAll('*')) if (e.shadowRoot && !e.matches('.simplify-jobs-shadow-root,#simplify-panel-restore-shell')) roots.push(e.shadowRoot);
  const all = selector => roots.flatMap(r => [...r.querySelectorAll(selector)]);
  const byId = id => all('[data-autoapply-field]').find(e => e.dataset.autoapplyField === id);
  const label = e => {
    if(!e) return '';
    const linked = (e.getAttribute('aria-labelledby') || '').split(/\s+/).map(id => e.getRootNode().getElementById?.(id)).filter(Boolean);
    return labelText(e.labels?.[0]) || e.getAttribute('aria-label') || linked.map(labelText).join(' ') ||
      labelText(e.closest('label')) || e.getAttribute('placeholder') || e.name || e.id || '';
  };
  const groupSelector='[role=group],fieldset,section';
  const groupName = e => e?.getAttribute('aria-label') || (e?.getAttribute('aria-labelledby')||'').split(/\s+/).map(id=>text(e?.getRootNode().getElementById?.(id))).filter(Boolean).join(' ') || text(e?.querySelector(':scope > legend,:scope > h2,:scope > h3,:scope > h4'));
  const section = e => groupName(e.closest(groupSelector)) || '';
  const norm = v=>String(v||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const collectionKind = name=>({'work experience':'experience','employment':'experience','employment history':'experience','work history':'experience','education':'education','education history':'education','websites':'websites','professional links':'websites'})[norm(name)];
  const recordIdentity = group=>{
    const match=/^(Work Experience|Employment|Employment History|Work History|Education|Education History|Websites|Professional Links)\s*#?\s*(\d+)$/i.exec(groupName(group));
    return match?{kind:collectionKind(match[1]),index:Number(match[2])-1}:null;
  };
  const record = e => {
    let group=e.closest(groupSelector),identity;
    while(group && !(identity=recordIdentity(group)))group=group.parentElement?.closest(groupSelector);
    if(!identity)return null;
    const {kind,index}=identity;
    const raw=(e.id||'').split('--').pop();
    const keys={jobTitle:'title',companyName:'company',location:'location',currentlyWorkHere:'current',roleDescription:'description',schoolName:'school',degree:'degree',fieldOfStudy:'field_of_study',gradeAverage:'gpa',url:'url'};
    const labels={'job title':'title','position':'title','title':'title','company':'company','company name':'company','employer':'company','location':'location','i currently work here':'current','current position':'current','role description':'description','description':'description','responsibilities':'description','school or university':'school','school':'school','institution':'school','university':'school','degree':'degree','field of study':'field_of_study','major':'field_of_study','gpa':'gpa','overall result gpa':'gpa','start date':'start_date','end date':'end_date','graduation date':'end_date','start month':'start_month','end month':'end_month','start year':'start_year','end year':'end_year','url':'url'};
    let key=keys[raw]||labels[norm(label(e))];
    const date=/^(startDate|endDate|firstYearAttended|lastYearAttended)-dateSection(Month|Year)-input$/.exec(raw);
    if(date)key=(/^(startDate|firstYearAttended)$/.test(date[1])?'start':'end')+'_'+date[2].toLowerCase();
    if(kind==='websites' && /url/i.test(label(e)))key='url';
    const company=[...group.querySelectorAll('input')].find(x=>/^(company|company name|employer)$/.test(norm(label(x))));
    return key?{kind,index,key,company:company?.value||''}:null;
  };
  const collectionRoots=()=>all(groupSelector).filter(e=>collectionKind(groupName(e))&&visible(e));
  const recordCount=e=>[...e.querySelectorAll(groupSelector)].filter(g=>recordIdentity(g)?.kind===collectionKind(groupName(e))).length;
  const fileOwner=e=>e.closest('[data-automation-id^="formField-"],.field,.form-group,[role=group],fieldset')||e.closest('label')?.parentElement||e.parentElement;
  const body = document.body?.innerText || '';
  const inputs = all('input,select,textarea,[role=combobox],[role=checkbox],[role=switch],[role=radio],[role=radiogroup],button[aria-haspopup=listbox],[contenteditable=true]');
  const live = inputs.filter(e => visible(e) && !e.matches(':disabled,[aria-disabled=true]') && (!e.readOnly || widgets.describe(e)) &&
    (!['hidden','submit','button','reset'].includes(e.type) || widgets.describe(e) || ['checkbox','switch'].includes(e.getAttribute('role'))) && !widgets.isComponentPart(e) &&
    !e.closest('[role=option],[role=treeitem]') &&
    !(e.closest('[role=radiogroup]') && e.closest('[role=radiogroup]')!==e && widgets.describe(e.closest('[role=radiogroup]'))));
  const password = live.some(e => e.type === 'password');
  const authentication = e => e.type === 'password' || e.autocomplete === 'one-time-code' ||
    (password && (e.type === 'email' || /^(?:email|email address|username|user name)$/i.test(label(e))));
  const authForm = /(?:sign[ -]?in|log[ -]?in|register|create (?:an? |your )?account|verify (?:your )?(?:email|identity)|verification code)/i;
  const titles = all('h1,h2,[role=heading],form legend').filter(visible).map(text).join(' ');
  const fatalError = all('h1,h2,[role=heading]').filter(visible).find(e=>/^something went wrong$/i.test(text(e)));
  // iCIMS can call its account lookup "Let's get started" and include a
  // privacy checkbox. It is still authentication, not an application email.
  const icimsAccountLookup = /(^|\.)icims\.com$/i.test(location.hostname) &&
    /\/login\/?$/i.test(location.pathname) && authForm.test(document.title) &&
    live.every(e=>e.type==='email'||e.type==='checkbox'||e.getAttribute('role')==='checkbox');
  const emailOnlyLogin = live.length <= 3 && live.some(e => e.type==='email') &&
    (authForm.test(titles) || icimsAccountLookup);
  const authenticationPending = password || emailOnlyLogin || /verification code|check your (?:email|inbox)|session (?:has )?expired/i.test(titles) ||
    (authForm.test(titles) && !live.length && !/application review|review application/i.test(titles));
  // Some ATS registration pages combine credentials with a full application.
  // Only the application fields are usable; account completion stays with Jake.
  const applicationProfile = live.some(e=>!authentication(e) && /address|mobile phone|postal code/i.test(label(e))) &&
    live.some(e=>!authentication(e) && /degree|university|school name|skills|resume/i.test(label(e)));
  const gate = authenticationPending && !applicationProfile;
  const kind = e => {
    const name = text(e) || e.getAttribute('aria-label') || e.value || '';
    if (/^(submit(?: application)?|send application|finish(?: application)?|apply(?: now)?)$/i.test(name)) return 'submit';
    if (/^(?:save (?:and|&) )?(?:next|continue|review)(?: application| and review| to review| step)?(?:\s*[→›>])?$/i.test(name)) return authenticationPending ? 'account' : 'next';
    if (/^(?:add(?: another)? (?:education|experience|work experience|school|employment|skill|link)|save|update|done)$/i.test(name)) return 'edit';
    if (authForm.test(name)) return 'account';
    return 'other';
  };
  const controls = () => all('button,input[type=button],input[type=submit],a[role=button]').filter(visible).map((e,i) => {
    if (!e.dataset.autoapplyButton) e.dataset.autoapplyButton = `b${i}-${crypto.randomUUID().slice(0,8)}`;
    return {id:e.dataset.autoapplyButton, label:text(e)||e.getAttribute('aria-label')||e.value||'', kind:kind(e), disabled:!!e.disabled};
  });
  const scan = () => {
    const radioSeen=new Set();
    const fields = live.filter(e => !authentication(e)).map((e,i) => {
      if(e.type==='radio') {
        const group=e.name || e.closest('fieldset');
        if(radioSeen.has(group)) return null;
        radioSeen.add(group);
      }
      if (!e.dataset.autoapplyField) e.dataset.autoapplyField = `f${i}-${crypto.randomUUID().slice(0,8)}`;
      const widget=widgets.describe(e);
      let value = e.isContentEditable ? text(e) : (e.value ?? e.getAttribute('aria-valuetext') ?? text(e));
      const role=e.getAttribute('role');
      const type = widget?.kind==='workday-date-part'?'date-part':widget && widget.kind!=='native-select' ? (role==='radiogroup'?'radiogroup':'combobox') : ['checkbox','switch'].includes(role)?'checkbox':e.type || role || e.tagName.toLowerCase();
      if (type==='checkbox') value = (e.checked || e.getAttribute('aria-checked') === 'true') ? 'Yes' : 'No';
      if (type==='radio') value = (e.checked || e.getAttribute('aria-checked') === 'true') ? (label(e)||'Yes') : '';
      if (e.tagName === 'SELECT') value = [...e.selectedOptions].filter(o=>o.value).map(o=>text(o)).join(', ');
      if (type==='file') value = [...(e.files||[])].map(f=>f.name).join(', ');
      const radios=type==='radio'?live.filter(r=>r.type==='radio'&&(e.name?r.name===e.name:r.closest('fieldset')===e.closest('fieldset'))):[];
      if(radios.length) value=label(radios.find(r=>r.checked))||'';
      const readback=widget?widgets.read(e,widget):null;
      if(readback) value=readback.committed?readback.values.join(', '):'';
      const prompt=e.labels?.[0] || document.getElementById((e.getAttribute('aria-labelledby')||'').split(/\s+/)[0]);
      const owner=e.closest('[data-automation-id^="formField-"],.field,.form-group')||e.parentElement;
      const requiredness=globalThis.AutoApplyJobWizard.modules['requirednessResolver.js']?.resolveRequiredness({region:{controls:[e],controlOwner:owner,questionContainer:owner,promptElement:prompt,regionConfidence:prompt&&owner.contains(prompt)?1:0}});
      return {id:e.dataset.autoapplyField, label:(radios.length?(section(e)||e.name):label(e)||widget?.title||'').replace(/\s*\*$/, ''), section:section(e), type,
        value, record:record(e), selected_values:readback?.committed?readback.values:undefined, adapter:widget?.kind||'native-input', required:!!e.required || !!widget?.required || e.getAttribute('aria-required')==='true' || !!requiredness?.required || !!(widget?.kind==='workday-button'&&/\brequired$/i.test(e.getAttribute('aria-label')||'')), autocomplete:e.autocomplete||'',
        placeholder:e.getAttribute('placeholder')||'',max_length:e.maxLength>0?e.maxLength:undefined,min:e.min||undefined,max:e.max||undefined,accept:e.accept||undefined,
        options:radios.length?radios.map(label):e.tagName==='SELECT'?[...e.options].filter(o=>o.value && !o.disabled).map(text):widget?.choices||[],
        attachment_text:type==='file'?text(fileOwner(e)).slice(0,1800):undefined};
    }).filter(Boolean);
    for(const e of collectionRoots()) {
      if(!e.dataset.autoapplyField)e.dataset.autoapplyField='collection-'+crypto.randomUUID().slice(0,8);
      e.dataset.autoapplyCollection=groupName(e);
      fields.push({id:e.dataset.autoapplyField,label:groupName(e),collection_kind:collectionKind(groupName(e)),type:'collection',value:String(recordCount(e)),required:false,section:'',adapter:'record-collection'});
    }
    // Include hidden file inputs if their visible wrapper offers upload controls.
    for (const e of inputs.filter(e=>e.type==='file' && !e.disabled && !live.includes(e) && visible(fileOwner(e)))) {
      if (!e.dataset.autoapplyField) e.dataset.autoapplyField = `upload-${crypto.randomUUID().slice(0,8)}`;
      fields.push({id:e.dataset.autoapplyField,label:label(e)||text(e.parentElement).slice(0,150),section:section(e),type:'file',
        required:!!e.required,accept:e.accept||'',value:[...(e.files||[])].map(f=>f.name).join(', '),attachment_text:text(fileOwner(e)).slice(0,1800)});
    }
    const errors = all('[aria-invalid=true],[role=alert],.field-error,.error-message').filter(visible)
      .filter(e=>!e.matches('.alert-info,.alert-success,[data-alert-type="info"]'))
      .map(e=>text(e)||e.validationMessage||(e.getAttribute('aria-invalid')==='true'?`${label(e)} is invalid`:'')).filter(Boolean);
    if(fatalError)errors.push(text(fatalError.parentElement).slice(0,700));
    for(const e of live) if(e.value && e.validity && !e.validity.valid && !e.validity.valueMissing) errors.push(`${label(e)}: ${e.validationMessage}`);
    return {adapter_revision:widgets.revision,url:location.origin+location.pathname,url_key:urlKey,title:document.title,gate,authentication_pending:!!authenticationPending,fatal_error:!!fatalError,fields,buttons:controls(),errors:[...new Set(errors)],
      busy:all('[aria-busy=true],[role=progressbar]').some(visible)||fields.some(f=>f.type==='file'&&/uploading|processing|parsing/i.test(f.attachment_text||'')),
      human_check:/i am (?:a )?human|i.m not a robot/i.test(body),text:body.slice(0,24000)};
  };
  if (request.op==='scan' || !request.op) return scan();
  if (gate) throw Error('Account screen: leave sign-in, sign-up and verification to Jake.');
  if (request.op==='attach-document') {
    if(location.href!==request.expectedHref || fatalError) throw Error('Inspect the current application before uploading');
    const exact = value => String(value || '').trim().replace(/\s*\*$/, '').trim().replace(/\s+/g, ' ').toLowerCase();
    const matches = inputs.filter(e => e.type==='file' && !e.matches(':disabled,[aria-disabled=true]') &&
      visible(fileOwner(e)) &&
      [label(e),section(e)].some(name => exact(name)===exact(request.label)));
    if(matches.length!==1) throw Error('Expected one matching file input; inspect the field in Chrome');
    const input=matches[0], owner=fileOwner(input);
    if(input.files?.length) {
      if(input.files.length===1 && input.files[0].name===request.name) {
        return {status:'check-in-chrome',detail:'The same filename is already selected'};
      }
      throw Error('A different file is already selected; inspect it before replacing');
    }
    // A site can retain an attachment in its UI after clearing its file input.
    const existing=[...owner.querySelectorAll('button,[role=button]')].some(button=>
      visible(button) && !button.matches(':disabled,[aria-disabled=true]') &&
      /^(?:remove|delete|replace)\s+(?:the\s+)?(?:attached\s+)?(?:file|attachment|résumé|resume|cover letter)\b/i.test(button.getAttribute('aria-label')||text(button)));
    if(existing) return {status:'check-in-chrome',detail:'The form already shows attachment controls'};
    if(input.accept && !input.accept.split(',').some(type=>
      ['.pdf','application/pdf','application/*','*/*'].includes(type.trim().toLowerCase()))) {
      throw Error('The observed field does not accept PDFs');
    }
    const bytes=Uint8Array.from(atob(request.data),c=>c.charCodeAt(0));
    const receipt=await widgets.upload(input,new File([bytes],request.name,{type:request.mime}),owner);
    return {status:receipt.failed?'blocked':receipt.confirmed&&receipt.uploadAccepted?'accepted':'check-in-chrome',
      detail:receipt.reason};
  }
  const set = async (e,value,aliases=[],items) => {
    if(fatalError)throw Error('The employer page reports an error; preserve this tab and inspect it');
    if(e.dataset.autoapplyCollection) {
      const name=e.dataset.autoapplyCollection,target=Number(value);
      if(!Number.isInteger(target)||target<0||target>20)throw Error('Invalid record count');
      for(let i=0;i<20;i++) {
        const root=collectionRoots().find(r=>groupName(r)===name);
        if(!root)throw Error('Record section changed');
        const before=recordCount(root);
        if(before>=target)return {ok:true,adapter:'record-collection',records:before};
        const add=[...root.querySelectorAll('button')].filter(b=>visible(b)&&!b.disabled&&/^Add(?: Another)?(?: Work Experience| Experience| Employment| Education| School| Website| Link)?$/i.test(text(b))&&b.closest(groupSelector)===root);
        if(add.length!==1)throw Error('Unique record Add button unavailable');
        add[0].click();
        const deadline=Date.now()+3500;
        while(Date.now()<deadline && recordCount(collectionRoots().find(r=>groupName(r)===name)||root)<=before)await new Promise(r=>setTimeout(r,60));
        if(recordCount(collectionRoots().find(r=>groupName(r)===name)||root)<=before)throw Error('Added record did not appear; inspect before retrying');
      }
      throw Error('Record limit reached');
    }
    const role=e.getAttribute('role');
    const type = ['checkbox','switch'].includes(role)?'checkbox':e.type || role;
    if (authentication(e)) throw Error('Authentication fields cannot be filled.');
    if (type==='email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) throw Error('Invalid email mapping');
    if(widgets.describe(e)) {
      const receipt=await widgets.fill(e,value,aliases,items);
      if(!receipt.ok) throw Object.assign(Error(`JobWizard ${receipt.adapter}: ${receipt.reason}`),{receipt});
      return receipt;
    }
    if(type==='radio') {
      const radios=live.filter(r=>r.type==='radio'&&(e.name?r.name===e.name:r.closest('fieldset')===e.closest('fieldset')));
      const option=radios.find(r=>label(r)===value);
      if(!option) throw Error('Exact radio choice is not available');
      if(!option.checked) option.click();
    } else if (type==='checkbox') {
      if(value!==true && value!==false && !/^(yes|no|true|false|checked|unchecked)$/i.test(String(value))) throw Error('Checkbox requires an explicit boolean answer');
      const checked = value === true || /^(yes|true|checked)$/i.test(String(value)) || value===label(e);
      if ((e.checked ?? (e.getAttribute('aria-checked')==='true')) !== checked) e.click();
    } else if (e.isContentEditable) {
      e.focus();
      const before=new InputEvent('beforeinput',{bubbles:true,cancelable:true,inputType:'insertText',data:String(value)});
      if(!e.dispatchEvent(before))throw Error('Rich text editor requires its specific input adapter');
      e.textContent=String(value);
    }
    else {
      if (e.getAttribute('role')==='combobox') throw Error('Use a tested widget adapter for this combobox');
      // Some editors persist on focusout, not the input event alone. Focus the
      // actual control so blur below commits its value through the form UI.
      e.focus();
      const proto = e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto,'value').set.call(e,String(value));
    }
    e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:String(value)}));
    e.dispatchEvent(new Event('change',{bubbles:true}));
    e.dispatchEvent(new FocusEvent('blur',{bubbles:true}));
    e.blur();
    await new Promise(resolve=>requestAnimationFrame(resolve));
    if(!e.isConnected)throw Error('Field replaced after input; rescan before claiming completion');
    const observed=type==='checkbox'?(e.checked??e.getAttribute('aria-checked')==='true')?'Yes':'No':type==='radio'?label(live.find(r=>r.type==='radio'&&r.name===e.name&&r.checked)):e.isContentEditable?text(e):e.value;
    const expected=typeof value==='boolean'?(value?'Yes':'No'):String(value);
    if(norm(observed)!==norm(expected))throw Error('Input readback mismatch; inspect the same field');
    if(e.validity&&!e.validity.valid)throw Error(e.validationMessage||'The employer rejected this value');
    return {ok:true,adapter:e.isContentEditable?'rich-text':'native-input',readback:[observed]};
  };
    if (request.op==='fill') {
    const changed=[], failures=[], receipts=[];
    for (const item of request.plan||[]) {
      const e=byId(item.field);
      try {
        if (!e || (!visible(e) && !(item.file && e.type==='file' && visible(fileOwner(e)))) || e.disabled) throw Error('Field changed; rescan');
        let receipt;
        if(item.file) {
          if(e.type!=='file')throw Error('Observed document control changed');
          const bytes=Uint8Array.from(atob(item.file.data),c=>c.charCodeAt(0));
          receipt=await widgets.upload(e,new File([bytes],item.file.name,{type:item.file.mime}));
          if(!receipt.confirmed||!receipt.uploadAccepted)throw Error('Upload not yet confirmed; inspect attachment before retrying');
        } else receipt=await set(e,item.value,item.aliases,item.items);
        changed.push(item.field); receipts.push({field:item.field,...receipt||{ok:true,adapter:'native-input'}});
      } catch(error) { failures.push({field:item.field,error:error.message,...(error.receipt?{receipt:error.receipt}:{})}); }
    }
    return {engine:widgets.version,changed,failures,receipts};
  }
  if (request.op==='upload') {
    const e=byId(request.field);
    if (!e || e.type!=='file') throw Error('The observed upload field is missing');
    const bytes=Uint8Array.from(atob(request.data),c=>c.charCodeAt(0));
    return widgets.upload(e,new File([bytes],request.name,{type:request.mime}));
  }
  if (request.op==='click') {
    const e=all('[data-autoapply-button]').find(e=>e.dataset.autoapplyButton===request.button);
    if (!e || !visible(e) || e.disabled) throw Error('The observed button changed');
    const allowed=request.mode==='advance'?['next']:['edit'];
    if (!allowed.includes(kind(e))) throw Error('Only observed non-final navigation or section-edit buttons may be clicked');
    e.click(); return {clicked:request.button};
  }
  throw Error('Unknown page operation');
};
