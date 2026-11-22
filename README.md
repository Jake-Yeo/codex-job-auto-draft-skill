# Job Applications

A portable Codex skill for drafting existing Chrome applications with AutoApply PDF uploads, employer guidance, and a private applicant profile.

1. Install this folder as `job-applications` in `~/.codex/skills/`. Use a clean destination if you already have a personalized skill with that name. Python 3.10 or later is required.
2. Send **`$job-applications setup`**. It opens [the setup page](references/setup.html), asks for the missing applicant information and links, and helps get the PDF upload extension ready.
3. Follow the page to connect Chrome and load the generated AutoApply extension. Then group supplied forms under **jobs** and ask **“Use $job-applications to draft the tabs in my jobs group.”** Review the drafts and submit them yourself.
4. Send **“Use $job-applications to open my profile”** to view it later, or ask the skill to save a correction or add a section.

The local profile page displays the profile MCP’s data. Applicant information, imported files, generated HTML, the built extension, and materials live in `~/.local/share/job-applications/` by default. Publish the reusable skill folder separately from that private data.

You can send `/jobapplication setup` as chat text. To add a menu entry on desktop versions that support custom prompts, copy [jobapplication.md](prompts/jobapplication.md) into `~/.codex/prompts/` and reopen the app. The entry is displayed as **`/prompts:jobapplication`**. Typing `$job-applications setup` also starts the interview.

The profile commands work without a separate server. To use the optional local MCP interface in Codex, register the provided stdio server with your installed skill path. This requires [uv](https://docs.astral.sh/uv/) and Python 3.11 or later.

~~~sh
codex mcp add job-applications-profile -- uv run --no-project \
  --with 'mcp>=1.20,<2' python ~/.codex/skills/job-applications/scripts/profile_mcp.py \
  --data-dir ~/.local/share/job-applications
~~~

Open a new Codex chat after registration. The MCP server and CLI use the same data folder. To copy the files from an older linked profile into that folder, run `python3 scripts/applicant_profile.py import-linked-files` once. From the skill folder, run `python3 scripts/applicant_profile.py setup-help` to open the setup guide, or use `--help` to list the profile commands. The bundled one-page cover-letter renderer can use `uv run --with reportlab --with pypdf` as shown in [the materials guide](references/application-materials.md#cover-letters).
