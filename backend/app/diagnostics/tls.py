import asyncio
import socket
import ssl
import time
from datetime import UTC, datetime

from app.models.schemas import ModuleResult


async def diagnose(host: str, port: int, address: str | None, timeout: float) -> ModuleResult:
    if not address:
        return ModuleResult(
            name="tls",
            status="unsupported",
            error_type="TCP_REQUIRED",
            detail="没有可连接的地址，无法继续 TLS 握手。",
        )
    start = time.perf_counter()
    try:
        context = ssl.create_default_context()
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(
                address,
                port,
                family=family,
                ssl=context,
                server_hostname=host,
                ssl_handshake_timeout=timeout,
            ),
            timeout=timeout + 1,
        )
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        session = writer.get_extra_info("ssl_object")
        certificate = session.getpeercert() if session else {}
        valid_to = certificate.get("notAfter")
        valid_from = certificate.get("notBefore")
        evidence = {
            "address": address,
            "port": port,
            "tls_version": session.version() if session else None,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "subject": str(certificate.get("subject", ""))[:500],
        }
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=1)
        except (OSError, TimeoutError):
            pass
        remaining = None
        if valid_to:
            remaining = (
                datetime.fromtimestamp(ssl.cert_time_to_seconds(valid_to), UTC) - datetime.now(UTC)
            ).days
        return ModuleResult(
            name="tls",
            status="success",
            duration_ms=elapsed,
            evidence=evidence,
            detail=f"TLS 握手成功，证书验证通过；协商 {evidence['tls_version']}。"
            + (f"证书约 {remaining} 天后到期。" if remaining is not None else ""),
        )
    except ssl.SSLCertVerificationError as exc:
        message = str(exc).lower()
        if "expired" in message:
            code, detail = "TLS_CERT_EXPIRED", "证书已过期，系统拒绝建立可信连接。"
        elif "hostname" in message or "ip address mismatch" in message:
            code, detail = "TLS_NAME_MISMATCH", "证书上的名称与目标主机不匹配。"
        else:
            code, detail = "TLS_CHAIN_UNTRUSTED", "证书链无法通过系统信任验证。"
        return ModuleResult(
            name="tls",
            status="failed",
            error_type=code,
            detail=detail,
            evidence={
                "address": address,
                "verify_code": getattr(exc, "verify_code", None),
                "verify_message": str(getattr(exc, "verify_message", exc))[:300],
            },
        )
    except (ssl.SSLError, OSError, TimeoutError) as exc:
        reason = "TLS_TIMEOUT" if isinstance(exc, TimeoutError) else "TLS_HANDSHAKE_FAILED"
        return ModuleResult(
            name="tls",
            status="failed",
            error_type=reason,
            detail="TLS 握手未成功，可能与协议、网络链路或服务器配置有关。",
            evidence={"address": address, "exception": type(exc).__name__},
        )
