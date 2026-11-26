"""Workday controls for the current application in Browser Use Path 2."""

import re
import time
from pathlib import Path

from browser_use_cli_form import evaluate, replace_text, tap_key
from draft_guard import DEFAULT, draft_url, edit_active_draft


PAGE_CONTROLS = r"""() => {
  const visible = el => !!el?.getClientRects().length && !el.closest('[hidden], [aria-hidden=true]');
  const text = document.body?.innerText || "";
  const step = text.match(/^current step (\d+) of (\d+)\s*$/im);
  const next = document.querySelector('[data-automation-id="pageFooterNextButton"]');
  const busy = [...document.querySelectorAll('[aria-busy=true], [role=progressbar],'
                + '[data-automation-id="loading"]')].some(visible);
  const modal = [...document.querySelectorAll('[role=dialog], [role=alertdialog]')].find(visible);
  const discard = modal?.getAttribute('aria-labelledby') === 'discardHeading' &&
    modal.querySelector('[data-automation-id="continueButton"]');
  const canContinue = !!step && Number(step[1]) < Number(step[2]) && visible(next) &&
    /^(Save and Continue|Continue|Next)$/.test(next.innerText.trim());
  const questions = [...document.querySelectorAll(
    '[id*=Questionnaire--]:is(input,textarea,select,button[aria-haspopup=listbox])')]
    .filter(el => visible(el) && !el.matches(':disabled, [aria-disabled=true], [type=hidden]'));
  const required = questions.filter(el => el.required || el.getAttribute('aria-required') === 'true' ||
    (el.tagName === 'BUTTON' && /\bRequired\s*$/.test(el.getAttribute('aria-label') || '')));
  const missing = required.filter(el => {
    if (el.type === 'radio') return !questions.some(q => q.name === el.name && q.checked);
    if (el.type === 'checkbox') return !el.checked;
    return !el.value?.trim();
  });
  const invalid = [...document.querySelectorAll('[aria-invalid=true]')].filter(visible);
  const errors = [...document.querySelectorAll('[data-automation-id="errorMessage"],'
                  + '[data-automation-id="errorMessageContainer"], [data-automation-id="pageError"]')];
  for (const el of invalid) {
    const describedBy = el.getAttribute('aria-errormessage') || el.getAttribute('aria-describedby') || '';
    for (const id of describedBy.split(/\s+/)) {
      const description = document.getElementById(id);
      if (description && (id.startsWith('error') || description.getAttribute('role') === 'alert')) {
        errors.push(description);
      }
    }
  }
  return {
    next, discard, view: {
      url: location.href,
      step: step ? Number(step[1]) : null,
      ready: canContinue && !next.matches(':disabled, [aria-disabled=true]') && !busy && !modal,
      canContinue, busy, hidden: document.hidden,
      footerDisabled: visible(next) && next.matches(':disabled, [aria-disabled=true]'),
      dialog: discard ? 'discard' : modal ? 'other' : null,
      errors: [...new Set(errors.filter(visible).map(el => el.innerText.trim()).filter(Boolean))],
      invalid: invalid.map(el => el.id).filter(Boolean),
      missing: missing.map(el => el.id),
      questions: questions.map(el => [el.id, /^(radio|checkbox)$/.test(el.type) ? el.checked : el.value]),
      signIn: !step && [...document.querySelectorAll('input[type=password]')].some(visible),
    },
  };
}"""

SAVE_VIEW = f"() => ({PAGE_CONTROLS})().view"
CLICK_SAVE = f"""(step, url, expectedQuestions) => {{
  const read = {PAGE_CONTROLS};
  const allowed = v => v.url === url && v.step === step && v.ready &&
    !v.missing.length && !v.invalid.length && !v.errors.length &&
    JSON.stringify(v.questions) === JSON.stringify(expectedQuestions);
  let page = read();
  if (!allowed(page.view)) return false;
  page.next.focus({{preventScroll: true}});
  page = read();
  if (!allowed(page.view)) return false;
  page.next.click();
  return true;
}}"""
KEEP_DRAFT = f"""(step, url) => {{
  const {{discard, view}} = ({PAGE_CONTROLS})();
  if (!discard || view.step !== step || view.url !== url || discard.disabled) return false;
  discard.click();
  return true;
}}"""


