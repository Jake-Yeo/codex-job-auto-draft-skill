#!/usr/bin/env python3
"""Maintain a private applicant profile and generate its local browser page."""

import argparse
from contextlib import contextmanager
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import webbrowser


SCHEMA_VERSION = 1
SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "assets" / "profile-template.html"
SETUP_PAGE = SKILL_DIR / "references" / "setup.html"
MODULE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")

BUILTIN_MODULES = {
    "contact": "Contact and links",
    "documents": "Résumé and required uploads",
    "education": "Education",
    "experience": "Experience",
    "projects": "Projects",
    "skills": "Skills",
    "cover-letters": "Cover letters",
    "eligibility": "Work authorization",
    "screening": "Screening answers",
    "preferences": "Preferences",
}

AUTOAPPLY_GROUPS = {
    "contact": ("first_name", "last_name", "email", "phone", "phone_device_type",
                "addresses", "linkedin", "github", "portfolio", "website"),
    "education": ("education",),
    "experience": ("experience", "years_experience"),
    "projects": ("project", "projects"),
    "skills": ("skills",),
    "eligibility": ("sponsorship", "citizenship", "us_immigration_status"),
    "screening": ("application_answers",),
    "preferences": ("desired_salary", "willing_to_relocate"),
    "self-identification": ("disability_status", "ethnicity", "gender_identity",
                            "hispanic_latino", "lgbt_status", "sex",
                            "sexual_orientation", "transgender", "veteran_status"),
}


class ProfileError(Exception):
    pass


