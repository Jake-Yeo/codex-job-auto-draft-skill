/* Local integration of the pinned JobWizard exports. No vendor service calls. */
(() => {
  const runtime = globalThis.AutoApplyJobWizard;
  if (!runtime) throw Error('JobWizard components were not loaded');
  if (globalThis.AutoApplyWidgets?.runtime === runtime && globalThis.AutoApplyWidgets?.revision === 8) return;
  const m = runtime.modules;
  const native = m['nativeSelectCommit.js'];
  const choice = m['choiceController.js'];
  const aria = m['genericAriaChoice.js'];
  const dynamic = m['typeaheadFill.js'];
  const workday = m['platforms/workday.js'];
  const prompt = m['workdayPromptAdapter.js'];
  const effects = m['formEffectSettlement.js'];
  const uploads = m['resumeLifecycle.js'];
  const text = e => (e?.innerText || e?.textContent || '').replace(/\s+/g,' ').trim();
  const normalize = s => String(s ?? '').normalize('NFKC').replace(/\s+/g,' ').trim().toLowerCase();
  const matching = (values, targets) => values.length === 1 && targets.some(t=>normalize(t)===normalize(values[0]));
  const visible = e => !!e?.isConnected && !e.closest('[hidden],[aria-hidden=true],[inert]') &&
    !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';

  function describe(el) {
    if(el.matches?.('input[role="spinbutton"][data-automation-id^="dateSection"]')) {
      const date=workday.describeWorkdayDateParts(el);
      const part=date&&Object.keys(date.parts).find(p=>date.parts[p]===el);
      if(part)return {kind:'workday-date-part',date,part,required:el.getAttribute('aria-required')==='true'};
    }
    if (prompt?.eligible(el) && prompt.read(el).known) return {kind:'workday-prompt',required:el.getAttribute('aria-required')==='true'};
    if (el.matches?.('select[multiple]')) return {kind:'native-multi',required:el.required};
    if (native.supports(el)) return {kind:'native-select',required:el.required};
    if (el.matches?.('button[aria-haspopup=listbox]')) {
      const value = workday.readWorkdayButtonSelect(el);
      const owner = globalThis.JobWizardChoiceOwnership.resolveButtonChoiceField(el);
      if (value?.known && owner) return {kind:'workday-button',title:text(owner.promptElement),
        required:el.getAttribute('aria-required')==='true' || !!owner.controlOwner.querySelector('[aria-required=true],[required]')};
    }
    const found = aria.describe(el);
    return found ? {...found,kind:found.mode==='tokens'?'aria-multi':'aria-choice'} : null;
  }
  function read(el, descriptor=describe(el)) {
    if (!descriptor) return null;
    if(descriptor.kind==='workday-date-part') {
      const state=descriptor.date.readPart(el,descriptor.part);
      const error=text(descriptor.date.owner.closest('fieldset')?.querySelector('[data-automation-id="inputAlert"]'));
      return {known:state.outcome!=='unknown',committed:state.outcome==='committed'&&!error,values:state.outcome==='committed'&&!error?[String(state.value)]:[]};
    }
    if (descriptor.kind==='workday-prompt') {
      const state=prompt.read(el);
      return {known:state.known,committed:state.committed,values:state.values};
    }
    if (['native-select','native-multi'].includes(descriptor.kind)) {
      const values=[...el.selectedOptions].filter(o=>o.value).map(text);
      return {known:true,committed:!!values.length && el.validity.valid,values};
    }
    return descriptor.kind==='workday-button' ? workday.readWorkdayButtonSelect(el) : aria.read(el);
  }
  function effect(scope) {
    let revision=0;
    const observer=new MutationObserver(records=>{revision+=records.length;});
    observer.observe(scope,{subtree:true,childList:true,characterData:true,attributes:true,
      attributeFilter:['aria-busy','aria-invalid','aria-expanded','hidden','disabled','value','class']});
    return {
      async settle(isCurrent) {
        return effects.settle({known:true,initialRevision:0,dispatchGraceMs:180,quietMs:100,timeoutMs:3500,
          isCurrent,read:()=>({revision,busy:effects.busy(scope)})});
      },
      dispose(){observer.disconnect();}
    };
  }
  async function fill(el, value, aliases=[], items) {
    const descriptor=describe(el);
    if (!descriptor) throw Error('No tested JobWizard adapter for this widget; use the mouse repair loop');
    const targets=[...new Set([String(value),...aliases].filter(Boolean))];
    const href=location.href;
    const id=el.dataset.autoapplyField;
    const current=()=>el.isConnected && visible(el) && location.href===href && el.dataset.autoapplyField===id;
    const before=read(el,descriptor);
    if(descriptor.kind==='workday-date-part') {
      const number=Number(value);
      if(!Number.isInteger(number)||number<1||number>({month:12,day:31,year:9999}[descriptor.part]))return {ok:false,adapter:descriptor.kind,reason:'invalid_date_part'};
      // Use JobWizard's shipped focus/select/input/blur implementation. Merely
      // painting .value can leave Workday's containing date unsaved.
      if(!descriptor.date.writePart(el,String(number),descriptor.part))return {ok:false,adapter:descriptor.kind,reason:'date_part_write_failed'};
      el.blur();
      await new Promise(r=>setTimeout(r,120));
      const after=read(el,descriptor);
      return {ok:current()&&after?.committed&&Number(after.values[0])===number,adapter:descriptor.kind,reason:'date_part_commit_readback',readback:after?.values||[]};
    }
    if(descriptor.kind==='workday-prompt') return fillPrompt(el,items||[{value,aliases}],current);
    if(descriptor.kind==='aria-multi') {
      const failures=[],wanted=items||[{value,aliases}],preserved=before?.values||[];
      for(const item of wanted) {
        const targets=[String(item.value),...(item.aliases||[])];
        const has=()=>read(el,descriptor)?.values.some(v=>targets.some(t=>normalize(t)===normalize(v)));
        if(has())continue;
        const result=await aria.fill(el,String(item.value),{timeoutMs:3000,isCurrent:current,answerId:id,
          dynamicResolver:dynamic.runDynamicChoiceResolver,commitVerifier:dynamic.awaitDynamicChoiceTerminalCommit,
          typeaheadIntent:{equivalentTargets:item.aliases||[],exactOnly:true,isCurrent:current}});
        if(!result.success||!has())failures.push({value:item.value,reason:result.reason||'selection_readback_mismatch'});
        if(!current())break;
      }
      const after=read(el,descriptor);
      const retained=preserved.every(v=>after?.values.includes(v));
      return {ok:current()&&!failures.length&&retained,adapter:descriptor.kind,reason:retained?'multiselect_readback':'previous_selection_lost',failures,readback:after?.values||[]};
    }
    if(descriptor.kind==='native-multi') {
      const wanted=items||[{value,aliases}],options=[...el.options].filter(o=>!o.disabled&&o.value),matches=[];
      for(const item of wanted){const candidates=options.filter(o=>[String(item.value),...(item.aliases||[])].some(t=>normalize(t)===normalize(text(o))));if(candidates.length!==1)return {ok:false,adapter:descriptor.kind,reason:'exact_unique_option_unavailable'};matches.push(candidates[0]);}
      for(const option of matches)option.selected=true;
      el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
      const after=read(el,descriptor),ok=current()&&matches.every(o=>after.values.includes(text(o)));
      return {ok,adapter:descriptor.kind,reason:ok?'native_multiselect_committed':'selection_readback_mismatch',readback:after.values};
    }
    if(before?.committed && matching(before.values,targets))
      return {ok:true,adapter:descriptor.kind,reason:'already_committed',readback:before.values};
    const pending=effect(el.closest('form')||document.body);
    try {
      let result;
      if (descriptor.kind==='native-select') {
        const options=[...el.options].filter(o=>!o.disabled&&!o.parentElement?.disabled&&o.value);
        const matches=[...new Set(targets.map(t=>dynamic.pickConfidentNativeSelectOption(options,t,{threshold:1,runnerUpMargin:0})).filter(Boolean))];
        if (matches.length!==1) return {ok:false,adapter:descriptor.kind,reason:'exact_unique_option_unavailable'};
        result=await native.commit({resolveElement:()=>current()?el:null,expectedValue:matches[0].value,
          allowReplacement:true,isCurrent:current,settleMs:700});
      } else if (descriptor.kind==='workday-button') {
        // Use the shipped visible-options path. No Workday private-state/network hooks.
        const adapter=workday.createWorkdayButtonChoiceAdapter(el,{skipNativeProbe:true,preserveExisting:false,
          timeoutMs:3000,isCurrent:current});
        if(!adapter) return {ok:false,adapter:descriptor.kind,reason:'workday_owner_unavailable'};
        result=await choice.execute({adapter,targets,isCurrent:current});
      } else {
        result=await aria.fill(el,String(value),{timeoutMs:3000,isCurrent:current,
          answerId:id,dynamicResolver:dynamic.runDynamicChoiceResolver,
          commitVerifier:dynamic.awaitDynamicChoiceTerminalCommit,
          typeaheadIntent:{equivalentTargets:aliases,exactOnly:true,isCurrent:current}});
        result={...result,ok:result.success};
      }
      const settlement=await pending.settle(()=>location.href===href);
      const after=current()?read(el,descriptor):null;
      const accepted=result.ok && after?.committed && matching(after.values,targets);
      return {ok:!!accepted,adapter:descriptor.kind,
        reason:accepted?result.reason:result.ok?'selection_readback_mismatch':result.reason,
        readback:after?.values||[],settlement};
    } finally {pending.dispose();}
  }
  async function fillPrompt(el, items, current) {
    const failures=[],selected=[];
    const owner=el.closest('[data-automation-id="multiSelectContainer"]');
    const key=(type,key)=>el.dispatchEvent(new KeyboardEvent(type,{key,code:key,bubbles:true,cancelable:true,keyCode:key==='Enter'?13:27,which:key==='Enter'?13:27}));
    const close=()=>{
      if(!current())return;
      key('keydown','Escape');
      const popup=[...document.querySelectorAll('[data-automation-id="responsiveMonikerPrompt"][data-associated-widget]')].find(p=>p.getAttribute('data-associated-widget')===owner?.id&&visible(p));
      if(popup) {
        // Some Workday checkbox menus ignore Escape. A click on the owning
        // section's static heading dismisses that menu without changing answers.
        const outside=owner.closest('[role="group"]')?.querySelector('h2,h3,legend')||document.body;
        for(const type of ['mousedown','mouseup','click'])outside.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true}));
      }
    };
    const setQuery=value=>{
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,value);
      el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
    };
    const until=async fn=>{const end=Date.now()+2200;while(current()&&Date.now()<end){const result=fn();if(result)return result;await new Promise(r=>setTimeout(r,60));}return null;};
    for(const item of items) {
      if(!current()) {failures.push({value:item.value,reason:'owner_changed'});break;}
      const targets=[String(item.value),...(item.aliases||[])];
      const has=()=>prompt.read(el).values.some(v=>targets.some(t=>normalize(t)===normalize(v)));
      if(has()) {selected.push(item.value);continue;}
      let found;
      for(const query of [...new Set(targets)]) {
        if(!current())break;
        close();setQuery('');
        const icon=owner?.querySelector('[data-automation-id="promptIcon"],[data-automation-id="promptSearchButton"]');
        icon?.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
        el.focus();setQuery(query);key('keydown','Enter');key('keyup','Enter');
        found=await until(()=>{
          if(has())return {committed:true};
          // Type 1 radio leaves and type 0 checkbox leaves share owned menus.
          const options=prompt.options(el).filter(o=>o.enabled&&(
            o.kind==='leaf'||(o.activation?.matches('[data-automation-id="promptLeafNode"][data-uxi-multiselectlistitem-type="0"][data-uxi-multiselectlistitem-hassidecharm="false"]')&&o.activation.querySelector('input[type="checkbox"]'))
          ));
          // Prefer the supplied label, then its explicit equivalent labels.
          // Different equivalent spellings are not an ambiguous duplicate.
          for(const target of targets) {
            const matches=options.filter(o=>normalize(target)===normalize(o.label));
            if(matches.length)return matches.length===1?{option:matches[0]}:{ambiguous:true};
          }
          return null;
        });
        if(found)break;
      }
      if(found?.option&&!found.option.checked) {
        for(const type of ['mousedown','mouseup','click'])found.option.activation.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true}));
      }
      if(found&&!found.ambiguous&&await until(has))selected.push(item.value);
      else failures.push({value:item.value,reason:found?.ambiguous?'ambiguous_option':'exact_option_not_committed'});
      close();
    }
    close();
    if(current())setQuery('');
    return {ok:!failures.length,adapter:'workday-prompt',reason:failures.length?'unresolved_prompt_choices':'selected_chips_committed',selected,failures,readback:prompt.read(el).values};
  }
  async function upload(el, file, owner) {
    const href=location.href, name=file.name;
    const wrapper=owner||el.closest('[data-automation-id^="formField-"],.field,.form-group,[role="group"],fieldset')||el.closest('label')||el.parentElement;
    const current=()=>location.href===href && wrapper.isConnected;
    const lifecycle=uploads.create({capability:'attachment',answerIds:[el.dataset.autoapplyField],
      isCurrent:current,readReceipt:()=>{
        const content=text(wrapper);
        const pending=/uploading|processing|parsing/i.test(content);
        const failed=(el.isConnected&&el.getAttribute('aria-invalid')==='true')||/upload failed|invalid file|file too large|unsupported file/i.test(content);
        // FileList alone is selection, not evidence of employer acceptance.
        const accepted=content.includes(name)&&!pending&&!failed;
        return {uploadAccepted:accepted,pending,failed};
      }});
    const transfer=new DataTransfer();transfer.items.add(file);el.files=transfer.files;
    el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));
    lifecycle.markHandedOff();
    return {name,...await lifecycle.wait()};
  }
  globalThis.AutoApplyWidgets={version:runtime.version,runtime,revision:8,describe,read,fill,upload,
    isComponentPart:el=>aria.isComponentPart(el),busy:scope=>effects.busy(scope)};
})();
