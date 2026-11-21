#!/usr/bin/env python3
"""Optional stdio MCP interface for the local Job Applications profile."""

import argparse
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from applicant_profile import ProfileStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    store = ProfileStore(parser.parse_args().data_dir)
    server = FastMCP("job-applications-profile")

    @server.tool()
    def list_profile_modules() -> list[dict[str, Any]]:
        """List local sections and counts without showing the saved values."""
        return store.list_modules()

    @server.tool()
    def read_profile_module(module_id: str) -> dict[str, Any]:
        """Read one section of the applicant's local profile when needed for their request."""
        return store.read_module(module_id)

    @server.tool()
    def upsert_profile_module(module_id: str, fields: dict[str, Any], title: str | None = None) -> dict[str, Any]:
        """Add or update user-confirmed fields in one section and regenerate the local page."""
        change = {"id": module_id, "fields": fields}
        if title is not None:
            change["title"] = title
        return store.upsert(change)

    @server.tool()
    def open_profile_page() -> dict[str, Any]:
        """Regenerate and open the applicant's private local webpage."""
        return store.open()

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
