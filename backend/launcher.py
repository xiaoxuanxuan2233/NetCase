"""Desktop entry point. Opens the local web UI on an ephemeral loopback port."""

import argparse
import asyncio
import json
import socket
import sys
import urllib.request
import webbrowser

import uvicorn

from app.main import create_app


def loopback_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(128)
    sock.setblocking(False)
    return sock


def smoke(url: str) -> None:
    with urllib.request.urlopen(f"{url}/api/health", timeout=5) as response:  # noqa: S310
        health = json.load(response)
    if not health.get("engine_available"):
        raise RuntimeError("健康检查未通过")
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
        page = response.read(128_000)
    if b'id="root"' not in page:
        raise RuntimeError("前端资源未正确打包")


async def launch(port: int, self_test: bool, no_browser: bool) -> None:
    sock = loopback_socket(port)
    address = f"http://127.0.0.1:{sock.getsockname()[1]}"
    config = uvicorn.Config(
        create_app(), log_level="warning", access_log=False,
        loop="asyncio", http="h11", ws="none", lifespan="on",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        for _ in range(100):
            if task.done():
                await task
                raise RuntimeError("本地服务启动失败")
            if server.started:
                break
            await asyncio.sleep(0.1)
        else:
            raise RuntimeError("本地服务启动超时")
        if self_test:
            await asyncio.to_thread(smoke, address)
            print("NetCase 桌面包健康检查通过", flush=True)
        else:
            print(f"NetCase 已启动：{address}\n按 Ctrl+C 退出。", flush=True)
            if not no_browser:
                webbrowser.open(address)
            await task
    finally:
        server.should_exit = True
        if not task.done():
            await task
        sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="NetCase 本地网络诊断")
    parser.add_argument("--port", type=int, default=0, help="本地端口，默认自动分配")
    parser.add_argument("--self-test", action="store_true", help="仅检查桌面包启动与页面")
    parser.add_argument("--no-browser", action="store_true", help="启动但不自动打开浏览器")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("端口必须是 0–65535 之间的整数")
    try:
        asyncio.run(launch(args.port, args.self_test, args.no_browser))
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError) as exc:
        print(f"NetCase 无法启动：{exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
