"""Small desktop controller for the macOS app and Linux AppImage."""

import argparse
import asyncio
import sys
import threading
import time
import webbrowser

import uvicorn

from app.main import create_app
from launcher import launch, loopback_socket, smoke


class LocalService:
    """Own the server thread so closing the desktop window can stop it cleanly."""

    def __init__(self, port: int = 0) -> None:
        self.port = port
        self.address: str | None = None
        self.error: str | None = None
        self.server: uvicorn.Server | None = None
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._serve, name="netcase-server", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self.server is not None:
            self.server.should_exit = True

    def _serve(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
            self.error = f"本地服务未能启动（{type(exc).__name__}）。"

    async def _run(self) -> None:
        sock = loopback_socket(self.port)
        try:
            config = uvicorn.Config(
                create_app(),
                log_level="warning",
                access_log=False,
                loop="asyncio",
                http="h11",
                ws="none",
                lifespan="on",
                timeout_graceful_shutdown=3,
            )
            self.server = uvicorn.Server(config)
            task = asyncio.create_task(self.server.serve(sockets=[sock]))
            try:
                deadline = time.monotonic() + 10
                while not self.server.started:
                    if self._stop.is_set():
                        self.server.should_exit = True
                        return
                    if task.done():
                        await task
                        raise RuntimeError("Local server stopped before startup")
                    if time.monotonic() > deadline:
                        raise TimeoutError("Local server startup timed out")
                    await asyncio.sleep(0.05)
                self.address = f"http://127.0.0.1:{sock.getsockname()[1]}"
                if self._stop.is_set():
                    self.server.should_exit = True
                await task
            finally:
                self.server.should_exit = True
                if not task.done():
                    await task
        finally:
            sock.close()


def run_desktop(port: int, self_test: bool, no_browser: bool) -> int:
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("NetCase")
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=24)
    frame.grid(sticky="nsew")
    ttk.Label(frame, text="NetCase", font=("TkDefaultFont", 20, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    status = tk.StringVar(value="正在启动本地服务…")
    ttk.Label(frame, textvariable=status, width=50).grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(12, 6)
    )
    address = tk.StringVar()
    ttk.Label(frame, textvariable=address).grid(row=2, column=0, columnspan=2, sticky="w")
    ttk.Label(frame, text="关闭此窗口会停止 NetCase；历史记录保存在本机。").grid(
        row=3, column=0, columnspan=2, sticky="w", pady=(12, 20)
    )
    service = LocalService(port)
    closing = False
    ready = False
    exit_code = 0

    def open_browser() -> None:
        if service.address:
            try:
                if not webbrowser.open(service.address):
                    status.set("请在浏览器中打开下方地址。")
            except OSError:
                status.set("无法自动打开浏览器，请手动打开下方地址。")

    def close() -> None:
        nonlocal closing
        closing = True
        status.set("正在停止本地服务…")
        open_button.configure(state="disabled")
        quit_button.configure(state="disabled")
        service.stop()

    open_button = ttk.Button(frame, text="打开界面", command=open_browser, state="disabled")
    open_button.grid(row=4, column=0, sticky="w")
    quit_button = ttk.Button(frame, text="退出 NetCase", command=close)
    quit_button.grid(row=4, column=1, sticky="e")
    root.protocol("WM_DELETE_WINDOW", close)
    if sys.platform == "darwin":
        root.createcommand("tk::mac::Quit", close)

    def poll() -> None:
        nonlocal ready, exit_code
        if closing and not service.thread.is_alive():
            root.destroy()
            return
        if service.error:
            status.set(service.error)
            exit_code = 1
            if self_test:
                close()
        elif ready and not closing and not service.thread.is_alive():
            status.set("本地服务已停止，请退出后重新打开 NetCase。")
            open_button.configure(state="disabled")
        elif not ready and not closing and service.address:
            ready = True
            address.set(service.address)
            status.set("本地服务已启动。")
            open_button.configure(state="normal")
            if self_test:
                try:
                    smoke(service.address)
                except Exception:
                    exit_code = 1
                close()
            elif not no_browser:
                open_browser()
        root.after(50, poll)

    service.start()
    root.after(50, poll)
    try:
        root.mainloop()
    finally:
        service.stop()
        service.thread.join(timeout=5)
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="NetCase desktop launcher")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-gui", action="store_true", help="Run in a terminal without a window")
    parser.add_argument("--self-test", action="store_true", help="Verify packaged API and UI")
    parser.add_argument(
        "--self-test-gui", action="store_true", help="Verify desktop start and exit"
    )
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535")
    try:
        if args.no_gui or (args.self_test and not args.self_test_gui):
            asyncio.run(launch(args.port, args.self_test, args.no_browser))
        else:
            raise SystemExit(run_desktop(args.port, args.self_test_gui, args.no_browser))
    except KeyboardInterrupt:
        pass
    except Exception:
        if sys.stderr is not None:
            print("NetCase could not start. Try --no-gui from a terminal.", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
