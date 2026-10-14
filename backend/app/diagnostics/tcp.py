import asyncio
import ipaddress
import socket
import time

from app.models.schemas import ModuleResult


async def diagnose(host: str, port: int, addresses: list[str], timeout: float) -> ModuleResult:
    if not addresses:
        return ModuleResult(
            name="tcp",
            status="unsupported",
            error_type="DNS_REQUIRED",
            detail="没有可用 IP 地址，无法开始 TCP 连接。",
        )

    async def attempt(address: str) -> dict:
        family = socket.AF_INET6 if ipaddress.ip_address(address).version == 6 else socket.AF_INET
        start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(address, port, family=family), timeout
            )
            elapsed = round((time.perf_counter() - start) * 1000, 1)
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), timeout=1)
            del reader
            return {
                "address": address,
                "family": "IPv6" if family == socket.AF_INET6 else "IPv4",
                "status": "success",
                "duration_ms": elapsed,
            }
        except (OSError, TimeoutError) as exc:
            reason = (
                "TCP_TIMEOUT"
                if isinstance(exc, TimeoutError)
                else (
                    "TCP_REFUSED"
                    if isinstance(exc, ConnectionRefusedError)
                    else "NETWORK_UNREACHABLE"
                    if isinstance(exc, OSError) and exc.errno in {101, 10051, 113, 10065}
                    else "TCP_ERROR"
                )
            )
            return {
                "address": address,
                "family": "IPv6" if family == socket.AF_INET6 else "IPv4",
                "status": "failed",
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "error_type": reason,
            }

    results = await asyncio.gather(*(attempt(a) for a in addresses[:8]))
    passed = [r for r in results if r["status"] == "success"]
    status = "success" if len(passed) == len(results) else "warning" if passed else "failed"
    types = {r.get("error_type") for r in results if r.get("error_type")}
    error = sorted(types)[0] if types and not passed else None
    detail = (
        f"{len(passed)}/{len(results)} 个解析地址的 {port} 端口可以建立 TCP 连接。"
        if passed
        else f"已尝试 {len(results)} 个解析地址，均未建立 TCP 连接。"
    )
    return ModuleResult(
        name="tcp",
        status=status,
        error_type=error,
        detail=detail,
        duration_ms=min(r["duration_ms"] for r in passed) if passed else None,
        evidence={"port": port, "addresses": results},
    )
