# Contributing to NetCase

Thank you for helping. Open a focused issue first for larger changes. Use a branch, keep probes limited to the explicitly requested single target, and attach tests for meaningful behavior changes. Avoid external-network dependencies in CI and preserve the distinction between observation and inference.

Local checks: `cd backend && uv sync --locked && uv run --no-sync ruff check app tests && uv run --no-sync ruff format --check app tests && uv run --no-sync pytest -q`; then `cd ../frontend && npm ci && npm run lint && npm test && npm run build`. Explain what you tested manually, especially on Windows/macOS. Add Chinese user-facing text, and update English docs when behavior changes. Never attach live credentials, private addresses, or unreviewed reports to an issue.

Architecture and API are described in `docs/ARCHITECTURE.md`; security reports go through `SECURITY.md` rather than public issues. Contributions are subject to the project's final license decision (currently proposed MIT).
