# NetCase

| 平台 / Platform | 下载 / Download |
| --- | --- |
| Windows x64 | [EXE](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-windows-x64.exe) |
| macOS Apple Silicon | [DMG](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-macos-arm64.dmg) |
| macOS Intel | [DMG](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-macos-x64.dmg) |
| Linux x64 | [AppImage](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-linux-x64.AppImage) |

[English](README_EN.md)

**看清网络问题出在哪一步。**  
*Understand your network, not just test it.*

NetCase 用来排查网站访问问题，分别检查 DNS、TCP、TLS 和 HTTP，并给出中文说明。支持 Ping、路由追踪、历史对比和报告导出。无需注册账号，诊断记录保存在本机。

NetCase is a local network troubleshooting tool for DNS, TCP, TLS, HTTP, Ping, and traceroute. It provides Chinese explanations, diagnosis history, comparisons, and shareable reports. No account or cloud service is required.

## 运行方式

当前版本：**v0.1.0-preview.2**。无需安装 Python、Node.js 或 Docker。

- **Windows**：双击下载的 EXE。
- **macOS**：打开 DMG，把 NetCase 拖入 Applications，再打开应用。
- **Linux**：在文件属性中允许作为程序执行，再双击 AppImage；也可在终端运行：

  ```bash
  chmod +x NetCase-0.1.0-preview.2-linux-x64.AppImage
  ./NetCase-0.1.0-preview.2-linux-x64.AppImage
  ```

启动后会自动打开浏览器，服务只监听本机 `127.0.0.1`。macOS / Linux 会显示启动控制窗口，关闭它或点击“退出 NetCase”即可停止服务；关闭浏览器不会退出程序。Windows EXE 会先解压内置组件，请等待浏览器打开。

Windows 程序未签名；macOS 应用使用临时签名，尚未完成 Developer ID 签名和 Apple 公证。Linux 包在 Ubuntu 22.04 上构建，需兼容的 glibc 和桌面环境；FUSE 不可用时可加 `--appimage-extract-and-run` 运行。各文件的 SHA-256 校验文件位于 [Release 页面](https://github.com/xiaoxuanxuan2233/NetCase/releases/tag/v0.1.0-preview.2)。

## 开始诊断

1. 输入域名、IP 或完整 URL，例如 `example.com`。
2. 选择检测模式，点击“开始诊断”。
3. 查看结果说明，展开详细指标和原始证据。检测完成后可添加备注、导出报告，或在历史页面选择两条记录比较。

| 模式 | 检测内容 |
| --- | --- |
| 快速检查 · Quick | DNS、TCP、TLS |
| 完整诊断 · Full | 加上 HTTP、Ping 和路由追踪 |
| 自定义 · Custom | 按需选择模块；域名连接检测会先解析 DNS |

默认使用系统 DNS。需要比较公开 DNS 时再手动选择；检测路由器等私网设备时，需勾选“允许本地目标”。

## 能查什么

| 检查项 | 主要结果 |
| --- | --- |
| DNS | A、AAAA、CNAME 记录，响应时间与错误类型，解析器之间的结果差异 |
| TCP | 指定端口是否可连接，各 IPv4 / IPv6 地址的耗时与错误 |
| TLS | 握手结果、协议版本、证书有效期与验证失败原因 |
| HTTP | 状态码、重定向、最终地址、基础响应头和请求耗时 |
| Ping | ICMP 回应、延迟与丢包情况 |
| 路由追踪 | 沿途跳点与超时信息 |

历史记录可按目标和时间筛选，也可以选取两次检测进行比较。报告支持 Markdown、JSON 和 HTML。设置中可以切换深浅色主题、调整超时和默认检测模块。

## 怎样理解结果

DNS、TCP、TLS 和 HTTP 分别检查网站访问的不同环节。DNS 解析成功、TCP 能连接，但 TLS 失败，说明 HTTPS 安全连接未能建立；收到 HTTP 503 则说明服务端已经回应，需要进一步检查网站服务状态。

结论中的“确认”指有直接检测结果支持，“较可能”指根据结果推测的原因，“无法判断”指证据不足。DNS 返回不同 IP 可能来自 CDN 或负载均衡；单凭超时无法判断是否被防火墙拦截，中间路由节点不回应也不代表终点不可达。

HTTP 初始请求沿用本次 DNS 检测的地址，跨主机重定向会重新解析并校验。比较记录时，请同时留意网络、解析器、地址族、端口和检测时间。

## 数据与隐私

历史、备注、收藏、草稿和设置保存在本机 SQLite 数据库中。没有遥测，也不会自动上传诊断记录。

| 系统 | 默认数据库位置 |
| --- | --- |
| Windows | `%LOCALAPPDATA%\NetCase\netcase.db` |
| macOS / Linux | `~/.local/share/netcase/netcase.db`，遵循 `XDG_DATA_HOME` |

可通过 `NETCASE_DATA_DIR` 更改目录，或在设置中导出数据、清理历史。

导出时会删除或替换 URL 查询串、常见敏感字段和非公网 IP，分享前仍需检查目标和备注。**脱敏不可逆**：重新导入 JSON 只保存脱敏后的内容，并标为“用户导入”；隐藏的 IP 目标以 `redacted.invalid` 占位，不会恢复原始信息或重新检测。

## 从源码运行

需要 Python **3.12+**、[uv](https://docs.astral.sh/uv/getting-started/installation/)、Node.js **22.12+** 和 npm。首次安装依赖需要联网。

下载或克隆源码后，在项目根目录执行：

**Windows PowerShell**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

**macOS / Linux**

```bash
bash scripts/start.sh
```

启动后访问 `http://127.0.0.1:8000`。端口被占用时，Windows 脚本可加 `-Port 8001`，macOS / Linux 可运行 `bash scripts/start.sh 8001`。

<details>
<summary>开发模式与测试命令</summary>

后端：

```bash
cd backend
uv sync --locked
uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

在另一个终端启动前端：

```bash
cd frontend
npm ci
npm run dev
```

访问 `http://127.0.0.1:5173`。Vite 会将 `/api` 请求转发到本地后端。

检查后端：

```bash
cd backend
uv run --no-sync ruff check app tests
uv run --no-sync ruff format --check app tests
uv run --no-sync pytest -q
```

检查前端：

```bash
cd frontend
npm run lint
npm test
npm run build
```

测试主要使用 Mock 和本地请求，不依赖外网。GitHub Actions 执行相同的 lint、测试、类型检查和构建。

</details>

## 当前限制

- 每次诊断一个目标，最多同时运行两项任务，单项任务最长 90 秒。
- HTTP 目前只检查 HTTP/1.1 响应头，最多跟随五次重定向；耗时截至收到响应头，不提供分阶段耗时，也不模拟浏览器。
- Ping 和路由追踪依赖系统工具与权限；不同操作系统和网络环境下的行为可能不同。
- 暂不支持周期监控、网段扫描、批量端口检测、AI 分析或 MCP。

## 开发与贡献

前端使用 React、TypeScript 和 Vite，后端使用 FastAPI、Pydantic、asyncio 与 SQLite/SQLAlchemy。网络检测、分析规则和报告导出分别放在独立模块中。

[架构与 API](docs/ARCHITECTURE.md) · [模块学习指南](docs/LEARNING.md) · [打包说明](docs/NATIVE_PACKAGES.md) · [贡献指南](CONTRIBUTING.md) · [安全说明](SECURITY.md) · [依赖与许可证](docs/DEPENDENCIES.md) · [更新记录](CHANGELOG.md) · [MIT License](LICENSE)
