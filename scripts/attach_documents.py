#!/usr/bin/env python3
"""Build the local AutoApply extension and attach PDFs to an active jobs tab."""

import argparse
import base64
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import shutil
import sys
import threading

from applicant_profile import ProfileError, ProfileStore, read_json, write_private
from draft_guard import clean_url, load_state


EXTENSION_SOURCE = Path(__file__).resolve().parents[1] / "extension"
DEFAULT_PORT = 8769
MAX_PDF_BYTES = 8_000_000


def build_extension(store, requested_port):
    with store.locked():
        config_path = store.directory / "attachment-bridge.json"
        config = read_json(config_path) if config_path.exists() else {
            "port": DEFAULT_PORT,
            "token": secrets.token_urlsafe(32),
        }
        if requested_port is not None:
            config["port"] = requested_port
        if not 1024 <= config["port"] <= 65535:
            raise ValueError("Choose a port between 1024 and 65535.")
        folder = store.directory / "attachment-extension"
        folder.mkdir(mode=0o700, exist_ok=True)
        for name in ("worker.js", "attachment.js", "manifest.json"):
            shutil.copyfile(EXTENSION_SOURCE / name, folder / name)
        # This file is generated locally and contains the private bridge token.
        worker_config = {"base": f"http://127.0.0.1:{config['port']}", "token": config["token"]}
        write_private(
            folder / "bridge-config.js",
            "globalThis.JOB_APPLICATIONS_BRIDGE = " + json.dumps(worker_config) + ";\n",
        )
        write_private(config_path, json.dumps(config) + "\n")
    return {"extension_directory": str(folder)}


def pdf_payload(path, label):
    with path.open("rb") as document:
        content = document.read(MAX_PDF_BYTES + 1)
    if path.suffix.casefold() != ".pdf" or not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
        raise ValueError("Use a PDF under 8 MB.")
    return {"label": label, "name": path.name, "data": base64.b64encode(content).decode("ascii")}


class AttachmentRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        # The request may contain applicant data.
        return

    def reply(self, status, data):
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        bridge = self.server
        origin = self.headers.get("Origin", "")
        token = self.headers.get("X-AutoApply-Pipeline", "")
        if (self.headers.get("Host") != f"127.0.0.1:{bridge.server_port}"
                or (origin and not re.fullmatch(r"chrome-extension://[a-p]{32}", origin))
                or not token.isascii() or not hmac.compare_digest(token, bridge.token)):
            self.reply(403, {"error": "Local extension authentication required"})
            return
        if self.path not in {"/poll", "/result"}:
            self.reply(404, {"error": "Unknown route"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16_384:
                raise ValueError
            self.connection.settimeout(3)
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError
        except (OSError, ValueError):
            self.reply(400, {"error": "Invalid request"})
            return
        with bridge.lock:
            if self.path == "/poll":
                command = None if bridge.delivered else bridge.command
                bridge.delivered = True
                self.reply(200, command)
            elif (bridge.delivered and body.get("id") == bridge.command["id"]
                  and isinstance(body.get("result"), dict) and not bridge.done.is_set()):
                bridge.result = body["result"]
                self.reply(200, {"received": True})
                bridge.done.set()
            else:
                self.reply(409, {"error": "Unexpected attachment result"})


def send_to_extension(config, target, timeout=48):
    with ThreadingHTTPServer(("127.0.0.1", config["port"]), AttachmentRequestHandler) as server:
        server.token = config["token"]
        server.command = {"id": secrets.token_hex(12), "op": "attach-documents", "data": target}
        server.delivered = False
        server.lock = threading.Lock()
        server.done = threading.Event()
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            if not server.done.wait(timeout):
                raise RuntimeError("No attachment result. Check the original form before retrying. Verify the extension is enabled or click its toolbar icon to check for a request.")
            result = server.result
        finally:
            server.shutdown()
            worker.join()
    if "error" in result or not isinstance(result.get("receipts"), list):
        raise RuntimeError(result.get("error", "The extension did not report the upload."))
    return result["receipts"]


def attach(store, args):
    config_path = store.directory / "attachment-bridge.json"
    if not config_path.is_file():
        raise ProfileError("Build and load the local attachment extension first.")
    active = load_state(store.directory / "active-draft.json")["active"]
    if not active or (active["tab_id"], active["url"]) != (str(args.tab_id), clean_url(args.url)):
        raise ValueError("The tab and URL must match the active draft.")
    saved_documents = store.read_module("documents")["fields"]
    payloads, receipts = [], []
    for label, value, is_cover in (
        (args.resume_field, saved_documents.get("resume"), False),
        (args.cover_letter_field, args.cover_letter, True),
    ):
        if not label:
            continue
        try:
            if not value:
                raise ValueError("Save an approved PDF for this document first.")
            path = Path(value).expanduser().resolve(strict=True)
            if is_cover and not path.is_relative_to(store.directory / "materials"):
                saved = saved_documents.get("cover_letter")
                if not saved or Path(saved).expanduser().resolve() != path:
                    raise ValueError("Use the PDF from the local materials folder or a saved cover letter.")
            payloads.append(pdf_payload(path, label))
        except (OSError, ValueError) as error:
            receipt = str(error) if isinstance(error, ValueError) else "The approved PDF could not be opened."
            receipts.append({"field": label, "status": "blocked", "detail": receipt})
    if payloads:
        receipts.extend(send_to_extension(read_json(config_path), {
            "tab_id": args.tab_id,
            "expected_url": args.url,
            "frame_url": clean_url(args.frame_url) if args.frame_url else None,
            "documents": payloads,
        }))
    return {"receipts": receipts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Generate the Chrome extension in the private data folder.")
    build.add_argument("--port", type=int)
    upload = commands.add_parser("upload", help="Attach PDFs to the active draft.")
    upload.add_argument("--tab-id", type=int, required=True)
    upload.add_argument("--url", required=True, help="The exact observed URL of the application tab")
    upload.add_argument("--frame-url", help="Observed frame origin and path, for an embedded form")
    upload.add_argument("--resume-field")
    upload.add_argument("--cover-letter-field")
    upload.add_argument("--cover-letter", type=Path)
    args = parser.parse_args()
    store = ProfileStore(args.data_dir)
    try:
        if args.command == "build":
            result = build_extension(store, args.port)
        else:
            if bool(args.cover_letter_field) != bool(args.cover_letter):
                parser.error("Provide the cover-letter field and PDF path together.")
            labels = [label for label in (args.resume_field, args.cover_letter_field) if label]
            normalized = {" ".join(label.strip().rstrip("*").casefold().split()) for label in labels}
            if not labels or "" in normalized or len(normalized) != len(labels):
                parser.error("Provide distinct, observed file-field labels.")
            result = attach(store, args)
    except (OSError, ValueError, RuntimeError, ProfileError) as error:
        parser.exit(1, f"Attachment helper: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(int(any(item["status"] == "blocked" for item in result.get("receipts", []))))


if __name__ == "__main__":
    main()
