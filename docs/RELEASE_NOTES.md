# NetCase v0.1.0 Preview 2

| 平台 / Platform | 下载 / Download |
| --- | --- |
| Windows x64 | [EXE](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-windows-x64.exe) |
| macOS Apple Silicon | [DMG](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-macos-arm64.dmg) |
| macOS Intel | [DMG](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-macos-x64.dmg) |
| Linux x64 | [AppImage](https://github.com/xiaoxuanxuan2233/NetCase/releases/download/v0.1.0-preview.2/NetCase-0.1.0-preview.2-linux-x64.AppImage) |

NetCase 是本地网络诊断工具，提供 DNS、TCP、TLS、HTTP、Ping 和路由追踪，支持中文解释、历史对比及脱敏报告。无需账号、云服务或单独安装 Python / Node.js。

NetCase checks DNS, TCP, TLS, HTTP, Ping, and routes, with Chinese explanations, local history, comparisons, and redacted reports. No account, cloud service, or separate Python / Node.js installation is required.

## 运行 / Run

- **Windows**：双击 EXE。Open the downloaded EXE.
- **macOS**：打开 DMG，将 NetCase 拖入 Applications 后启动。Open the DMG, drag NetCase into Applications, then launch it.
- **Linux**：赋予 AppImage 执行权限后运行。Make the AppImage executable, then run it:

  ```bash
  chmod +x NetCase-0.1.0-preview.2-linux-x64.AppImage
  ./NetCase-0.1.0-preview.2-linux-x64.AppImage
  ```

macOS 和 Linux 会显示一个启动控制窗口，并打开浏览器。关闭控制窗口或选择“退出 NetCase”会停止服务；历史记录留在用户数据目录。Closing the desktop controller stops the local service; history remains in your user data directory.

Windows 程序未签名；macOS 应用仅做临时签名，未经 Developer ID 签名及 Apple 公证。Linux 包在 Ubuntu 22.04 上构建，图形窗口需要桌面环境。若 FUSE 不可用，可加 `--appimage-extract-and-run` 运行；无图形环境可再加 `--no-gui`。

Windows binaries are unsigned. macOS apps are ad-hoc signed, without Developer ID signing or Apple notarization. Linux builds target Ubuntu 22.04+ compatible glibc environments. Use `--appimage-extract-and-run` when FUSE is unavailable, and `--no-gui` for terminal use.

旧 ZIP 和 tar.gz 仍保留在附件中，SHA-256 校验文件与各安装包一起提供。Earlier folder archives remain available, alongside checksums for each download.

## Preview 2 修复 / Fixes

- 自定义 TLS 检测与其他连接模块统一执行本地地址访问控制。Custom TLS checks respect local-address opt-in.
- 脱敏 JSON 报告可以重新导入，已移除的数据不可恢复。Redacted JSON reports can be imported without restoring removed data.
- HTTP 首次连接沿用本次 DNS 的地址；跨主机重定向单独解析和校验。Initial HTTP requests use the diagnosis DNS results; cross-host redirects are resolved and checked separately.

## 验证与限制 / Validation and limits

DMG 经过挂载、复制和独立目录运行检查；AppImage 经过独立目录的 extract-and-run 检查。两者都验证本地 API、网页资源、控制窗口启动和退出。各平台执行单元测试、Lint、TypeScript 检查和前端构建。真实网络与系统安全提示仍需在实际设备上验证。

DMG checks mount and relocate the app. AppImage checks use extract-and-run from an isolated directory. Both verify the API, web UI, desktop startup, and shutdown. Native runners also run tests, lint, TypeScript checks, and the frontend build. Real network conditions and downloaded-file security prompts need testing on actual devices.

每次只诊断用户指定的单个目标。公开 DNS 和本地目标需要主动选择；HTTP 只读取诊断所需的响应头，最多跟随五次重定向。Ping 和路由追踪依赖系统工具与权限。

Only one explicit target is diagnosed per job. Public resolvers and local addresses require opt-in. HTTP checks headers with at most five redirects. Ping and traceroute depend on OS tools and permissions.

Windows EXE build source: `e715e0f06a3c5bd3ed6cdc68199e8aeaf871e887`.
