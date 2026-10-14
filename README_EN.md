# NetCase

[Download Windows x64](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.1/NetCase-0.1.0-preview.1-windows-x64.zip) · [All platform packages](https://github.com/xiaoxuanxuan2233/NetCase/releases/tag/v0.1.0-preview.1)

> These links become available after the native builds and preview release succeed.

**Understand your network, not just test it.** A local-first, single-target network diagnosis workspace with evidence-based Chinese explanations.

> Source preview: automated tests and build have run in a Linux container. Windows and macOS real-network behavior and actual product screenshots still need manual acceptance before a release tag.

## Features

Dashboard with real history metrics and honest empty states; Quick / Full / Custom DNS, TCP, TLS, HTTP, Ping and traceroute checks; progress, conclusions, evidence, history filters, two-record comparison, notes, effective theme and timeout settings, local deletion, and redacted Markdown / JSON / HTML reports. Public DNS and local-network probing require explicit user selection. Imported JSON reports are marked as imported.

DNS variance is not proof of poisoning; failed TCP is not proof of firewall filtering. HTTP 403/429/5xx means an HTTP response was received. Conclusions attach evidence and next steps.

## Portable desktop packages

Download the full ZIP/tar.gz folder from the release page. Windows: extract everything and launch `NetCase/NetCase.exe`; macOS or Linux: run `NetCase/NetCase` in Terminal. Python, Node.js and Docker are not required for the portable package. The local UI opens in your browser on an automatically chosen loopback port. The Windows binary is unsigned, macOS is not notarized, and Linux initially targets a compatible Ubuntu 22.04+ glibc environment. The platform package self-test checks the local API and UI; real network behavior still needs platform-specific acceptance.

## Requirements and start from source

Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js 22.12+ and npm. First-time dependency installation requires internet. Docker, cloud services, and accounts are not required.

Windows PowerShell, from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

macOS/Linux:

```bash
bash scripts/start.sh
```

Open `http://127.0.0.1:8000`. Pass `-Port 8001` on Windows or `8001` on macOS/Linux to change the port. Development: run `uv sync --locked` and `uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log` from `backend`, then `npm ci && npm run dev` from `frontend` and open port 5173. Access logging is disabled to avoid writing URL query strings to terminal logs.

Try `example.com` with Quick Check to observe system DNS, TCP 443 and strict TLS validation. Full Diagnosis adds HTTP, Ping and traceroute. Only opt in to probing a local address you are authorized to diagnose.

## Storage and privacy

SQLite database: `%LOCALAPPDATA%\NetCase\netcase.db` on Windows; `~/.local/share/netcase/netcase.db` on macOS/Linux (honors `XDG_DATA_HOME`). Override the directory with `NETCASE_DATA_DIR`. No telemetry, account, automatic uploads or default third-party resolver. Reports redact URL queries, common sensitive fields, and non-public IPs, but must still be reviewed before sharing.

## Testing

From `backend`: `uv sync --locked`, then `uv run --no-sync ruff check app tests`, `uv run --no-sync ruff format --check app tests`, `uv run --no-sync pytest -q`. From `frontend`: `npm ci`, `npm run lint`, `npm test`, `npm run build`.

Automated tests mock public network probes; real network behavior is platform-dependent. HTTP is an HTTP/1.1 header-only probe with at most five redirects. DNS is a bounded built-in UDP/TCP resolver, and system resolver discovery needs Windows/macOS acceptance. Ping/traceroute depend on system tools and ICMP permissions. No subnet scanning, bulk ports, continuous monitoring, AI, or MCP in this release.

## Project

Architecture and API: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md). Changelog: [CHANGELOG.md](CHANGELOG.md). Actual screenshots will be added after visual acceptance; mockups are not product screenshots. MIT is proposed and requires the owner's final confirmation before publication.
