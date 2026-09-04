# Milestone 8 — Documentation & Demo Packaging

Date: 2026-09-04

## Completed

- Added the project README with:
  - problem statement and scope
  - quick-start commands
  - console and dashboard demo commands
  - architecture diagram
  - component responsibilities
  - configuration example
  - firmware-concept mapping
  - limitations and documentation links
- Updated the five living documents to identify the implemented MVP state.
- Added links to all milestone reports from the README.
- Added optional JSON Lines persistence for dashboard event history in the gitignored `events.jsonl` file.
- Expanded the sample configuration to five tasks and added dashboard timing controls for slow-motion demonstrations.
- Verified the documented test and run commands during previous milestone validation.

## Main demo

```bash
cd /Users/khushi_makwana/VSCode/EMBEDDED_PROJECT
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python3 -m pytest -q
PYTHONPATH=. python3 -m streamlit run dashboard/app.py
```

The dashboard writes structured events to `events.jsonl` and reloads them on startup, while keeping the live in-memory view for fast rendering.

Dashboard flow:

```text
HEALTHY → inject fault → LATE/STALLED → RECOVERING → HEALTHY
```

## Remaining user-owned packaging actions

- Record and attach a short GIF or video of the dashboard flow.
- Commit and push the final repository history to GitHub.

These actions require the developer's local recording, GitHub credentials, and repository publishing decision, so they are not performed automatically.

The implementation and documentation portions of Milestone 8 are complete; these final distribution artifacts are intentionally left for the project owner.
