#!/usr/bin/env python3
"""Maintain a private applicant profile and generate its local browser page."""

import argparse
from contextlib import contextmanager
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import webbrowser


SCHEMA_VERSION = 1
SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "assets" / "profile-template.html"
SETUP_PAGE = SKILL_DIR / "references" / "setup.html"
MODULE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")
DOCUMENT_FIELDS = frozenset({"resume", "transcript", "cover_letter"})
APPLICATION_MODULES = frozenset({
    "cover-letters", "eligibility", "screening", "preferences", "self-identification",
})
RECORD_HEADINGS = {
    "education": ("school", "degree", "field_of_study"),
    "experience": ("title", "company", "location"),
}
ADDRESS_FIELDS = ("street", "unit", "city", "region", "postal_code", "country")
CONTACT_LINKS = ("linkedin", "github", "portfolio", "website")
FIELD_TITLES = {
    "full_name": "Name",
    "github": "GitHub",
    "gpa": "GPA",
    "gpa_basis": "GPA basis",
    "gpa_numeric": "Numeric GPA",
    "gpa_scale": "GPA scale",
    "linkedin": "LinkedIn",
    "phone_device_type": "Phone type",
    "years_experience": "Years of experience",
}

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


def write_private(path, contents):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(contents.encode("utf-8") if isinstance(contents, str) else contents)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def local_reference(directory, value):
    if not isinstance(value, str) or not value.strip():
        raise ProfileError("A saved file reference must be a local path.")
    path = (directory / Path(value).expanduser()).resolve()
    if not path.is_relative_to(directory):
        raise ProfileError("Import linked files into the MCP data folder before using the profile.")
    return path


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


def module_view(state, directory):
    modules = {mid: {"title": title, "fields": {}} for mid, title in BUILTIN_MODULES.items()}
    sources = state["sources"]
    if location := sources.get("autoapply"):
        facts = read_json(local_reference(directory, location))
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
    document_keys = set(sources.get("documents", {}))
    modules["documents"]["fields"].update(sources.get("documents", {}))
    modules.update(markdown_modules(local_reference(directory, path) for path in sources.get("notes", [])))
    for key, record in state["modules"].items():
        module = modules.setdefault(key, {"title": label(key), "fields": {}})
        if "title" in record:
            module["title"] = record["title"]
        module["fields"].update(record["fields"])
    for key in document_keys | DOCUMENT_FIELDS:
        value = modules["documents"]["fields"].get(key)
        if value:
            modules["documents"]["fields"][key] = str(local_reference(directory, value))
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
    rows = []
    for key, value in fields.items():
        title = FIELD_TITLES.get(key, label(key))
        long_text = isinstance(value, str) and (len(value) > 72 or "\n" in value)
        wide = long_text or isinstance(value, (dict, list))
        rows.append(
            f'<div class="field{" wide" if wide else ""}">'
            f"<dt>{escape(title)}</dt><dd>{value_html(value)}</dd></div>"
        )
    return '<dl class="fields">' + "".join(rows) + "</dl>"


def take_text(fields, key):
    value = fields.get(key)
    if isinstance(value, str) and value.strip():
        return escape(fields.pop(key))
    return ""


def address_html(key, record):
    fields = record.copy()
    parts = {}
    for field in ADDRESS_FIELDS:
        if type(fields.get(field)) in (int, float):
            fields[field] = str(fields[field])
        parts[field] = take_text(fields, field)
        if fields.get(field) in (None, ""):
            fields.pop(field, None)

    country = parts["country"]
    name = label(key)
    if country and (len(key) == 2 or name.casefold() == country.casefold()):
        name = ""
    heading = " · ".join(part for part in (escape(name), country) if part)
    title = f"<h4>{heading}</h4>" if heading else ""

    unit = f'Unit {parts["unit"]}' if parts["unit"] else ""
    street = ", ".join(part for part in (parts["street"], unit) if part)
    region = " ".join(part for part in (parts["region"], parts["postal_code"]) if part)
    area = ", ".join(part for part in (parts["city"], region) if part)
    lines = "<br>".join(part for part in (street, area) if part)
    postal = f"<address>{lines}</address>" if lines else ""
    other = fields_html(fields) if fields else ""
    body = title + postal + other
    return f'<li>{body or fields_html({})}</li>'


def addresses_html(addresses):
    if isinstance(addresses, dict) and any(key in addresses for key in ADDRESS_FIELDS):
        records = [("", addresses)]
    elif isinstance(addresses, dict) and all(isinstance(record, dict) for record in addresses.values()):
        records = addresses.items()
    elif isinstance(addresses, list) and all(isinstance(record, dict) for record in addresses):
        records = [("", record) for record in addresses]
    else:
        return value_html(addresses)
    entries = "".join(address_html(key, record) for key, record in records)
    return f'<ul class="address-list" role="list">{entries}</ul>'


