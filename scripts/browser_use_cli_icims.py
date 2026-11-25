"""Read iCIMS draft status and saved documents on an attached Path 2 tab."""

from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

from draft_guard import ICIMS_JOB_PATH


READ_DRAFT = r"""
async ({origin, requisition, fingerprints}) => {
  const form = document.getElementById("icims_content_iframe")?.contentDocument || document;
  const current = new URL(form.URL);
  const job = current.pathname.match(/^\/jobs\/([0-9]+)(?:\/[^/]+)?\/(?:job|candidate|questions|eeo)\/?$/);
  if (current.origin !== origin || !job || job[1] !== requisition) {
    return {error: "The current form does not match the expected iCIMS requisition."};
  }
  const text = element => (element?.textContent || "").trim().replace(/\s+/g, " ");
  const result = {
    requisition,
    step: text(form.querySelector(".iCIMS_Steps_Current")),
    saved: form.body?.innerText.includes("Your responses have been saved.") || false,
    dashboard: null,
    profileDocuments: null,
  };
  const findLink = (doc, name) => [...doc.querySelectorAll("a[href]")]
    .find(link => text(link).toLowerCase() === name);
  const dashboardLink = findLink(form, "dashboard");
  if (!dashboardLink) return result;

  async function getLink(link, base) {
    const url = new URL(link.getAttribute("href"), base);
    if (url.origin !== origin) throw Error("The employer link leaves the current portal.");
    const response = await form.defaultView.fetch(url.href, {
      mode: "same-origin",
      credentials: "same-origin",
      cache: "no-store",
      signal: AbortSignal.timeout(6000),
    });
    if (!response.ok) throw Error("The employer page was unavailable.");
    return response;
  }
  async function getPage(link, base) {
    const response = await getLink(link, base);
    const doc = new DOMParser().parseFromString(await response.text(), "text/html");
    return {doc, base: response.url};
  }
  let dashboard;
  try {
    dashboard = await getPage(dashboardLink, form.URL);
  } catch {
    result.dashboard = {error: "Could not read the employer dashboard."};
    return result;
  }
  const jobCell = new RegExp("^(?:Job ID\\s+)?(?:[0-9]{4}-)?" + requisition + "$", "i");
  const row = [...dashboard.doc.querySelectorAll("tr")]
    .find(row => [...row.cells].some(cell => jobCell.test(text(cell))));
  if (row) {
    const status = [...row.cells].find(cell => /^Status\s/i.test(text(cell)))
      || row.cells[[...dashboard.doc.querySelectorAll("th")].findIndex(cell => /^Status$/i.test(text(cell)))];
    const continueLink = findLink(row, "continue application");
    result.dashboard = {
      status: status ? text(status).replace(/^Status\s+/i, "") : null,
      canContinue: !!continueLink && !continueLink.classList.contains("iCIMS_Hidden"),
    };
  }

  const profileLink = findLink(dashboard.doc, "update your profile/resume");
  if (!profileLink || !Object.keys(fingerprints).length) return result;
  let profile;
  try {
    profile = await getPage(profileLink, dashboard.base);
  } catch {
    result.profileDocuments = {error: "Could not read the saved candidate profile."};
    return result;
  }
  if (!profile.doc.getElementById("profileForm")) {
    result.profileDocuments = {error: "The candidate profile is unavailable on this session."};
    return result;
  }

  const coverFields = [...profile.doc.querySelectorAll('input[type=file][id$="_File"]')]
    .filter(input => {
      const labels = [...input.labels || []].map(text);
      const ids = (input.getAttribute("aria-labelledby") || "").split(/\s+/);
      labels.push(input.getAttribute("aria-label") || "");
      labels.push(...ids.map(id => text(profile.doc.getElementById(id))));
      return labels.some(label => /\bcover\s+letter\b/i.test(label));
    });
  const coverId = coverFields.length === 1 ? coverFields[0].id.replace(/_File$/, "_CurrentFile") : null;
  async function checkFile(id, expected) {
    if (!id) return {filename: null, matches: null, error: "Could not identify the profile's cover-letter field."};
    const link = profile.doc.getElementById(id)?.querySelector("a[href]");
    if (!link) return {filename: null, matches: null};
    const filename = text(link);
    if (!expected) return {filename, matches: null};
    try {
      const response = await getLink(link, profile.base);
      const bytes = await response.arrayBuffer();
      const hash = await form.defaultView.crypto.subtle.digest("SHA-256", bytes);
      const actual = [...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, "0")).join("");
      return {filename, matches: actual === expected};
    } catch {
      return {filename, matches: null, error: "Could not verify the saved PDF contents."};
    }
  }
  const [resume, coverLetter] = await Promise.all([
    checkFile("PortalProfileFields.Resume_CurrentFile", fingerprints.resume),
    checkFile(coverId, fingerprints.coverLetter),
  ]);
  result.profileDocuments = {resume, coverLetter};
  return result;
}
"""


def inspect_draft(cdp, session_id, application_url, *, resume=None, cover_letter=None):
    """Read the exact requisition and optionally compare PDFs on the shared profile.

    Use the session returned by `switch_tab(target_id, activate=False)`. This reads
    links the portal displays without navigating the tab or changing any answers.
    A match confirms what the profile holds, not what a past submission contains.
    """
    url = urlsplit(application_url)
    job = ICIMS_JOB_PATH.fullmatch(url.path)
    if (url.scheme not in ("http", "https") or not url.hostname or url.username or url.password
            or not (url.hostname == "icims.com" or url.hostname.endswith(".icims.com")) or not job):
        raise ValueError("Use the observed requisition URL on the iCIMS portal.")
    fingerprints = {
        kind: sha256(Path(path).expanduser().read_bytes()).hexdigest()
        for kind, path in (("resume", resume), ("coverLetter", cover_letter))
        if path is not None
    }
    query = {
        "origin": f"{url.scheme}://{url.netloc}",
        "requisition": job[1],
        "fingerprints": fingerprints,
    }
    response = cdp(
        "Runtime.evaluate", session_id=session_id,
        expression=f"({READ_DRAFT})({json.dumps(query)})",
        awaitPromise=True, returnByValue=True, _response_timeout=22,
    )
    result = response.get("result", {}).get("value")
    if "exceptionDetails" in response or not isinstance(result, dict):
        raise RuntimeError("Could not inspect the existing iCIMS form.")
    return result
