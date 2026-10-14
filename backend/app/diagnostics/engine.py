"""One target, bounded module execution, explicit dependencies and progress."""

import ipaddress
import logging
import platform
import time
from datetime import UTC, datetime
from uuid import uuid4

from app.analyzers.rules import RULE_VERSION, analyze
from app.core.targets import addresses_allowed
from app.diagnostics import commands, dns, http, tcp, tls
from app.diagnostics.target import parse_target
from app.models.schemas import DiagnosisInput, DiagnosisRecord, ModuleResult

ORDER = ["dns", "tcp", "tls", "http", "ping", "traceroute"]
logger = logging.getLogger("netcase")


def selected_modules(request: DiagnosisInput, scheme: str, is_ip: bool) -> list[str]:
    requested = (
        (["dns", "tcp", "tls"] if request.mode == "quick" else ORDER)
        if request.mode != "custom"
        else request.modules or []
    )
    requested = list(requested)
    if not is_ip and any(name != "dns" for name in requested) and "dns" not in requested:
        requested.insert(0, "dns")
    # HTTP targets retain an explicit unsupported TLS step instead of probing port 80 with TLS.
    del scheme
    return [name for name in ORDER if name in requested]


def overall(modules: list[ModuleResult]) -> str:
    statuses = {m.status for m in modules if m.status != "unsupported"}
    return (
        "unsupported"
        if not statuses
        else "failed"
        if "failed" in statuses
        else "warning"
        if "warning" in statuses
        else "success"
    )


async def run(request: DiagnosisInput, on_progress=None) -> DiagnosisRecord:
    target = parse_target(request)
    names = selected_modules(request, target.scheme, target.is_ip)
    results: list[ModuleResult] = []
    start = time.perf_counter()
    addresses: list[str] = [target.host] if target.is_ip else []
    connected: str | None = None
    resolver_details: dict = {}

    for name in names:
        if on_progress:
            on_progress(name, "running", list(results))
        try:
            if (
                name != "dns"
                and addresses
                and not addresses_allowed(addresses, request.allow_local)
            ):
                result = ModuleResult(
                    name=name,
                    status="unsupported",
                    error_type="LOCAL_OPT_IN_REQUIRED",
                    detail="目标包含本地或特殊 IP，须明确允许本地目标检测。",
                )
            elif name == "dns":
                result = await dns.diagnose(
                    target.host,
                    target.is_ip,
                    request.resolver,
                    request.compare_resolver,
                    request.timeout_seconds,
                )
                resolver_details = {
                    "resolver": result.evidence.get("resolver", request.resolver),
                    "server": result.evidence.get("server", "n/a"),
                }
                if not target.is_ip:
                    records = result.evidence.get("records", {})
                    addresses = records.get("A", [])[:4] + records.get("AAAA", [])[:4]
            elif name == "tcp":
                result = await tcp.diagnose(
                    target.host, target.port, addresses, request.timeout_seconds
                )
                connected = next(
                    (
                        a["address"]
                        for a in result.evidence.get("addresses", [])
                        if a["status"] == "success"
                    ),
                    None,
                )
            elif name == "tls":
                result = (
                    await tls.diagnose(
                        target.host,
                        target.port,
                        connected or (addresses[0] if "tcp" not in names and addresses else None),
                        request.timeout_seconds,
                    )
                    if target.scheme == "https"
                    else ModuleResult(
                        name="tls",
                        status="unsupported",
                        detail="HTTP 目标不使用 TLS；需要 HTTPS 才能执行证书验证。",
                    )
                )
            elif name == "http":
                tls_result = next((m for m in results if m.name == "tls"), None)
                if not addresses:
                    result = ModuleResult(
                        name="http",
                        status="unsupported",
                        error_type="DNS_REQUIRED",
                        detail="没有可用 IP 地址，已跳过 HTTP 请求。",
                    )
                elif target.scheme == "https" and tls_result and tls_result.status != "success":
                    result = ModuleResult(
                        name="http",
                        status="unsupported",
                        error_type="TLS_REQUIRED",
                        detail="TLS 验证未通过，已跳过 HTTPS 请求。",
                    )
                else:
                    result = await http.diagnose(
                        target.url,
                        request.timeout_seconds,
                        request.allow_local,
                        target.host,
                        addresses,
                    )
            else:
                if not addresses:
                    result = ModuleResult(
                        name=name,
                        status="unsupported",
                        error_type="DNS_REQUIRED",
                        detail="没有可用 IP 地址，已跳过探测。",
                    )
                else:
                    result = await commands.diagnose(name, addresses[0])
        except Exception as exc:
            # Contain a single module failure; never return a misleading success.
            logger.error("module_failed module=%s error_type=%s", name, type(exc).__name__)
            result = ModuleResult(
                name=name,
                status="failed",
                error_type="MODULE_ERROR",
                detail="本模块出现未预期的错误，请查看本地服务日志。",
                evidence={"exception": type(exc).__name__},
            )
        results.append(result)
        if on_progress:
            on_progress(name, result.status, list(results))
    summary, conclusions = analyze(results)
    families = sorted(
        {"IPv6" if ipaddress.ip_address(a).version == 6 else "IPv4" for a in addresses}
    )
    context = {
        "platform": platform.system(),
        "port": target.port,
        "protocol": target.scheme,
        "address_families": families,
        "resolver": resolver_details,
        "network_label": request.network_label or "未标注",
    }
    if "http" in names:
        context["http_resolution"] = (
            "HTTP 初始目标使用本次 DNS 检测所得地址（IP 目标使用输入地址）；"
            "跨主机重定向会重新解析并检查地址，因此后续响应条件可能不同。"
        )
    return DiagnosisRecord(
        id=str(uuid4()),
        created_at=datetime.now(UTC),
        target=request.target,
        mode=request.mode,
        status=overall(results),
        duration_ms=round((time.perf_counter() - start) * 1000, 1),
        summary=summary,
        rule_version=RULE_VERSION,
        modules=results,
        conclusions=conclusions,
        context=context,
        environment=f"{context['network_label']} / {platform.system()} / {request.resolver}",
        source="runtime",
    )