def contact_links_html(links):
    entries = []
    other = {}
    for key, value in links.items():
        address = value.strip() if isinstance(value, str) else ""
        try:
            url = urlsplit(address)
        except ValueError:
            other[key] = value
            continue
        if url.scheme not in {"http", "https"} or not url.hostname or any(char.isspace() for char in address):
            other[key] = value
            continue
        title = escape(FIELD_TITLES.get(key, label(key)))
        domain = escape(url.hostname.removeprefix("www."))
        entries.append(
            f'<li><a class="saved-link" href="{escape(address, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'<span>{title}</span><small>{domain}</small></a></li>'
        )
    listed = f'<ul class="link-list" role="list">{"".join(entries)}</ul>' if entries else ""
    return listed + (fields_html(other) if other else "")


def contact_html(fields):
    details = fields.copy()
    addresses = details.pop("addresses", None)
    links = {key: details.pop(key) for key in CONTACT_LINKS if key in details}
    saved_links = details.pop("links", None)
    if isinstance(saved_links, dict):
        for key, value in saved_links.items():
            links[key] = [links[key], value] if key in links and links[key] != value else value
        saved_links = None

    first, last = details.get("first_name"), details.get("last_name")
    if all(isinstance(part, str) and part.strip() for part in (first, last)):
        name = f"{first.strip()} {last.strip()}"
        if details.get("full_name") in (None, "", name):
            details["full_name"] = name
            del details["first_name"], details["last_name"]
    phone, device = details.get("phone"), details.get("phone_device_type")
    if all(isinstance(part, str) and part.strip() for part in (phone, device)):
        details["phone"] = f"{phone.strip()} · {device.strip()}"
        del details["phone_device_type"]

    priority = ("full_name", "first_name", "last_name", "email", "phone", "phone_device_type")
    primary = {key: details.pop(key) for key in priority if key in details}
    primary.update(details)
    parts = [fields_html(primary)] if primary else []
    if addresses not in (None, "", {}, []):
        parts.append(f'<section class="contact-group"><h3>Addresses</h3>{addresses_html(addresses)}</section>')
    if links or saved_links not in (None, "", []):
        link_fields = contact_links_html(links)
        extra_links = value_html(saved_links) if saved_links is not None else ""
        parts.append(f'<section class="contact-group"><h3>Links</h3>{link_fields}{extra_links}</section>')
    return "".join(parts) or fields_html({})


def description_html(text):
    lines = [line for line in text.splitlines() if line.strip()]
    bullets = [re.fullmatch(r"\s*[•*-]\s+(.+)", line) for line in lines]
    if bullets and all(bullets):
        return value_html([match[1] for match in bullets])
    return value_html(text)


def record_html(record, heading_keys):
    fields = record.copy()
    names = [part for key in heading_keys if (part := take_text(fields, key))]
    identity = ""
    if names:
        title, *context = names
        subtitle = f'<p class="record-context">{" · ".join(context)}</p>' if context else ""
        identity = f'<div><h3>{title}</h3>{subtitle}</div>'

    start = take_text(fields, "start_date")
    end = take_text(fields, "end_date")
    if start and end:
        period = f"{start} – {end}"
    elif start:
        period = f"From {start}"
    else:
        period = f"Until {end}" if end else ""
    dates = f'<p class="record-dates">{period}</p>' if period else ""
    heading = f'<div class="record-heading">{identity}{dates}</div>' if identity or dates else ""

    narrative = ""
    description = fields.get("description")
    if isinstance(description, str) and description.strip():
        narrative = f'<div class="record-description">{description_html(fields.pop("description"))}</div>'
    extra = fields_html(fields) if fields else ""
    body = heading + narrative + extra
    return f'<li class="record">{body or fields_html({})}</li>'


def module_fields_html(module_id, fields):
    if module_id == "contact":
        return contact_html(fields)
    heading_keys = RECORD_HEADINGS.get(module_id)
    if not heading_keys:
        return fields_html(fields)

    records = fields.get(module_id)
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list) or not records or not all(isinstance(record, dict) for record in records):
        return fields_html(fields)

    entries = "".join(record_html(record, heading_keys) for record in records)
    rest = {key: value for key, value in fields.items() if key != module_id}
    extra = fields_html(rest) if rest else ""
    return f'<ul class="record-list" role="list">{entries}</ul>{extra}'