def default_dir():
    configured = os.environ.get("JOB_APPLICATIONS_PROFILE_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".local/share/job-applications"


def label(key):
    return key.replace("_", " ").replace("-", " ").strip().capitalize()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfileError(f"Could not read {path.name} as JSON.") from exc


def write_private(path, text):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def markdown_modules(files):
    """Split each selected Markdown file into plain-text modules by heading."""
    modules = {}
    for filename in files:
        path = Path(filename)
        prefix = re.sub(r"[^a-z0-9]+", "-", path.stem.casefold()).strip("-") or "notes"
        title, lines, fence, is_section = path.stem, [], None, False

        def add_module():
            text = "\n".join(lines).strip()
            if not text and not is_section:
                return
            slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-") or "section"
            base = f"notes-{prefix}-{slug}"[:72].rstrip("-")
            key = base
            number = 2
            while key in modules:
                key = f"{base}-{number}"
                number += 1
            modules[key] = {"title": title, "fields": {"notes": text} if text else {}, "source": path.name}

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProfileError(f"Could not read the linked notes file {path.name}.") from exc
        for line in text.splitlines():
            marker = re.match(r"^\s{0,3}(\x60{3,}|~{3,})(.*)$", line)
            if marker:
                token, end = marker.groups()
                if not fence:
                    fence = token
                elif token.startswith(fence) and not end.strip():
                    fence = None
            heading = None if fence else re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                add_module()
                title, lines = heading.group(2).rstrip("#").strip(), []
                is_section = len(heading.group(1)) > 1
            else:
                lines.append(line)
        add_module()
    return modules


def module_view(state):
    modules = {mid: {"title": title, "fields": {}} for mid, title in BUILTIN_MODULES.items()}
    sources = state["sources"]
    if location := sources.get("autoapply"):
        facts = read_json(Path(location))
        if not isinstance(facts, dict):
            raise ProfileError("The linked AutoApply profile should contain a JSON object.")
        groups = dict(AUTOAPPLY_GROUPS)
        groups["eligibility"] += tuple(key for key in facts if key.startswith("work_auth_"))
        for key, fields in groups.items():
            values = {name: facts[name] for name in fields if name in facts}
            if values:
                module = modules.setdefault(key, {"title": label(key), "fields": {}})
                module["fields"].update(values)
        used = {field for fields in groups.values() for field in fields}
        extra = {key: value for key, value in facts.items() if key not in used}
        if extra:
            modules["saved-facts"] = {"title": "Other saved facts", "fields": extra}
    modules["documents"]["fields"].update(sources.get("documents", {}))
    modules.update(markdown_modules(sources.get("notes", [])))
    for key, record in state["modules"].items():
        module = modules.setdefault(key, {"title": label(key), "fields": {}})
        if "title" in record:
            module["title"] = record["title"]
        module["fields"].update(record["fields"])
    return modules


def value_html(value):
    if isinstance(value, dict):
        return fields_html(value)
    if isinstance(value, list):
        if not value:
            return '<span class="muted">None saved</span>'
        return "<ul>" + "".join(f"<li>{value_html(item)}</li>" for item in value) + "</ul>"
    if value is None or value == "":
        return '<span class="muted">Not provided</span>'
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return f'<span class="value">{escape(str(value))}</span>'


def fields_html(fields):
    if not fields:
        return '<p class="muted">Nothing saved here yet.</p>'
    return "<dl>" + "".join(
        f"<dt>{escape(label(key))}</dt><dd>{value_html(value)}</dd>"
        for key, value in fields.items()
    ) + "</dl>"


def render_html(modules):
    nav, cards = [], []
    for module_id, module in modules.items():
        safe_id = escape(module_id, quote=True)
        title = escape(module["title"])
        fields = module["fields"]
        notes = module.get("source")
        nav_label = f'{title} <small>Notes</small>' if notes else title
        nav.append(f'<a href="#{safe_id}">{nav_label}</a>')
        source = f'<p class="source">From {escape(notes)}</p>' if notes else ""
        body = fields_html(fields)
        badge = "Notes" if notes else f"{len(fields)} saved"
        opened = " open" if fields and not notes and module_id != "self-identification" else ""
        cards.append(
            f'<details class="module" id="{safe_id}"{opened}>'
            f'<summary>{title}<span>{badge}</span></summary>'
            f'<div class="module-body">{source}{body}</div></details>'
        )
    replacements = {
        "<!-- NAV -->": "".join(nav),
        "<!-- MODULES -->": "\n".join(cards),
        "<!-- SUMMARY -->": f"{sum(bool(item['fields']) for item in modules.values())} of {len(modules)} sections filled",
    }
    # Substitute once so applicant text cannot introduce another template token.
    return re.sub(
        r"<!-- (?:NAV|MODULES|SUMMARY) -->",
        lambda match: replacements[match[0]],
        TEMPLATE.read_text(encoding="utf-8"),
    )


def open_local_page(page):
    if not page.is_file():
        raise ProfileError("The local page file is missing.")
    opened = False
    if sys.platform == "darwin":
        result = subprocess.run(
            ["/usr/bin/open", "-g", "-a", "Google Chrome", str(page)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        opened = result.returncode == 0
    if not opened:
        opened = webbrowser.open(page.as_uri())
    return {"page": str(page), "opened": opened}


def setup_status(modules):
    def fields(module):
        return modules.get(module, {}).get("fields", {})

    def has_text(value):
        return isinstance(value, str) and bool(value.strip())

    contact = fields("contact")
    countries = fields("preferences").get("target_countries")
    countries = [country.strip().casefold() for country in countries if has_text(country)] if isinstance(countries, list) else []
    eligibility = fields("eligibility").get("work_authorization", {})
    eligibility = {name.strip().casefold(): answer for name, answer in eligibility.items()} if isinstance(eligibility, dict) else {}
    resume = fields("documents").get("resume")
    checks = {
        "name": has_text(contact.get("full_name")) or (has_text(contact.get("first_name")) and has_text(contact.get("last_name"))),
        "email": has_text(contact.get("email")),
        "phone": has_text(contact.get("phone")),
        "location": has_text(contact.get("location")) or bool(contact.get("addresses")),
        "target-countries": bool(countries),
        "work-authorization": bool(countries) and all(
            isinstance(eligibility.get(country), dict)
            and all(isinstance(eligibility[country].get(key), bool) for key in ("authorized", "needs_sponsorship"))
            for country in countries
        ),
        "resume": has_text(resume) and Path(resume).expanduser().is_file(),
        "education": bool(fields("education")),
        "experience": bool(fields("experience")),
        "skills": bool(fields("skills")),
        "links": isinstance(contact.get("links"), dict),
    }
    choices = fields("setup").get("deferred", [])
    choices = set(item for item in choices if isinstance(item, str)) if isinstance(choices, list) else set()
    missing = [key for key, done in checks.items() if not done and key not in choices]
    deferred = [key for key, done in checks.items() if not done and key in choices]
    return {"missing": missing, "deferred": deferred, "interview_complete": not missing}


class ProfileStore:
    def __init__(self, directory=None):
        self.directory = Path(directory or default_dir()).expanduser().resolve()
        self.state_path = self.directory / "profile.json"
        self.page_path = self.directory / "profile.html"

    def load(self):
        if not self.state_path.exists():
            return {"version": SCHEMA_VERSION, "sources": {}, "modules": {}}
        state = read_json(self.state_path)
        if (not isinstance(state, dict) or state.get("version") != SCHEMA_VERSION
                or not all(isinstance(state.get(key), dict) for key in ("sources", "modules"))):
            raise ProfileError("The saved profile has an unsupported format.")
        return state

    @contextmanager
    def locked(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name != "nt" and self.directory.stat().st_mode & 0o077:
            raise ProfileError("Choose a profile directory that only your account can access.")
        fd = os.open(self.directory / ".lock", os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "r+b") as lock:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def list_modules(self):
        return [{"id": key, "title": item["title"], "fields": len(item["fields"])}
                for key, item in module_view(self.load()).items()]

    def read_module(self, module_id):
        module = module_view(self.load()).get(module_id)
        if module is None:
            raise ProfileError("That module is missing. List the saved modules for valid IDs.")
        return {"id": module_id, **module}

    def render(self):
        with self.locked():
            write_private(self.page_path, render_html(module_view(self.load())))
        return self.page_path

    def save(self, state):
        page = render_html(module_view(state))
        state_json = json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        write_private(self.state_path, state_json)
        write_private(self.page_path, page)

    def upsert(self, changes):
        changes = [changes] if isinstance(changes, dict) else changes
        if not isinstance(changes, list) or not changes:
            raise ProfileError("Supply one module or a nonempty list of modules.")
        with self.locked():
            state = self.load()
            for change in changes:
                if not isinstance(change, dict) or set(change) - {"id", "title", "fields"}:
                    raise ProfileError("A module update accepts id, title and fields.")
                key = change.get("id")
                if not isinstance(key, str) or MODULE_ID.fullmatch(key) is None:
                    raise ProfileError("Use a module ID with lowercase letters, digits and hyphens.")
                fields = change.get("fields", {})
                if not isinstance(fields, dict) or any(
                    not isinstance(name, str) or not name.strip() for name in fields
                ):
                    raise ProfileError("Fields must be an object with nonempty names.")
                module = state["modules"].setdefault(key, {"fields": {}})
                if "title" in change:
                    title = change["title"]
                    if not isinstance(title, str) or not title.strip():
                        raise ProfileError("A module title must be text.")
                    module["title"] = title.strip()
                module["fields"].update(fields)
            self.save(state)
        return {"updated": [change["id"] for change in changes], "page": str(self.page_path)}

    def link_sources(self, autoapply=None, notes=None, documents=None):
        def existing(value):
            path = Path(value).expanduser().resolve()
            if not path.is_file():
                raise ProfileError(f"File not found: {path.name}")
            return str(path)

        with self.locked():
            state = self.load()
            sources = state["sources"]
            if autoapply:
                sources["autoapply"] = existing(autoapply)
            if notes:
                sources["notes"] = list(dict.fromkeys(sources.get("notes", []) + [existing(path) for path in notes]))
            if documents:
                sources.setdefault("documents", {}).update({key: existing(path) for key, path in documents.items()})
            self.save(state)
        return {"page": str(self.page_path), "linked_sources": sorted(sources)}

    def open(self):
        return open_local_page(self.render())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("open", "render", "list", "setup", "setup-status", "setup-help"):
        commands.add_parser(name)
    commands.add_parser("read").add_argument("module")
    commands.add_parser("upsert", help="Read a module update as JSON on stdin.")
    link = commands.add_parser("link", help="Link your existing files without changing them.")
    link.add_argument("--autoapply-json", type=Path)
    link.add_argument("--notes", type=Path, action="append")
    link.add_argument("--resume", type=Path)
    link.add_argument("--transcript", type=Path)
    args = parser.parse_args()
    store = ProfileStore(args.data_dir)
    try:
        if args.command == "open":
            result = store.open()
        elif args.command == "setup-help":
            result = open_local_page(SETUP_PAGE)
        elif args.command in {"setup", "setup-status"}:
            result = setup_status(module_view(store.load()))
            if args.command == "setup":
                result.update(open_local_page(SETUP_PAGE))
        elif args.command == "render":
            result = {"page": str(store.render())}
        elif args.command == "list":
            result = store.list_modules()
        elif args.command == "read":
            result = store.read_module(args.module)
        elif args.command == "upsert":
            result = store.upsert(json.load(sys.stdin))
        else:
            documents = {key: value for key, value in (("resume", args.resume), ("transcript", args.transcript)) if value}
            if not (args.autoapply_json or args.notes or documents):
                parser.error("link requires at least one file")
            result = store.link_sources(args.autoapply_json, args.notes, documents)
    except (ProfileError, OSError, ValueError) as exc:
        parser.exit(1, f"{exc if isinstance(exc, ProfileError) else 'Could not update the local profile.'}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