def _background_frame(cdp, session_id):
    # Workday releases the Continue button in requestAnimationFrame. A scoped
    # Chrome capture runs a frame on a hidden tab without activating it.
    try:
        cdp("Page.captureScreenshot", session_id=session_id, format="png", fromSurface=True,
            clip={"x": 0, "y": 0, "width": 1, "height": 1, "scale": 1}, _response_timeout=1)
    except (OSError, RuntimeError):
        # Observe the real control even if Chrome could not capture a frame.
        pass


def _page_url(page):
    try:
        return draft_url(page["url"])
    except ValueError:
        return None


def save_and_continue(cdp, session_id, tab_id, url, step, *, wait_seconds=18, state_path=DEFAULT):
    """Save and observe this step. After a pending result, call again with the same step."""
    state_path = Path(state_path)
    expected_url = draft_url(url)
    start = time.monotonic()
    deadline = start + wait_seconds
    next_frame = start
    settled_at = start
    question_state = None
    kept_draft = False
    while True:
        page = evaluate(cdp, session_id, SAVE_VIEW)
        current_url = _page_url(page)
        now = time.monotonic()
        # A hidden tab can be waiting for a frame before or after validation.
        # Space captures out and only request them while the control needs one.
        if (current_url == expected_url and page["hidden"] and now >= next_frame and
                ((page["footerDisabled"] and not page["dialog"]) or
                 (page["dialog"] == "discard" and kept_draft))):
            _background_frame(cdp, session_id)
            next_frame = time.monotonic() + 0.4
            page = evaluate(cdp, session_id, SAVE_VIEW)
            current_url = _page_url(page)
        current_questions = (page["questions"], page["missing"])
        if current_questions != question_state:
            question_state = current_questions
            settled_at = time.monotonic() + (0.65 if page["questions"] else 0)

        reserved = None
        with edit_active_draft(state_path, tab_id, url) as active:
            previous_save = active.get("save")
            save = previous_save or {}
            saving_step = save.get("step", step)
            if saving_step != step:
                if current_url != expected_url or page["step"] is None or page["step"] <= saving_step:
                    raise ValueError(f"Finish observing Workday step {saving_step} before saving another.")
                active.pop("save", None)
                previous_save = None
                save = {}
            attempts = save.get("attempts", 0)
            if current_url != expected_url:
                status = "page_changed"
            elif page["step"] is not None and page["step"] > step:
                active.pop("save", None)
                status = "advanced"
            elif page["signIn"]:
                active.pop("save", None)
                status = "sign_in"
            elif page["step"] != step:
                status = "step_changed" if page["step"] is not None else "pending"
            elif page["dialog"]:
                status = "keep_draft" if page["dialog"] == "discard" and not kept_draft else "dialog"
            elif page["errors"] or page["invalid"]:
                active.pop("save", None)
                status = "needs_repair"
            elif time.monotonic() < settled_at:
                status = "pending" if attempts else "settling"
            elif page["missing"] and (page["ready"] or not attempts):
                active.pop("save", None)
                status = "needs_repair"
            elif page["ready"] and time.time() - save.get("last_attempt", 0) >= 2:
                if attempts < 2:
                    reserved = {"step": step, "attempts": attempts + 1, "last_attempt": time.time()}
                    active["save"] = reserved
                    status = "pending"
                else:
                    status = "same_step"
            else:
                # Before the first click, an unavailable control alone is not an in-flight save.
                status = "pending" if attempts or page["busy"] else "disabled"

        if reserved is not None:
            if not evaluate(cdp, session_id, CLICK_SAVE, step, page["url"], page["questions"]):
                with edit_active_draft(state_path, tab_id, url) as active:
                    if active.get("save") == reserved:
                        if previous_save is None:
                            active.pop("save")
                        else:
                            active["save"] = previous_save
                status = "control_changed"
            else:
                next_frame = time.monotonic()
        if status == "keep_draft":
            kept_draft = evaluate(cdp, session_id, KEEP_DRAFT, step, page["url"])
            if kept_draft:
                next_frame = time.monotonic()
                status = "dialog"

        observation_time = time.monotonic()
        waiting = (status in ("pending", "settling", "control_changed") or
                   (status == "dialog" and kept_draft) or
                   (status == "disabled" and observation_time < start + 1.2))
        if not waiting or observation_time >= deadline:
            return {"status": status, "step": page["step"], "ready": page["ready"],
                    "errors": page["errors"], "invalid": page["invalid"], "missing": page["missing"]}
        time.sleep(0.2)


