"""Bounded DNS wire queries with system-first resolver discovery.

No third-party query is sent unless requested in DiagnosisInput. The tiny wire
reader handles A, AAAA and CNAME including compressed labels and TCP fallback.
"""

import asyncio
import ipaddress
import os
import re
import secrets
import socket
import struct
import subprocess
import time
from pathlib import Path

from app.models.schemas import ModuleResult

PUBLIC_RESOLVERS = {"cloudflare": "1.1.1.1", "google": "8.8.8.8"}
QTYPE = {"A": 1, "AAAA": 28, "CNAME": 5}
TYPE = {value: key for key, value in QTYPE.items()}


def system_nameservers() -> list[str]:
    if os.name == "nt":
        command = (
            "Get-DnsClientServerAddress | Where-Object {$_.ServerAddresses.Count -gt 0} "
            "| Select-Object -ExpandProperty ServerAddresses | Sort-Object -Unique "
            "| ConvertTo-Json -Compress"
        )
        try:
            # Fixed PowerShell program; target names never enter the command.
            result = subprocess.run(  # noqa: S603
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=4,
                check=True,
            )
            import json

            parsed = json.loads(result.stdout)
            values = [parsed] if isinstance(parsed, str) else parsed
            return [str(ipaddress.ip_address(value)) for value in values if value][:4]
        except (OSError, ValueError, subprocess.SubprocessError):
            return []
    try:
        if os.uname().sysname == "Darwin":
            value = subprocess.run(
                ["scutil", "--dns"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=4,
                check=True,
            ).stdout
            candidates = re.findall(r"nameserver\[\d+\]\s*:\s*(\S+)", value)
        else:
            value = Path("/etc/resolv.conf").read_text(encoding="utf-8")
            candidates = re.findall(r"^\s*nameserver\s+(\S+)", value, flags=re.M)
        return list(dict.fromkeys(str(ipaddress.ip_address(v)) for v in candidates))[:4]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def _name(message: bytes, start: int) -> tuple[str, int]:
    labels: list[str] = []
    position = start
    next_position: int | None = None
    visited: set[int] = set()
    for _ in range(128):
        if position in visited or position >= len(message):
            raise ValueError("Invalid DNS name compression")
        visited.add(position)
        length = message[position]
        if length & 0xC0 == 0xC0:
            if position + 1 >= len(message):
                raise ValueError("Short DNS pointer")
            pointer = ((length & 0x3F) << 8) | message[position + 1]
            if next_position is None:
                next_position = position + 2
            position = pointer
            continue
        if length & 0xC0 or length > 63:
            raise ValueError("Invalid DNS label")
        position += 1
        if length == 0:
            return ".".join(labels), next_position or position
        if position + length > len(message):
            raise ValueError("Short DNS label")
        labels.append(message[position : position + length].decode("ascii"))
        position += length
    raise ValueError("DNS compression depth exceeded")


def _decode(message: bytes, transaction: int) -> tuple[int, dict[str, list[str]], bool]:
    if len(message) < 12:
        raise ValueError("Short DNS response")
    ident, flags, questions, answers, _, _ = struct.unpack_from("!HHHHHH", message)
    if ident != transaction or not flags & 0x8000 or questions != 1:
        raise ValueError("Unexpected DNS response")
    position = 12
    _, position = _name(message, position)
    if position + 4 > len(message):
        raise ValueError("Short DNS question")
    position += 4
    found: dict[str, list[str]] = {name: [] for name in QTYPE}
    for _ in range(min(answers, 64)):
        _, position = _name(message, position)
        if position + 10 > len(message):
            raise ValueError("Short DNS record")
        kind, record_class, _, length = struct.unpack_from("!HHIH", message, position)
        position += 10
        if position + length > len(message):
            raise ValueError("Short DNS record data")
        if record_class == 1 and kind in TYPE:
            data = message[position : position + length]
            if kind == 1 and length == 4:
                found["A"].append(str(ipaddress.IPv4Address(data)))
            elif kind == 28 and length == 16:
                found["AAAA"].append(str(ipaddress.IPv6Address(data)))
            elif kind == 5:
                name, _ = _name(message, position)
                found["CNAME"].append(name)
        position += length
    return flags & 0xF, found, bool(flags & 0x200)


def _wire_query(host: str, qtype: str, server: str, timeout: float) -> tuple[int, dict, float]:
    transaction = secrets.randbits(16)
    wire = b"".join(bytes([len(label)]) + label.encode("ascii") for label in host.split("."))
    packet = struct.pack("!HHHHHH", transaction, 0x100, 1, 0, 0, 0) + wire
    packet += b"\0" + struct.pack("!HH", QTYPE[qtype], 1)
    family = socket.AF_INET6 if ":" in server else socket.AF_INET
    started = time.perf_counter()
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(packet, (server, 53))
        message, source = sock.recvfrom(4096)
        if source[0] != server:
            raise ValueError("Unexpected DNS sender")
    code, records, truncated = _decode(message, transaction)
    if truncated:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((server, 53))
            sock.sendall(struct.pack("!H", len(packet)) + packet)

            def read_exact(n: int) -> bytes:
                result = b""
                while len(result) < n:
                    chunk = sock.recv(n - len(result))
                    if not chunk:
                        raise ValueError("Truncated DNS/TCP reply")
                    result += chunk
                return result

            size = struct.unpack("!H", read_exact(2))[0]
            if size > 4096:
                raise ValueError("DNS reply too large")
            code, records, _ = _decode(read_exact(size), transaction)
    return code, records, (time.perf_counter() - started) * 1000


async def _resolve(host: str, servers: list[str], timeout: float) -> dict:
    if not servers:
        return await _system_fallback(host, timeout)
    errors: list[str] = []
    for server in servers:
        try:
            results = await asyncio.gather(
                *(
                    asyncio.to_thread(_wire_query, host, record_type, server, timeout)
                    for record_type in QTYPE
                ),
                return_exceptions=True,
            )
            records: dict[str, list[str]] = {kind: [] for kind in QTYPE}
            codes: list[int] = []
            times: list[float] = []
            for result in results:
                if isinstance(result, BaseException):
                    errors.append(type(result).__name__)
                else:
                    code, values, ms = result
                    codes.append(code)
                    times.append(ms)
                    for kind in QTYPE:
                        records[kind].extend(values[kind])
            if codes:
                return {
                    "server": server,
                    "records": {k: sorted(set(v)) for k, v in records.items()},
                    "rcode": codes[0],
                    "response_ms": round(max(times), 1),
                    "errors": errors,
                }
        except (OSError, ValueError) as exc:
            errors.append(type(exc).__name__)
    return {
        "server": servers[0],
        "records": {},
        "rcode": None,
        "response_ms": None,
        "errors": errors,
    }


async def _system_fallback(host: str, timeout: float) -> dict:
    """Native OS resolution can lack CNAME/RCODE information. Disclose the limit."""
    started = time.perf_counter()
    try:
        infos = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM),
            timeout=timeout,
        )
        a = sorted({info[4][0] for info in infos if info[0] == socket.AF_INET})
        aaaa = sorted({info[4][0] for info in infos if info[0] == socket.AF_INET6})
        return {
            "server": "system-native",
            "records": {"A": a, "AAAA": aaaa, "CNAME": []},
            "rcode": 0,
            "response_ms": round((time.perf_counter() - started) * 1000, 1),
            "errors": [],
            "limit": "CNAME/RCODE unavailable via native resolver",
        }
    except (OSError, TimeoutError) as exc:
        return {
            "server": "system-native",
            "records": {},
            "rcode": None,
            "response_ms": None,
            "errors": [type(exc).__name__],
            "limit": "System resolver error does not identify authoritative RCODE",
        }


