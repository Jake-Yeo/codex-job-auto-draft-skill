#!/usr/bin/env python3
"""Render an approved draft as a private one-page cover-letter PDF."""

import argparse
import html
from pathlib import Path
import re
import sys
import tempfile

from applicant_profile import MODULE_ID, ProfileError, ProfileStore

from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def letter_pdf(path, text, sender, recipient, greeting="Dear Hiring Manager,"):
    from datetime import datetime

    from pypdf import PdfReader

    today = datetime.now().astimezone()
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "LetterBody",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=11,
        leading=13.2,
        spaceAfter=6.05,
        firstLineIndent=16.5,
    )
    title = ParagraphStyle(
        "LetterHeader",
        parent=body,
        firstLineIndent=0,
        spaceAfter=0,
    )

    def block(lines):
        return Paragraph("<br/>".join(html.escape(value) for value in lines if value), title)

    story = [
        block([sender.get(k, "") for k in ("name", "institution", "degree", "email", "phone")]),
        Spacer(1, 12.1),
        block(
            [recipient.get(k, "") for k in ("company", "location", "title")]
            + [f"{today:%B} {today.day}, {today.year}"]
        ),
        Spacer(1, 12.1),
        block([greeting]),
        Spacer(1, 3.85),
    ]
    story += [
        Paragraph(html.escape(part.strip()).replace("\n", "<br/>"), body)
        for part in text.split("\n\n")
        if part.strip()
    ]
    story += [Spacer(1, 3.85), block(["Sincerely,"]), Spacer(1, 12), block([sender["name"]])]
    SimpleDocTemplate(
        str(path),
        pagesize=(8.5 * inch, 11 * inch),
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    ).build(story)
    path.chmod(0o600)
    if len(PdfReader(path).pages) != 1:
        path.unlink()
        raise ValueError(
            "The letter exceeds one page at 11pt. Shorten the body while keeping its strongest job-specific story."
        )


def filename_part(value):
    return "_".join(word[0].upper() + word[1:] for word in re.findall(r"[^\W_]+", value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--job-key", required=True, help="A short lowercase ID for this application")
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--short-role")
    parser.add_argument("--location", default="")
    parser.add_argument("--greeting", default="Dear Hiring Manager,")
    args = parser.parse_args()
    if not MODULE_ID.fullmatch(args.job_key):
        parser.error("Use a lowercase job key with letters, digits, or hyphens.")
    body = sys.stdin.read().strip()
    if not body:
        parser.error("Provide the letter body on stdin.")
    store = ProfileStore(args.data_dir)
    try:
        contact = store.read_module("contact")["fields"]
        name = contact.get("full_name") or " ".join(
            str(contact[key]) for key in ("first_name", "last_name") if contact.get(key)
        )
        if not name:
            raise ValueError("Save the applicant's name to the profile first.")
        sender = {"name": name, "email": contact.get("email", ""), "phone": contact.get("phone", "")}
        recipient = {"company": args.company, "title": args.role, "location": args.location}
        pieces = [filename_part(value) for value in (args.company, args.short_role or args.role, name)]
        if not all(pieces):
            raise ValueError("A company, role, and sender name are required.")
        with store.locked():
            output = store.directory / "materials" / args.job_key
            output.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = output / ("_".join(pieces) + "_Cover_Letter.pdf")
            if path.exists():
                raise ValueError("A letter already exists for this job key. Use a new job key for a revised PDF.")
            with tempfile.TemporaryDirectory(dir=output) as temporary:
                draft = Path(temporary) / path.name
                letter_pdf(draft, body, sender, recipient, args.greeting)
                draft.replace(path)
    except (ProfileError, ValueError, OSError) as error:
        parser.exit(1, f"Cover letter: {error}\n")
    print(path)


if __name__ == "__main__":
    main()