def render_html(modules):
    group_titles = {"details": "Profile", "applications": "Applications", "notes": "Saved notes"}
    groups = {key: [] for key in group_titles}
    panels = []
    for module_id, module in modules.items():
        safe_id = escape(module_id, quote=True)
        title = escape(module["title"])
        fields = module["fields"]
        notes = module.get("source")
        source = f'<p class="source">From {escape(notes)}</p>' if notes else ""
        body = value_html(fields["notes"]) if notes and fields.keys() == {"notes"} else module_fields_html(module_id, fields)
        group = "notes" if notes else "applications" if module_id in APPLICATION_MODULES else "details"
        groups[group].append(f'<a href="#{safe_id}">{title}</a>')
        panels.append(
            f'<article class="profile-panel" id="{safe_id}" aria-labelledby="title:{safe_id}">'
            f'<h2 id="title:{safe_id}" tabindex="-1">{title}</h2>'
            f'<div class="panel-body">{source}{body}</div></article>'
        )
    nav = []
    for key, title in group_titles.items():
        if not groups[key]:
            continue
        nav.append(
            f'<section class="nav-group" aria-labelledby="group:{key}">'
            f'<h2 id="group:{key}">{title}</h2>{"".join(groups[key])}</section>'
        )
    replacements = {
        "<!-- NAV -->": "".join(nav),
        "<!-- MODULES -->": "\n".join(panels),
    }
    # Substitute once so applicant text cannot introduce another template token.
    return re.sub(
        r"<!-- (?:NAV|MODULES) -->",
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
        state = read_json(local_reference(self.directory, self.state_path.name))
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

    def modules(self):
        return module_view(self.load(), self.directory)

    def list_modules(self):
        return [{"id": key, "title": item["title"], "fields": len(item["fields"])}
                for key, item in self.modules().items()]

    def read_module(self, module_id):
        module = self.modules().get(module_id)
        if module is None:
            raise ProfileError("That module is missing. List the saved modules for valid IDs.")
        return {"id": module_id, **module}

    def render(self):
        with self.locked():
            write_private(self.page_path, render_html(self.modules()))
        return self.page_path

    def save(self, state):
        page = render_html(module_view(state, self.directory))
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

    def import_file(self, value, category):
        if not isinstance(value, (Path, str)) or not str(value).strip():
            raise ProfileError("Provide a path to an applicant-approved local file.")
        source = Path(value).expanduser().resolve()
        if not source.is_file():
            raise ProfileError(f"File not found: {source.name}")
        if source.is_relative_to(self.directory):
            return str(source)
        contents = source.read_bytes()
        digest = sha256(contents).hexdigest()
        destination = local_reference(self.directory, f"imports/{category}/{digest}/{source.name}")
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not destination.is_file():
            write_private(destination, contents)
        return str(destination)

    def import_documents(self, fields, keys):
        return {
            key: self.import_file(value, "documents") if key in keys and value else value
            for key, value in fields.items()
        }

    def link_sources(self, autoapply=None, notes=None, documents=None):
        with self.locked():
            state = self.load()
            sources = state["sources"]
            if autoapply:
                sources["autoapply"] = self.import_file(autoapply, "facts")
            if notes:
                copies = [self.import_file(path, "notes") for path in notes]
                sources["notes"] = list(dict.fromkeys(sources.get("notes", []) + copies))
            if documents:
                sources.setdefault("documents", {}).update(self.import_documents(documents, documents.keys()))
            self.save(state)
        return {"page": str(self.page_path), "linked_sources": sorted(sources)}

    def import_linked_files(self):
        """Copy the active profile's previously linked files into its MCP store."""
        with self.locked():
            state = self.load()
            sources = state["sources"]
            if sources.get("autoapply"):
                sources["autoapply"] = self.import_file(sources["autoapply"], "facts")
            if "notes" in sources:
                sources["notes"] = [self.import_file(path, "notes") for path in sources["notes"]]
            if "documents" in sources:
                docs = sources["documents"]
                sources["documents"] = self.import_documents(docs, docs.keys())
            if "documents" in state["modules"]:
                record = state["modules"]["documents"]
                record["fields"] = self.import_documents(
                    record["fields"], DOCUMENT_FIELDS | set(sources.get("documents", {}))
                )
            self.save(state)
        return {"page": str(self.page_path), "data_directory": str(self.directory)}

    def open(self):
        return open_local_page(self.render())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("open", "render", "list", "setup", "setup-status", "setup-help"):
        commands.add_parser(name)
    commands.add_parser("import-linked-files", help="Import files already linked in a legacy profile into its MCP data folder.")
    commands.add_parser("read").add_argument("module")
    commands.add_parser("upsert", help="Read a module update as JSON on stdin.")
    link = commands.add_parser("link", help="Import private copies of approved existing files into the MCP data folder.")
    link.add_argument("--autoapply-json", type=Path)
    link.add_argument("--notes", type=Path, action="append")
    link.add_argument("--resume", type=Path)
    link.add_argument("--transcript", type=Path)
    link.add_argument("--cover-letter", type=Path)
    args = parser.parse_args()
    store = ProfileStore(args.data_dir)
    try:
        if args.command == "open":
            result = store.open()
        elif args.command == "setup-help":
            result = open_local_page(SETUP_PAGE)
        elif args.command in {"setup", "setup-status"}:
            result = setup_status(store.modules())
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
        elif args.command == "import-linked-files":
            result = store.import_linked_files()
        else:
            documents = {
                key: path for key, path in (
                    ("resume", args.resume),
                    ("transcript", args.transcript),
                    ("cover_letter", args.cover_letter),
                ) if path
            }
            if not (args.autoapply_json or args.notes or documents):
                parser.error("link requires at least one file")
            result = store.link_sources(args.autoapply_json, args.notes, documents)
    except (ProfileError, OSError, ValueError) as exc:
        parser.exit(1, f"{exc if isinstance(exc, ProfileError) else 'Could not update the local profile.'}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
