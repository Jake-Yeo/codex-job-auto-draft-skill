"""Batch ordinary fields and stage files on an already attached Path 2 tab."""

from contextlib import suppress
import json
from pathlib import Path


def evaluate(cdp, session_id, function, *args, by_value=True):
    expression = f"({function})({', '.join(json.dumps(arg) for arg in args)})"
    reply = cdp(
        "Runtime.evaluate", session_id=session_id, expression=expression,
        returnByValue=by_value, awaitPromise=True, _response_timeout=5,
    )
    if "exceptionDetails" in reply:
        raise RuntimeError("The browser could not evaluate the observed form control.")
    result = reply["result"]
    return result.get("value") if by_value else result.get("objectId")


def tap_key(cdp, session_id, key, code):
    for kind in ("rawKeyDown", "keyUp"):
        cdp("Input.dispatchKeyEvent", session_id=session_id, type=kind, key=key,
            code=key, windowsVirtualKeyCode=code)


def replace_text(cdp, session_id, field_id, value, *, commit=True):
    """Replace an observed plain text input or textarea in one browser input call."""
    field = evaluate(cdp, session_id, """id => {
      const el = document.getElementById(id);
      if (!el || el.disabled || el.readOnly || !el.getClientRects().length ||
          !el.matches('textarea,input[type="text"],input:not([type]),input[type="email"],'
                      + 'input[type="tel"],input[type="url"],input[type="number"],input[type="search"]')) {
        return null;
      }
      el.focus({preventScroll: true});
      if (document.activeElement !== el) return null;
      if (el.value) el.select();
      return {empty: !el.value, selected: el.selectionStart === 0 &&
                                         el.selectionEnd === el.value.length};
    }""", field_id)
    if field is None:
        return False
    if not field["empty"] and not field["selected"]:
        for kind in ("rawKeyDown", "keyUp"):
            commands = {"commands": ["SelectAll"]} if kind == "rawKeyDown" else {}
            cdp("Input.dispatchKeyEvent", session_id=session_id, type=kind, key="a",
                code="KeyA", windowsVirtualKeyCode=65, **commands)
    if value:
        cdp("Input.insertText", session_id=session_id, text=value)
    elif not field["empty"]:
        tap_key(cdp, session_id, "Backspace", 8)

    return evaluate(cdp, session_id, """(id, expected, commit) => {
      const el = document.getElementById(id);
      if (!el || el.value !== expected || document.activeElement !== el) return false;
      if (commit) el.blur();
      return document.getElementById(id)?.value === expected;
    }""", field_id, value, commit)


def fill_text_fields(cdp, session_id, fields):
    """Fill observed IDs together and return the fields that need a different control."""
    return {
        field_id: replace_text(cdp, session_id, field_id, str(value))
        for field_id, value in fields.items()
    }


def stage_files_once(cdp, session_id, selector, paths):
    """Use one file selection on the observed input in local Chrome."""
    if isinstance(paths, (str, Path)):
        paths = [paths]
    files = [str(Path(path).expanduser().resolve(strict=True)) for path in paths]
    if not files or any(not Path(path).is_file() for path in files):
        raise ValueError("Select existing files for the observed upload field.")
    element = evaluate(cdp, session_id, """(selector, count) => {
      const matches = document.querySelectorAll(selector);
      const input = matches.length === 1 ? matches[0] : null;
      return input?.matches('input[type="file"]:enabled') && (count === 1 || input.multiple)
        ? input : null;
    }""", selector, len(files), by_value=False)
    if not element:
        raise ValueError("Identify one enabled file input with the required file capacity.")
    try:
        cdp("DOM.setFileInputFiles", session_id=session_id, objectId=element, files=files)
    finally:
        with suppress(RuntimeError):
            cdp("Runtime.releaseObject", session_id=session_id, objectId=element)
