# NetCase

| Platform / 平台 | Download / 下载 |
| --- | --- |
| Windows x64 | [EXE](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-windows-x64.exe) |
| macOS Apple Silicon | [ZIP](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-macos-arm64.zip) |
| macOS Intel | [ZIP](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-macos-x64.zip) |
| Linux x64 | [tar.gz](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-linux-x64.tar.gz) |

[简体中文](README.md)

**Understand your network, not just test it.**  
*看清网络问题出在哪一步。*

NetCase is a local network troubleshooting tool for DNS, TCP, TLS, HTTP, Ping, and traceroute. It provides Chinese explanations, diagnosis history, comparisons, and shareable reports. No account or cloud service is required.

NetCase 用来排查网站访问问题，分别检查 DNS、TCP、TLS 和 HTTP，并给出中文说明。支持 Ping、路由追踪、历史对比和报告导出。无需注册账号，诊断记录保存在本机。

## Run NetCase

Current release: **v0.1.0-preview.2**. Run the Windows EXE directly; extract the full archive on macOS / Linux. Python, Node.js, and Docker are not required for these packages.

- **Windows:** open the downloaded EXE.
- **macOS / Linux:** run `NetCase/NetCase` in Terminal.

NetCase opens your browser and listens only on `127.0.0.1`. Exiting the program stops the local service. The Windows EXE extracts its bundled components before opening the browser. On macOS / Linux, keep the entire extracted folder.

Windows binaries are unsigned; macOS binaries are not notarized. Linux packages target Ubuntu 22.04+ compatible glibc environments. SHA-256 checksum files are available on the [release page](https://github.com/xiaoxuanxuan2233/NetCase/releases/tag/v0.1.0-preview.2).

## Run a diagnosis

1. Enter a domain, IP address, or full URL, such as `example.com`.
2. Choose a mode and start the diagnosis.
3. Read the explanation, then expand metrics and evidence. Add notes, export a report, or compare two records in History.

| Mode | Checks |
| --- | --- |
| Quick | DNS, TCP, TLS |
| Full | Adds HTTP, Ping, and traceroute |
| Custom | Select modules; domain-based connection checks also run DNS |

The system DNS resolver is used by default. Public resolver comparisons and local-address probing require explicit selection.

## What it checks

| Module | Results |
| --- | --- |
| DNS | A, AAAA, CNAME records, response times, errors, and resolver differences |
| TCP | Connectivity, timing, and errors for individual IPv4 / IPv6 addresses |
| TLS | Handshake, protocol version, certificate dates, and validation errors |
| HTTP | Status, redirects, final URL, selected headers, and request time |
| Ping | ICMP replies, latency, and packet loss |
| Traceroute | Hops and timeouts |

History supports target and time filters and two-record comparisons. Reports are available as Markdown, JSON, and HTML. Settings control the theme, timeout, and default modules.

## Reading the results

Each module checks a different step. If DNS and TCP succeed but TLS fails, the HTTPS connection was not established. HTTP 503 means a server response was received and the website's service state needs further investigation.

Conclusions distinguish observations (确认), supported possibilities (较可能), and insufficient evidence (无法判断). Different DNS answers can come from CDNs or load balancing. A timeout alone does not prove firewall filtering, and a silent intermediate hop does not mean the destination is unreachable.

Initial HTTP requests use the addresses from the diagnosis's DNS results. Redirects to another hostname are resolved and checked separately. When comparing records, consider the network, resolver, address family, port, and time of each check.

## Data and privacy

History, notes, favorites, drafts, and settings stay in a local SQLite database. There is no telemetry or automatic upload.

| Platform | Default database |
| --- | --- |
| Windows | `%LOCALAPPDATA%\NetCase\netcase.db` |
| macOS / Linux | `~/.local/share/netcase/netcase.db`, honoring `XDG_DATA_HOME` |

Set `NETCASE_DATA_DIR` to change the directory. Settings provides data export and history deletion.

Exports remove or replace URL queries, common sensitive fields, and non-public IP addresses. Review targets and notes before sharing. **Redaction is irreversible:** importing JSON stores only the redacted snapshot and marks it as imported. Hidden IP targets become `redacted.invalid`; importing does not restore the original data or run a new diagnosis.

## Run from source

Requires Python **3.12+**, [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js **22.12+**, and npm. Installing dependencies for the first time requires internet access.

Download or clone the source, then run from the repository root:

**Windows PowerShell**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

**macOS / Linux**

```bash
bash scripts/start.sh
```

Open `http://127.0.0.1:8000`. If the port is in use, add `-Port 8001` on Windows or run `bash scripts/start.sh 8001` on macOS / Linux.

<details>
<summary>Development and test commands</summary>

Backend:

```bash
cd backend
uv sync --locked
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Frontend, in a separate terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite forwards `/api` requests to the local backend.

Backend checks:

```bash
cd backend
uv run --no-sync ruff check app tests
uv run --no-sync ruff format --check app tests
uv run --no-sync pytest -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm test
npm run build
```

Tests use mocks and local requests without depending on public network access. GitHub Actions runs the lint, tests, type check, and build.

</details>

## Current limits

- One target per diagnosis, up to two concurrent jobs, and a 90-second limit per job.
- HTTP checks HTTP/1.1 response headers and follows at most five redirects. Timing ends at the response headers; it does not provide per-stage timings or simulate a browser.
- Ping and traceroute depend on system tools and permissions. Behavior varies by operating system and network.
- Periodic monitoring, subnet scanning, bulk port checks, AI analysis, and MCP are not included.

## Development and contributions

The frontend uses React, TypeScript, and Vite. The backend uses FastAPI, Pydantic, asyncio, and SQLite/SQLAlchemy. Probes, analysis rules, and report exports live in separate modules.

[Architecture and API](docs/ARCHITECTURE.md) · [Learning guide](docs/LEARNING.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Dependencies and licenses](docs/DEPENDENCIES.md) · [Changelog](CHANGELOG.md) · [MIT License](LICENSE)
