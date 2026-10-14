"""Bounded, shell-free ICMP and route commands for one requested target."""

import asyncio
import re
import shutil
import sys
import time

from app.models.schemas import ModuleResult


def _arguments(kind: str, host: str) -> list[str] | None:
    if kind == "ping":
        if sys.platform == "win32":
            return ["ping", "-n", "3", "-w", "1000", host]
        if sys.platform == "darwin":
            return ["ping", "-n", "-c", "3", "-W", "1000", host]
        return ["ping", "-n", "-c", "3", "-W", "1", host]
    if sys.platform == "win32":
        return ["tracert", "-d", "-h", "16", "-w", "800", host]
    return ["traceroute", "-n", "-m", "16", "-w", "1", "-q", "1", host]


async def diagnose(kind: str, host: str) -> ModuleResult:
    cmd = _arguments(kind, host)
    if not cmd or shutil.which(cmd[0]) is None:
        return ModuleResult(
            name=kind,
            status="unsupported",
            error_type="TOOL_NOT_FOUND",
            detail=f"系统中没有 {cmd[0] if cmd else kind} 工具。",
        )
    started = time.perf_counter()
    limit = 8 if kind == "ping" else 48
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), limit)
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
            await process.communicate()
            raise
        except TimeoutError:
            if process.returncode is None:
                process.kill()
            await process.communicate()
            return ModuleResult(
                name=kind,
                status="failed",
                error_type="COMMAND_TIMEOUT",
                detail="系统检测工具超过运行时间限制，已停止。",
            )
        text = stdout[:64_000].decode(errors="replace")
        error = stderr[:2000].decode(errors="replace")
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        if kind == "ping":
            # Windows uses time<1ms or 时间=12ms; Linux/macOS use time=12.3 ms.
            samples = [
                float(v.replace(",", "."))
                for v in re.findall(r"(?:time|时间)\s*[=<]\s*([\d.,]+)\s*ms", text, flags=re.I)
            ]
            evidence = {
                "sent": 3,
                "received": len(samples),
                "loss_percent": round((3 - min(3, len(samples))) / 3 * 100, 1),
                "exit_code": process.returncode,
                "raw_excerpt": text[:2500] or error[:1000],
            }
            if samples:
                evidence.update(
                    {
                        "min_ms": min(samples),
                        "avg_ms": round(sum(samples) / len(samples), 1),
                        "max_ms": max(samples),
                    }
                )
                return ModuleResult(
                    name="ping",
                    status="success" if len(samples) == 3 else "warning",
                    duration_ms=elapsed,
                    detail=f"收到 {len(samples)}/3 次 ICMP 回应。",
                    evidence=evidence,
                )
            return ModuleResult(
                name="ping",
                status="warning",
                duration_ms=elapsed,
                error_type="ICMP_NO_REPLY",
                detail="没有解析到 ICMP 回应。可能是目标未响应或 ICMP 被限制。",
                evidence=evidence,
            )
        hops = []
        for line in text.splitlines():
            matched = re.match(r"^\s*(\d{1,2})\s+(.{1,300})$", line)
            if matched and 1 <= int(matched[1]) <= 16:
                hops.append({"hop": int(matched[1]), "raw": matched[2].strip()})
        return ModuleResult(
            name="traceroute",
            status="success" if hops else "warning",
            duration_ms=elapsed,
            error_type=None if hops else "ROUTE_NO_HOPS",
            detail=f"系统工具记录了 {len(hops)} 跳。中间节点无回应不等于最终目标失败。",
            evidence={
                "hops": hops,
                "exit_code": process.returncode,
                "raw_excerpt": text[:2500] or error[:1000],
            },
        )
    except (OSError, ValueError) as exc:
        return ModuleResult(
            name=kind,
            status="unsupported",
            error_type="COMMAND_UNAVAILABLE",
            detail="系统检测工具不可用或权限不足。",
            evidence={"exception": type(exc).__name__},
        )
