"""Core behavior without public DNS or external websites."""

import asyncio
import ssl
import struct
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.analyzers.rules import analyze
from app.diagnostics import commands, dns, http, tcp, tls
from app.diagnostics.engine import overall, run, selected_modules
from app.diagnostics.target import parse_target
from app.models.schemas import DiagnosisInput, ModuleResult
from app.reports.export import markdown


def test_dns_success_and_difference_is_not_pollution(monkeypatch):
    async def fake(host, servers, timeout):
        answer = "93.184.215.14" if servers[0] == "1.1.1.1" else "93.184.215.15"
        return {
            "server": servers[0],
            "records": {"A": [answer], "AAAA": [], "CNAME": []},
            "rcode": 0,
            "response_ms": 12,
            "errors": [],
        }

    monkeypatch.setattr(dns, "_resolve", fake)
    monkeypatch.setattr(dns, "system_nameservers", lambda: ["192.0.2.53"])
    result = asyncio.run(dns.diagnose("example.com", False, "system", "cloudflare", 1))
    assert result.status == "success"
    assert result.evidence["comparison"]["different_addresses"] is True
    assert "CDN" in result.detail
    summary, conclusions = analyze([result])
    assert summary == "两个解析器返回了不同的 IP 地址。"
    assert "污染" in conclusions[0].knowledge


@pytest.mark.parametrize(
    "rcode,error",
    [(3, "DNS_NXDOMAIN"), (2, "DNS_SERVFAIL"), (None, "DNS_TIMEOUT"), (0, "DNS_NO_ADDRESS")],
)
def test_dns_failures_are_distinct(monkeypatch, rcode, error):
    async def fake(*_):
        return {
            "server": "192.0.2.53",
            "records": {"A": [], "AAAA": [], "CNAME": []},
            "rcode": rcode,
            "response_ms": None,
            "errors": [],
        }

    monkeypatch.setattr(dns, "_resolve", fake)
    monkeypatch.setattr(dns, "system_nameservers", lambda: ["192.0.2.53"])
    result = asyncio.run(dns.diagnose("example.invalid", False, "system", None, 1))
    assert result.error_type == error
    assert result.status == ("warning" if rcode == 0 else "failed")


@pytest.mark.parametrize(
    "exception,reason", [(TimeoutError(), "TCP_TIMEOUT"), (ConnectionRefusedError(), "TCP_REFUSED")]
)
def test_tcp_classifies_timeout_and_refusal(monkeypatch, exception, reason):
    async def broken(*_, **__):
        raise exception

    monkeypatch.setattr(asyncio, "open_connection", broken)
    result = asyncio.run(tcp.diagnose("example.com", 443, ["93.184.215.14"], 1))
    assert result.status == "failed"
    assert result.error_type == reason
    assert result.evidence["addresses"][0]["error_type"] == reason


def test_tls_certificate_error_stays_strict(monkeypatch):
    async def bad_certificate(*_, **__):
        raise ssl.SSLCertVerificationError("certificate has expired")

    monkeypatch.setattr(asyncio, "open_connection", bad_certificate)
    result = asyncio.run(tls.diagnose("example.com", 443, "93.184.215.14", 1))
    assert result.status == "failed"
    assert result.error_type == "TLS_CERT_EXPIRED"
    assert "过期" in result.detail


def test_http_503_is_a_server_response(monkeypatch):
    async def fake_headers(*_):
        return 503, {"content-type": "text/plain"}

    monkeypatch.setattr(http, "response_headers", fake_headers)
    result = asyncio.run(
        http.diagnose("https://example.com/", 1, False, "example.com", ["93.184.215.14"])
    )
    assert result.status == "warning"
    assert result.error_type == "HTTP_503"
    assert result.evidence["status_code"] == 503
    assert "网站服务" in result.detail


@pytest.mark.parametrize("allow_local", [False, True])
def test_http_rejects_redirect_to_local_network(monkeypatch, allow_local):
    async def fake_addresses(host, *_):
        return ["127.0.0.1"] if host == "localhost" else ["93.184.215.14"]

    async def fake_headers(*_):
        return 302, {"location": "http://localhost/internal"}

    monkeypatch.setattr(http, "addresses", fake_addresses)
    monkeypatch.setattr(http, "response_headers", fake_headers)
    result = asyncio.run(
        http.diagnose("https://example.com/", 1, allow_local, "example.com", ["93.184.215.14"])
    )
    assert result.error_type == "ADDRESS_BLOCKED"
    assert len(result.evidence["redirects"]) == 1


