# 原生软件打包

Windows 使用 PyInstaller 单文件 EXE；macOS 使用 `.app` 加 DMG；Linux x64 使用 AppImage。各平台在对应的原生系统上构建，不交叉编译。

## 启动与退出

macOS / Linux 的入口是 `backend/desktop.py`。Tk 的主线程处理窗口与按钮，另一个线程运行 Uvicorn 和 asyncio 网络服务。窗口定期读取服务状态，因此网络任务不会阻塞窗口。关闭窗口会请求服务退出，最多给正在进行的服务任务三秒收尾；未完成的诊断可能被中断。

窗口只负责打开浏览器、显示本机地址和退出服务。诊断界面仍是 React，接口的 Host / Origin 校验、并发上限和目标地址控制沿用后端实现。Windows 的入口仍是 `backend/launcher.py`。

## 构建

先安装前后端依赖并构建页面：

```bash
cd frontend
npm ci
npm run build
cd ../backend
uv sync --locked
uv pip install --python .venv pyinstaller==6.22.3
```

然后在 `backend` 目录运行：

```bash
uv run --no-sync python ../packaging/build.py
```

macOS 需要系统自带的 `hdiutil`、`codesign`。Linux 构建先安装 `xvfb`、`xauth` 和 `desktop-file-utils`，再从项目根目录执行 `python packaging/fetch_appimage_tools.py`。工具只从 AppImage 官方仓库下载，并核对固定 SHA-256；上游文件变化时会拒绝继续，维护者应检查新版本后再更新摘要。

输出位于 `release-dist/`，每个文件附带 `.sha256` 校验文件。AppImage runtime 的上游许可、来源及摘要放在 `packaging/licenses/AppImage-runtime.txt`，并随 AppImage 分发。

## 自动验收

- 后端单元测试覆盖服务器启动、退出、启动中取消和端口冲突；这些测试使用本地服务器和临时数据库。
- Windows EXE 单独复制到含中文、空格的目录后运行，检查 API 和页面。
- DMG 完成磁盘映像校验和挂载，从映像复制应用到独立目录后检查临时签名、API、页面、图形窗口和退出。
- AppImage 在独立目录通过 `--appimage-extract-and-run` 检查 API、页面和图形窗口；图形测试使用 Xvfb，不要求 CI 配置 FUSE。

`--self-test` 检查打包后的 API 和网页；`--self-test-gui` 走真实的图形启动及退出流程。`--no-gui` 可用于终端，`--no-browser` 允许手动打开本机地址。

这些检查不等同于用户设备上的完整验收。macOS 公证、下载隔离提示、不同 Linux 桌面和 FUSE 配置、真实 ICMP 权限仍需实机验证。不会关闭系统安全验证来通过打包测试。