async def diagnose(
    host: str, is_ip: bool, resolver: str, compare: str | None, timeout: float
) -> ModuleResult:
    if is_ip:
        return ModuleResult(
            name="dns",
            status="unsupported",
            detail="输入是 IP 地址，无需 DNS 解析。",
            evidence={"address": host},
        )
    primary = await _resolve(
        host,
        system_nameservers() if resolver == "system" else [PUBLIC_RESOLVERS[resolver]],
        timeout,
    )
    evidence = {"resolver": resolver, **primary}
    if compare and compare != resolver:
        secondary = await _resolve(host, [PUBLIC_RESOLVERS[compare]], timeout)
        primary_ips = set(
            primary.get("records", {}).get("A", []) + primary.get("records", {}).get("AAAA", [])
        )
        secondary_ips = set(
            secondary.get("records", {}).get("A", []) + secondary.get("records", {}).get("AAAA", [])
        )
        evidence["comparison"] = {
            "resolver": compare,
            **secondary,
            "different_addresses": primary_ips != secondary_ips,
        }
    records = primary.get("records", {})
    addresses = records.get("A", []) + records.get("AAAA", [])
    code = primary.get("rcode")
    if addresses:
        detail = (
            f"获得 {len(records.get('A', []))} 条 A、{len(records.get('AAAA', []))} 条 AAAA 记录。"
        )
        if evidence.get("comparison", {}).get("different_addresses"):
            detail += "不同解析器返回了不同地址，可能与 CDN 或调度策略有关。"
        return ModuleResult(
            name="dns",
            status="success",
            duration_ms=primary["response_ms"],
            detail=detail,
            evidence=evidence,
        )
    if code == 3:
        reason, detail = "DNS_NXDOMAIN", "解析器返回 NXDOMAIN：此域名不存在。"
    elif code == 2:
        reason, detail = "DNS_SERVFAIL", "解析器返回 SERVFAIL：此次查询未能得到有效答复。"
    elif code is None:
        reason, detail = "DNS_TIMEOUT", "DNS 服务器未响应或系统解析失败。"
    elif code == 0:
        reason, detail = "DNS_NO_ADDRESS", "查询成功，但没有获得 A 或 AAAA 地址。"
    else:
        reason, detail = "DNS_ERROR", f"解析器返回错误代码 {code}。"
    return ModuleResult(
        name="dns",
        status="warning" if code == 0 else "failed",
        duration_ms=primary["response_ms"],
        error_type=reason,
        detail=detail,
        evidence=evidence,
    )