def test_analysis_uses_evidence_and_specific_next_step():
    modules = [
        ModuleResult(name="dns", status="success", detail="A 记录存在。"),
        ModuleResult(name="tcp", status="success", detail="443 可连接。"),
        ModuleResult(
            name="tls", status="failed", error_type="TLS_NAME_MISMATCH", detail="证书名称不匹配。"
        ),
    ]
    summary, conclusions = analyze(modules)
    assert "TCP 可达" in summary
    assert conclusions[0].confidence == "确认"
    assert any("TLS" in item for item in conclusions[0].evidence)
    assert conclusions[0].possible_causes
    assert conclusions[0].next_steps
    assert overall(modules) == "failed"


@pytest.mark.parametrize(
    "payload",
    [
        {"target": "https://alice:secret@example.com/"},
        {"target": "file:///etc/passwd"},
        {"target": "example.com -c 10"},
        {"target": "example.com", "port": 70000},
        {"target": "example.com", "timeout_seconds": 1000},
        {"target": "example.com", "mode": "custom", "modules": ["tcp", "tcp"]},
    ],
)
def test_rejects_malformed_or_unbounded_input(payload):
    with pytest.raises(ValidationError):
        DiagnosisInput.model_validate(payload)


def test_engine_keeps_unsupported_dependency_separate(monkeypatch):
    async def no_address(*_):
        return ModuleResult(
            name="dns",
            status="failed",
            error_type="DNS_NXDOMAIN",
            detail="NXDOMAIN",
            evidence={"records": {"A": [], "AAAA": []}},
        )

    monkeypatch.setattr(dns, "diagnose", no_address)
    result = asyncio.run(run(DiagnosisInput(target="example.invalid", timeout_seconds=1)))
    assert result.status == "failed"
    assert result.modules[0].error_type == "DNS_NXDOMAIN"
    assert result.modules[1].status == "unsupported"
    assert result.conclusions[0].evidence
    assert result.created_at <= datetime.now(UTC)


def test_custom_icmp_also_resolves_before_local_access(monkeypatch):
    async def private(*_):
        return ModuleResult(
            name="dns",
            status="success",
            detail="private",
            evidence={"records": {"A": ["192.168.1.1"], "AAAA": []}},
        )

    async def must_not_run(*_):
        raise AssertionError("Ping should not probe a private address without opt-in")

    monkeypatch.setattr(dns, "diagnose", private)
    monkeypatch.setattr("app.diagnostics.commands.diagnose", must_not_run)
    request = DiagnosisInput(target="router.example", mode="custom", modules=["ping"])
    assert selected_modules(request, "https", False) == ["dns", "ping"]
    result = asyncio.run(run(request))
    assert result.modules[1].error_type == "LOCAL_OPT_IN_REQUIRED"


@pytest.mark.parametrize("module", ["tcp", "tls", "http", "ping", "traceroute"])
def test_all_probes_reject_private_dns_without_opt_in(monkeypatch, module):
    async def private(*_):
        return ModuleResult(
            name="dns",
            status="success",
            detail="private",
            evidence={"records": {"A": ["192.168.1.1"], "AAAA": []}},
        )

    async def must_not_probe(*_, **__):
        raise AssertionError("A private address must not be probed")

    monkeypatch.setattr(dns, "diagnose", private)
    monkeypatch.setattr(
        {"tcp": tcp, "tls": tls, "http": http, "ping": commands, "traceroute": commands}[module],
        "diagnose",
        must_not_probe,
    )
    request = DiagnosisInput(target="router.example", mode="custom", modules=[module])
    result = asyncio.run(run(request))
    assert result.modules[1].status == "unsupported"
    assert result.modules[1].error_type == "LOCAL_OPT_IN_REQUIRED"


def test_custom_tls_local_opt_in_uses_observed_address(monkeypatch):
    async def private(*_):
        return ModuleResult(
            name="dns",
            status="success",
            detail="private",
            evidence={"records": {"A": ["192.168.1.1"], "AAAA": []}},
        )

    observed = []

    async def fake_tls(host, port, address, timeout):
        observed.append((host, port, address))
        return ModuleResult(name="tls", status="success", detail="TLS validated")

    monkeypatch.setattr(dns, "diagnose", private)
    monkeypatch.setattr(tls, "diagnose", fake_tls)
    request = DiagnosisInput(
        target="router.example", mode="custom", modules=["tls"], allow_local=True
    )
    result = asyncio.run(run(request))
    assert result.modules[1].status == "success"
    assert observed == [("router.example", 443, "192.168.1.1")]


