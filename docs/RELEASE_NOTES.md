# NetCase v0.1.0 Preview 2

Windows 版现提供独立 EXE，下载后双击即可运行，不需要解压文件夹或另外安装 Python。启动时会先解压内置组件，然后打开本地界面。macOS 和 Linux 继续使用下方的压缩包。

The Windows download is now a standalone EXE: download and run it directly. It extracts its bundled components at startup and opens the local web UI. macOS and Linux downloads remain folder archives.

Preview 2 fixes three issues from Preview 1: custom TLS checks now respect the local-address opt-in; redacted JSON reports can be imported again; and the first HTTP connection uses the DNS addresses found in the same diagnosis. Cross-host redirects are resolved and checked separately. Use this version instead of Preview 1.

NetCase is a local-first, single-target network troubleshooting workspace. Enter a domain, IP address or HTTP(S) URL to see DNS, TCP, TLS, HTTP and optional ICMP evidence with Chinese explanations. No account, telemetry or cloud server is required.

## Download and run

| Platform | File suffix | Start |
| --- | --- | --- |
| Windows x64 | `windows-x64.exe` | Download the EXE and double-click it. |
| macOS Intel | `macos-x64.zip` | Extract, run `NetCase/NetCase` from Terminal. |
| macOS Apple Silicon | `macos-arm64.zip` | Extract, run `NetCase/NetCase` from Terminal. |
| Linux x64 | `linux-x64.tar.gz` | Extract, run `NetCase/NetCase` from Terminal. |

The launcher opens the web UI in your default browser. It listens only on an automatically chosen `127.0.0.1` port; closing the process stops the service. Your SQLite history remains in the OS user data directory. These are portable programs, not installers. macOS binaries are not Apple notarized, and Windows binaries are not code signed. The Linux binary may need a compatible glibc distribution; Ubuntu 22.04 or newer is the initial target. The earlier Windows ZIP remains available for users who prefer the folder version.

## What is included

Quick Check: system DNS A/AAAA/CNAME, TCP address/port checks and certificate-validating TLS. Full Diagnosis adds bounded HTTP header requests, Ping and traceroute. Custom mode selects modules. History, comparison, notes, settings and redacted Markdown/JSON/HTML export are local. The rule engine distinguishes observations from possible causes and does not automatically accuse a firewall, DNS poisoning or a man-in-the-middle.

## Boundaries

Only one explicitly provided target is diagnosed per job. Optional public resolvers require selection; local and private destinations require opt-in. HTTP uses a strict, header-only HTTP/1.1 probe with at most five redirects. ICMP depends on OS tools and permissions. These native packages receive startup/API/UI smoke checks on their own GitHub-hosted runner, but cross-network reliability and platform UI usability need community testing. Please report the exact OS and a reviewed, redacted report with issues. The source and technical documentation are in the repository.
