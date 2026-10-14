"""Bounded HTTP/1.1 header probe; pin connections to validated DNS addresses."""

import asyncio
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

from app.core.targets import addresses_allowed
from app.models.schemas import ModuleResult

MAX_HEADER = 32 * 1024
MAX_REDIRECTS = 5


def safe_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def parse_url(value: str) -> tuple[str, int, str, str]:
    if len(value) > 2048:
        raise ValueError("URL 太长")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or (parsed.username or parsed.password)
    ):
        raise ValueError("重定向目标必须是没有账号密码的 HTTP(S) URL")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    if "\r" in path or "\n" in path:
        raise ValueError("非法路径字符")
    return host, port, parsed.scheme, path


async def addresses(host: str, port: int, timeout: float) -> list[str]:
    infos = await asyncio.wait_for(
        asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM), timeout
    )
    return list(dict.fromkeys(info[4][0] for info in infos))[:8]


async def response_headers(url: str, address: str, timeout: float) -> tuple[int, dict[str, str]]:
    host, port, scheme, path = parse_url(url)
    context = ssl.create_default_context() if scheme == "https" else None
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(
            address, port, ssl=context, server_hostname=host if context else None
        ),
        timeout + 1,
    )
    try:
        host_field = f"[{host}]" if ":" in host else host
        if port != (443 if scheme == "https" else 80):
            host_field += f":{port}"
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {host_field}\r\n"
            "User-Agent: NetCase/0.1\r\nAccept: */*\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        writer.write(request)
        await asyncio.wait_for(writer.drain(), timeout)
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            if len(buffer) >= MAX_HEADER:
                raise ValueError("响应头超过 32 KiB")
            chunk = await asyncio.wait_for(
                reader.read(min(4096, MAX_HEADER - len(buffer))), timeout
            )
            if not chunk:
                raise ValueError("未收到完整的 HTTP 响应头")
            buffer += chunk
        raw = buffer.split(b"\r\n\r\n", 1)[0].decode("iso-8859-1")
        lines = raw.split("\r\n")
        words = lines[0].split(" ", 2)
        if len(words) < 2 or not words[0].startswith("HTTP/1."):
            raise ValueError("无效的 HTTP/1.1 状态行")
        status = int(words[1])
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        return status, headers
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1)
        except (OSError, TimeoutError):
            pass


async def diagnose(
    url: str, timeout: float, allow_local: bool, original_host: str, initial_addresses: list[str]
) -> ModuleResult:
    started = time.perf_counter()
    redirects: list[dict] = []
    current = url
    try:
        for hop in range(MAX_REDIRECTS + 1):
            host, port, _, _ = parse_url(current)
            # Pin the original host to this diagnosis's DNS evidence; redirects to
            # another host are resolved separately and checked before connecting.
            resolved = (
                initial_addresses if host == original_host else await addresses(host, port, timeout)
            )
            if not addresses_allowed(resolved, allow_local and host == original_host):
                return ModuleResult(
                    name="http",
                    status="failed",
                    error_type="ADDRESS_BLOCKED",
                    detail="目标或重定向包含本地 / 特殊 IP。跨主机重定向不允许访问本地地址。",
                    evidence={"redirects": redirects},
                )
            for address in resolved[:4]:
                try:
                    status, headers = await response_headers(current, address, timeout)
                    break
                except (OSError, TimeoutError):
                    continue
            else:
                raise OSError("No address responded")
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            if status in {301, 302, 303, 307, 308} and headers.get("location"):
                redirects.append({"url": safe_url(current), "status": status})
                if hop == MAX_REDIRECTS:
                    return ModuleResult(
                        name="http",
                        status="warning",
                        error_type="HTTP_REDIRECT_LIMIT",
                        duration_ms=elapsed,
                        detail="重定向超过 5 次，已停止请求。",
                        evidence={"redirects": redirects},
                    )
                current = urljoin(current, headers["location"])
                parse_url(current)  # Reject credentials, scheme and invalid port before connecting.
                continue
            selected = {
                key: value[:300]
                for key, value in headers.items()
                if key in {"server", "content-type", "cache-control"}
            }
            result_status = "success" if 200 <= status < 400 else "warning"
            detail = f"服务器返回 HTTP {status}。"
            if status in {403, 429}:
                detail += "可能涉及访问策略或请求频率，不能据此判定网络故障。"
            elif status >= 500:
                detail += "可能与网站服务状态有关。"
            return ModuleResult(
                name="http",
                status=result_status,
                error_type=f"HTTP_{status}" if result_status != "success" else None,
                duration_ms=elapsed,
                detail=detail,
                evidence={
                    "status_code": status,
                    "final_url": safe_url(current),
                    "redirects": redirects,
                    "headers": selected,
                    "connected_address": address,
                    "resolution_note": (
                        "初始目标沿用本次 DNS 检测结果；跨主机重定向单独解析并校验。"
                    ),
                    "timing_note": "总耗时至响应头；未读取或保存响应正文",
                },
            )
    except (OSError, TimeoutError, ssl.SSLError, ValueError, UnicodeError) as exc:
        reason = (
            "HTTP_TIMEOUT"
            if isinstance(exc, TimeoutError)
            else "HTTP_PROTOCOL"
            if isinstance(exc, ValueError)
            else "HTTP_TLS_FAILED"
            if isinstance(exc, ssl.SSLError)
            else "HTTP_CONNECT_FAILED"
        )
        return ModuleResult(
            name="http",
            status="failed",
            error_type=reason,
            detail="HTTP 请求未成功，请结合 DNS、TCP 和 TLS 结果查看。",
            evidence={
                "request_url": safe_url(current),
                "redirects": redirects,
                "exception": type(exc).__name__,
            },
        )