def test_mixed_public_private_dns_answer_blocks_all_connections(monkeypatch):
    async def mixed(*_):
        return ModuleResult(
            name="dns",
            status="success",
            detail="mixed",
            evidence={"records": {"A": ["93.184.215.14", "127.0.0.1"], "AAAA": []}},
        )

    async def must_not_probe(*_, **__):
        raise AssertionError("Mixed answer set must be rejected without opt-in")

    monkeypatch.setattr(dns, "diagnose", mixed)
    monkeypatch.setattr(tls, "diagnose", must_not_probe)
    result = asyncio.run(run(DiagnosisInput(target="example.com", mode="custom", modules=["tls"])))
    assert result.modules[1].error_type == "LOCAL_OPT_IN_REQUIRED"


def test_http_pins_initial_dns_but_resolves_redirect_host(monkeypatch):
    looked_up = []
    connected = []

    async def redirected_addresses(host, *_):
        looked_up.append(host)
        return ["93.184.215.15"]

    async def headers(url, address, _):
        connected.append((url, address))
        return (
            (302, {"location": "https://other.example/next"}) if len(connected) == 1 else (200, {})
        )

    monkeypatch.setattr(http, "addresses", redirected_addresses)
    monkeypatch.setattr(http, "response_headers", headers)
    result = asyncio.run(
        http.diagnose("https://example.com/", 1, False, "example.com", ["93.184.215.14"])
    )
    assert result.status == "success"
    assert looked_up == ["other.example"]
    assert [address for _, address in connected] == ["93.184.215.14", "93.184.215.15"]
    assert result.evidence["connected_address"] == "93.184.215.15"


def test_http_does_not_re_resolve_failed_dns(monkeypatch):
    async def must_not_resolve(*_):
        raise AssertionError("The first hop must use the diagnosis DNS result")

    monkeypatch.setattr(http, "addresses", must_not_resolve)
    result = asyncio.run(http.diagnose("https://example.com/", 1, False, "example.com", []))
    assert result.error_type == "ADDRESS_BLOCKED"


def test_engine_http_report_describes_shared_and_redirect_dns_conditions(monkeypatch):
    async def resolved(*_):
        return ModuleResult(
            name="dns",
            status="success",
            detail="public",
            evidence={
                "resolver": "system",
                "server": "192.0.2.53",
                "records": {"A": ["93.184.215.14"], "AAAA": []},
            },
        )

    seen = []

    async def fake_http(url, timeout, allow_local, original_host, addresses):
        seen.append((original_host, addresses))
        return ModuleResult(name="http", status="success", detail="HTTP 200")

    monkeypatch.setattr(dns, "diagnose", resolved)
    monkeypatch.setattr(http, "diagnose", fake_http)
    result = asyncio.run(run(DiagnosisInput(target="example.com", mode="custom", modules=["http"])))
    assert seen == [("example.com", ["93.184.215.14"])]
    assert "跨主机重定向" in result.context["http_resolution"]
    assert "HTTP 地址条件" in markdown(result)


def test_plain_ipv6_target_uses_valid_https_url():
    target = parse_target(DiagnosisInput(target="2001:db8::1", allow_local=True))
    assert target.host == "2001:db8::1"
    assert target.url == "https://[2001:db8::1]/"


def test_dns_wire_parser_reads_address_cname_and_rcode():
    name = b"\x07example\x03com\x00"
    question = name + struct.pack("!HH", 1, 1)
    cname = b"\x05alias\xc0\x0c"
    record_a = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 60, 4) + b"\x5d\xb8\xd7\x0e"
    record_c = b"\xc0\x0c" + struct.pack("!HHIH", 5, 1, 60, len(cname)) + cname
    packet = struct.pack("!HHHHHH", 1234, 0x8180, 1, 2, 0, 0) + question + record_a + record_c
    code, records, truncated = dns._decode(packet, 1234)
    assert code == 0 and not truncated
    assert records["A"] == ["93.184.215.14"]
    assert records["CNAME"] == ["alias.example.com"]
    failure = struct.pack("!HHHHHH", 1234, 0x8183, 1, 0, 0, 0) + question
    assert dns._decode(failure, 1234)[0] == 3
    with pytest.raises(ValueError):
        dns._decode(packet, 9999)