def choose_options(cdp, session_id, choices):
    """Set exact visible options in a batch of observed Workday dropdowns."""
    for field_id, label in choices.items():
        if evaluate(cdp, session_id, """(id, label) => {
          const button = document.getElementById(id);
          if (!button?.matches('button[aria-haspopup=listbox]:enabled') ||
              !button.getClientRects().length || button.innerText.trim() === label) return false;
          if (button.getAttribute('aria-expanded') !== 'true') button.click();
          return true;
        }""", field_id, label):
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                chosen = evaluate(cdp, session_id, """(id, label) => {
                  const button = document.getElementById(id);
                  const list = document.getElementById(button?.getAttribute('aria-controls'));
                  const option = [...list?.querySelectorAll('[role=option]') || []]
                    .find(el => el.getClientRects().length && el.innerText.trim() === label);
                  if (option) option.click();
                  return !!option;
                }""", field_id, label)
                if chosen:
                    break
                time.sleep(0.1)
    # A later choice can re-render an earlier or dependent question.
    return evaluate(cdp, session_id, """ids => Object.fromEntries(ids.map(id =>
      [id, document.getElementById(id)?.innerText.trim() || null]))""", list(choices))


# Equivalent catalog labels for technologies commonly named differently by tenants.
SKILL_NAMES = (
    ("SQL", "Structured Query Language (SQL)", "Structured Query Language"),
    ("ETL", "Data ETL", "ETL (Extract, Transform, Load)", "Extract, Transform, Load (ETL)"),
    ("AWS", "Amazon Web Services (AWS)", "Amazon Web Services"),
    ("AWS Lambda", "Amazon Lambda", "Amazon Web Services Lambda", "Lambda (AWS)"),
    ("Amazon S3", "AWS S3", "Amazon Simple Storage Service (S3)", "Amazon S3 (Simple Storage Service)"),
    ("Amazon Cognito", "AWS Cognito", "Amazon Web Services Cognito"),
    ("AWS AppSync", "Amazon AppSync"),
    ("AWS CDK", "AWS Cloud Development Kit", "Cloud Development Kit (CDK)"),
    ("C", "C (Programming Language)"),
    ("C++", "C Plus Plus"),
    ("OpenID Connect (OIDC)", "OpenID Connect", "OIDC"),
    ("Single Sign-On (SSO)", "Single Sign-On", "Single Sign On", "SSO"),
    ("JSON Web Tokens (JWT)", "JSON Web Token", "JSON Web Tokens", "JWT"),
    ("PostgreSQL", "Postgres"),
    ("React.js", "React", "ReactJS"),
    ("Node.js", "NodeJS"),
    ("Next.js", "NextJS"),
    ("Express.js", "ExpressJS"),
    ("OpenAI API", "OpenAI APIs", "OpenAI"),
    ("REST APIs", "REST API", "RESTful APIs", "REST Web Services"),
    ("Artificial Intelligence (AI)", "Artificial Intelligence", "AI"),
    ("LLM Integration", "Large Language Model Integration"),
    ("Object-Oriented Programming", "Object-Oriented Programming (OOP)", "OOP"),
    ("CI/CD", "Continuous Integration and Continuous Delivery", "Continuous Integration/Continuous Delivery"),
    ("HLS Streaming", "HTTP Live Streaming (HLS)", "HTTP Live Streaming", "HLS"),
    ("Data Pipelines", "Data Pipeline"),
    ("Unit Testing", "Unit Tests"),
    ("End-to-End Testing", "End to End Testing", "E2E Testing"),
)


