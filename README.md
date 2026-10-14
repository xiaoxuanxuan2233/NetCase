# NetCase

[⬇ Windows x64 软件包直链](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.1/NetCase-0.1.0-preview.1-windows-x64.zip) · [其他平台下载与发布说明](https://github.com/xiaoxuanxuan2233/NetCase/releases/tag/v0.1.0-preview.1)

> 上述链接仅在 GitHub 原生构建和预发布成功后可用；请以 Release 页面实际附件为准。

**Understand your network, not just test it.** 让网络故障变得可观察、可解释、可追踪。

NetCase 是本地运行的单目标网络诊断工具。它按 DNS、TCP、TLS、HTTP、Ping 和路由追踪呈现实际测到的证据，再用可阅读的中文规则解释结果。无需账号、云服务或 Docker；默认只监听 `127.0.0.1`。

> 当前是预发布阶段。自动化测试不能替代 Windows/macOS 实机网络验收。请勿把单次结果作为网络故障的最终归因。

## 它解决什么问题

一个网页打不开时，“能不能 Ping 通”只回答了很小一部分。NetCase 分别记录 DNS 能否给出地址、指定端口能否建立 TCP、TLS 证书和握手是否通过、HTTP 有没有返回状态码。它把测量与推测分开：你可以看到第一条通俗结论，展开关键耗时与地址族，最后查看原始技术证据。适合个人用户、网络学习者和 IT 运维人员在自己的设备上排查一个明确目标。

例如 DNS 成功、TCP 可达、TLS 失败时，报告会说明 HTTPS 安全连接未成功，并给出证书或协议方向的排查建议；它不会未经证据就断言有人攻击。历史对比会显示 DNS 解析器、网络备注、地址族、端口与时间等条件差异，方便你观察更换网络前后的变化。

**界面**：概览、诊断配置、进度、分层结果、历史、两次对比与设置。浅色/深色主题、收藏目标和草稿都可实际使用。没有历史时不伪造统计图或测速数据。

## 下载桌面软件

便携版解压即可运行，无需另外安装 Python、Node.js 或 Docker。不要只把单个 EXE 从压缩包中取出；它需要旁边的 `_internal` 目录。首次启动会打开默认浏览器，后台只监听自动分配的 `127.0.0.1` 端口。关闭程序进程即停止服务。

| 系统 | 下载 | 启动方式 |
| --- | --- | --- |
| Windows x64 | [ZIP 直链](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.1/NetCase-0.1.0-preview.1-windows-x64.zip) | 完整解压，双击 `NetCase/NetCase.exe` |
| macOS Intel | [ZIP 直链](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.1/NetCase-0.1.0-preview.1-macos-x64.zip) | 完整解压，在终端运行 `NetCase/NetCase` |
| macOS Apple Silicon | [ZIP 直链](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.1/NetCase-0.1.0-preview.1-macos-arm64.zip) | 完整解压，在终端运行 `NetCase/NetCase` |
| Linux x64 | [tar.gz 直链](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.1/NetCase-0.1.0-preview.1-linux-x64.tar.gz) | 解压后运行 `NetCase/NetCase` |

这是便携式程序文件夹，不是 Windows 安装器或已签名的 macOS App。预发布版本没有 Windows 代码签名和 Apple 公证；Linux 初始目标为 Ubuntu 22.04 或更新的兼容 glibc 环境。每个平台的包在同系统 GitHub runner 上构建，并以本地 API 与首页自检作为上传门槛；真实网络行为仍需用户实机反馈。

Release 附件同时提供每个压缩包的 `.sha256` 文件，可用 Windows 的 `Get-FileHash` 或 macOS/Linux 的 `shasum -a 256` 核对下载文件。项目不会要求关闭杀毒软件或绕过系统保护。

## 功能

- **概览**：真实历史统计、最近检测、常用目标与草稿；无记录时显示空状态。
- **新建诊断**：Quick / Full / Custom，系统 DNS 默认，公开 DNS 显式选择，本地目标显式允许；异步进度和有限时长。
- **结果**：中文解释、分模块指标、原始证据、用户备注。
- **历史**：域名与时间筛选、详情、删除、两次记录对比，提示网络环境和检测条件差异。
- **设置**：主题、超时、默认模式与模块、脱敏 JSON 导出、清空历史、存储位置说明。
- **报告**：单次 Markdown、JSON、HTML；脱敏后仍需人工复查。JSON 导入会标记为“用户导入”。

检测失败不会自动归因为封锁、污染或中间人攻击。HTTP 403/429/5xx 表示已收到服务端响应；中间路由节点不回应也不能证明终点不可达。

## 截图

尚未提供产品截图。截图必须从真实运行界面采集；当前环境不能完成受控浏览器视觉验收，发布时补充实际截图。

## 从源码运行（开发者）

Python **3.12+**、[uv](https://docs.astral.sh/uv/getting-started/installation/)、Node.js **22.12+** 与 npm；第一次安装依赖需要联网。无需数据库服务器。打开本地界面无需浏览器插件。

### Windows（PowerShell）

```powershell
# 在项目根目录
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
# 浏览器打开 http://127.0.0.1:8000
```

如果 PowerShell 中已允许脚本执行，可运行 `.\scripts\start.ps1`。默认端口占用时使用 `-Port 8001`。Windows 的 `ping` 和 `tracert` 应为系统自带工具；受操作系统权限或防火墙影响，ICMP 可能不可用。

### macOS / Linux

```bash
bash scripts/start.sh
# 浏览器打开 http://127.0.0.1:8000
```

可将端口作为参数传给 `start.sh`，例如 `bash scripts/start.sh 8001`。Ping / traceroute 依赖系统工具；不存在或无权限时模块会返回不可用提示。

**开发模式**：在 `backend` 运行 `uv sync --locked` 和 `uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log`；另在 `frontend` 运行 `npm ci`、`npm run dev`，打开 `http://127.0.0.1:5173`。Vite 只绑定本机，代理 `/api` 到 8000。启动脚本会构建前端，然后由 FastAPI 同端口提供页面。禁用 HTTP access log 可避免把搜索条件等 URL 查询串写进终端日志。

## 第一次使用

输入 `example.com`，选择“快速检查”，点击“开始诊断”。DNS 查询系统解析器，TCP 检查 443 端口，TLS 严格验证证书。选择“完整诊断”才会加入 HTTP、Ping 和路由追踪。若要诊断私网设备，明确勾选本地目标允许；只诊断你有权访问的设备。公开 DNS 和对比 DNS 只有主动选中才查询第三方。

结果中的“确认”只指相关观测已获得证据；“较可能”是有依据的可能原因；“无法判断”保留不确定性。HTTP 的耗时仅到响应头，不包含正文和伪造的分阶段 TTFB。

## 本地数据与隐私

Windows 默认 `%LOCALAPPDATA%\NetCase\netcase.db`；macOS/Linux 默认 `~/.local/share/netcase/netcase.db`，遵循 `XDG_DATA_HOME`。`NETCASE_DATA_DIR` 可更改目录。SQLite 保存记录、收藏、草稿、设置；无遥测、无账号、无自动上传。浏览器另缓存主题，方便首屏配色。导出的报告过滤 URL 查询串、敏感字段与非公网 IP，但备注及公开目标可能仍敏感，分享前检查。

## 架构与范围

`frontend/` 是 React、TypeScript、Vite；`backend/app/` 是 FastAPI、Pydantic、asyncio、SQLite/SQLAlchemy。`diagnostics/` 只负责测量，`analyzers/` 负责规则，`reports/` 负责脱敏；前端调用同源 `/api`。设计与 API 详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，安全边界见 [SECURITY.md](SECURITY.md)。

本版不做周期监控、网段扫描、批量端口扫描、AI 分析或 MCP。DNS 使用自带的有限 UDP/TCP 查询实现，不依赖 dnspython；系统 DNS 发现和解析器行为跨平台尚需实机验证。HTTP 仅实现 HTTP/1.1 响应头探测（不下载正文），最多五次重定向；没有浏览器行为模拟。每次最多两个并行任务，任务总上限 90 秒。界面截图、Windows/macOS 实测和正式稳定版标签仍待完成。

想理解每个模块的代码与网络原理，可以按 [docs/LEARNING.md](docs/LEARNING.md) 逐步阅读。依赖许可证的初步检查见 [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md)。

## 测试

```bash
cd backend
uv sync --locked
uv run --no-sync ruff check app tests
uv run --no-sync ruff format --check app tests
uv run --no-sync pytest -q
cd ../frontend
npm ci
npm run lint
npm test
npm run build
```

单元测试以 Mock 和本地 ASGI 请求为主，不依赖公网。CI 在 GitHub Actions 执行同等检查。真实网络与系统 ICMP 的差异需在目标操作系统手工验证。

## 后续与贡献

先完成 Windows/macOS 实机验收、可核验截图和 v0.1.0 发布；后续可考虑延迟趋势、健康检查、DNS 变化提醒。贡献前阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，发现安全问题阅读 [SECURITY.md](SECURITY.md)。项目暂选 MIT，**发布前请项目所有者确认最终许可证**。[English README](README_EN.md)。