def skill_key(text):
    text = re.sub(r"\s*\((?:programming language|software|framework|version control system)\)$",
                  "", text.strip(), flags=re.IGNORECASE)
    return " ".join(text.casefold().replace("‐", "-").replace("‑", "-").split())


ALIASES = {skill_key(name): names for names in SKILL_NAMES for name in names}

SKILLS_CONTROL = """(id, action, labels) => {
  const input = document.getElementById(id);
  const container = input?.closest('[data-automation-id="multiSelectContainer"]');
  if (!container) return null;
  const visible = el => !!el?.getClientRects().length;
  const name = el => el.innerText.trim();
  const chips = [...container.querySelectorAll('[data-automation-id="selectedItem"]')];
  const linked = document.getElementById(input.getAttribute('aria-controls'));
  const prompt = visible(linked) ? linked :
    [...document.querySelectorAll('[data-automation-id="responsiveMonikerPrompt"]')]
      .find(el => visible(el) && container.id &&
            el.getAttribute('data-associated-widget') === container.id);
  const options = [...prompt?.querySelectorAll('[data-automation-id="promptOption"]') || []]
    .filter(el => visible(el) && !el.closest('[data-automation-id="selectedItem"]') &&
                  !el.closest('[aria-disabled=true]'));
  if (action === 'choose') {
    const matching = options.filter(el => name(el) === labels[0]);
    if (matching.length !== 1) return false;
    matching[0].click();
    return true;
  }
  if (action === 'remove') {
    const added = chips.filter(el => labels.includes(name(el)));
    for (const chip of added) chip.querySelector('[data-automation-id="DELETE_charm"]')?.click();
  }
  return {chips: chips.map(name), options: options.map(name),
          disabled: input.matches(':disabled, [aria-disabled=true]')};
}"""


def add_skills(cdp, session_id, skills, *, field_id="skills--skills", search_seconds=2.8):
    """Try every supplied skill and keep only matching, committed catalog choices."""
    def control(action="read", labels=()):
        result = evaluate(cdp, session_id, SKILLS_CONTROL, field_id, action, labels)
        if result is None:
            raise ValueError("Identify this application's Workday skills input first.")
        return result

    report = {"selected": {}, "unavailable": [], "needs_attention": []}
    seen = set()
    for skill in skills:
        names = ALIASES.get(skill_key(skill), (skill,))
        keys = {skill_key(name) for name in names}
        if keys & seen:
            continue
        seen.update(keys)
        field = control()
        existing = next((chip for chip in field["chips"] if skill_key(chip) in keys), None)
        if existing:
            report["selected"][skill] = existing
            continue
        if field["disabled"]:
            report["needs_attention"].append(skill)
            continue
        original = set(field["chips"])
        settled = None
        needs_attention = False
        alternate = next((name for name in names if name.casefold() != skill.casefold()), skill)
        queries = tuple(dict.fromkeys((skill, alternate)))
        for query in queries:
            if not replace_text(cdp, session_id, field_id, query, commit=False):
                needs_attention = True
                break
            tap_key(cdp, session_id, "Enter", 13)
            deadline = time.monotonic() + search_seconds
            clicked_option = False
            while time.monotonic() < deadline:
                field = control()
                added = [chip for chip in field["chips"] if chip not in original]
                wrong = [chip for chip in added if skill_key(chip) not in keys]
                if wrong:
                    control("remove", wrong)
                    if set(wrong) & set(control()["chips"]):
                        raise RuntimeError("Inspect the unexpected skill chip before continuing.")
                    needs_attention = True
                    break
                settled = next((chip for chip in added if skill_key(chip) in keys), None)
                if settled:
                    break
                option = next((label for label in field["options"] if skill_key(label) in keys), None)
                if option and not clicked_option:
                    clicked_option = control("choose", [option])
                time.sleep(0.1)
            if clicked_option and not settled:
                needs_attention = True
            if settled or needs_attention:
                break
        if settled:
            report["selected"][skill] = settled
        else:
            report["needs_attention" if needs_attention else "unavailable"].append(skill)
    final = control()
    report["chips"] = final["chips"]
    if not final["disabled"]:
        replace_text(cdp, session_id, field_id, "", commit=True)
    return report
