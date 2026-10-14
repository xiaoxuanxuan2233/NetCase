"""Shareable reports deliberately omit credentials, URL queries, and private IPs."""

import html
import ipaddress
import json
import re
from urllib.parse import urlsplit, urlunsplit

from app.models.schemas import DiagnosisRecord

SENSITIVE = re.compile(r"password|passwd|secret|token|cookie|authorization|api[_-]?key", re.I)
ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|secret|token|cookie|api[_-]?key)\s*[:=]\s*[^\s&,;]+"
)
BEARER = re.compile(r"(?i)\bBearer\s+\S+")
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
IPV6 = re.compile(r"(?<![\w:])\[?(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\]?(?![\w:])")


def redact_text(text: str) -> str:
    def replace_url(matched: re.Match) -> str:
        value = matched.group(0)
        try:
            parts = urlsplit(value)
            host = parts.hostname or ""
            if parts.username or parts.password:
                host = "[REDACTED-CREDENTIALS]@" + host
            netloc = (f"[{host}]" if ":" in host else host) + (
                f":{parts.port}" if parts.port else ""
            )
            return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
        except ValueError:
            return "[REDACTED-URL]"

    text = re.sub(r"https?://[^\s<>\"']+", replace_url, text, flags=re.I)
    text = ASSIGNMENT.sub(lambda m: f"{m[1]}=[REDACTED]", text)
    text = BEARER.sub("Bearer [REDACTED]", text)

    def mask_ip(matched: re.Match) -> str:
        try:
            ip = ipaddress.ip_address(matched.group(0))
            return matched.group(0) if ip.is_global else "[PRIVATE-IP]"
        except ValueError:
            return matched.group(0)

    text = IPV4.sub(mask_ip, text)

    def mask_ipv6(matched: re.Match) -> str:
        value = matched.group(0)
        try:
            ip = ipaddress.ip_address(value.strip("[]"))
            return value if ip.is_global else "[PRIVATE-IPV6]"
        except ValueError:
            return value

    return IPV6.sub(mask_ipv6, text)


def scrub(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SENSITIVE.search(key) else scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def safe_record(record: DiagnosisRecord) -> dict:
    result = scrub(record.model_dump(mode="json"))
    result["export_notice"] = (
        "敏感字段、URL 查询串和非公网 IP 地址已脱敏；仍请在分享前检查目标、备注和证据。"
    )
    return result


def markdown(record: DiagnosisRecord) -> str:
    data = safe_record(record)
    source = "用户导入，未重新验证" if record.source == "imported" else "NetCase 本机实际检测"
    lines = [
        "# NetCase 网络诊断报告",
        "",
        f"- 检测时间（UTC）：{data['created_at']}",
        f"- 目标：`{data['target']}`",
        f"- 状态：{data['status']}",
        f"- 来源：{source}",
        f"- 环境：{data['environment']}",
        f"- 平台：{data['context'].get('platform', '未记录')}",
        f"- 协议 / 端口：{data['context'].get('protocol', '未记录')} / "
        f"{data['context'].get('port', '未记录')}",
        f"- 地址族：{'、'.join(data['context'].get('address_families', [])) or '未记录'}",
        f"- 规则版本：`{data['rule_version']}`",
    ]
    if data["notes"]:
        lines.append(f"- 备注：{data['notes']}")
    lines += ["", "## 结论", "", data["summary"], "", "## 检测模块", ""]
    for module in data["modules"]:
        duration = module["duration_ms"] if module["duration_ms"] is not None else "未测量"
        lines += [
            f"### {module['name'].upper()} · {module['status']}",
            "",
            f"- 耗时：{duration} ms",
            f"- 说明：{module['detail']}",
            f"- 错误类型：`{module['error_type'] or '无'}`",
            "",
            "技术证据：",
            "",
            "```json",
            json.dumps(module["evidence"], ensure_ascii=False, indent=2).replace("```", "` ` `"),
            "```",
            "",
        ]
    if data["conclusions"]:
        lines += ["## 分析与下一步", ""]
        for conclusion in data["conclusions"]:
            lines += [
                f"### {conclusion['title']}",
                "",
                f"- 置信程度：{conclusion['confidence']}",
                f"- 依据：{'；'.join(conclusion['evidence'])}",
                f"- 可能原因：{'；'.join(conclusion['possible_causes']) or '无足够证据'}",
                f"- 下一步：{'；'.join(conclusion['next_steps'])}",
                f"- 网络知识：{conclusion['knowledge']}",
                "",
            ]
    lines += [
        "## 限制与隐私",
        "",
        "- 单次结果仅适用于本次目标、网络环境和测试时间；不同环境不能直接归因。",
        "- HTTP 耗时仅到响应头；Ping 和路由节点不回应不一定说明网站不可访问。",
        f"- {data['export_notice']}",
        "",
    ]
    return "\n".join(lines)


def html_report(record: DiagnosisRecord) -> str:
    data = safe_record(record)

    def escape(value: object) -> str:
        return html.escape(str(value), quote=True)

    def bullet(items: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"

    modules = "".join(
        '<section class="card"><div class="row"><h3>'
        + escape(module["name"].upper())
        + '</h3><span class="badge">'
        + escape(module["status"])
        + "</span></div><p>"
        + escape(module["detail"])
        + "</p><dl><dt>耗时</dt><dd>"
        + escape(f"{module['duration_ms']} ms" if module["duration_ms"] is not None else "未测量")
        + "</dd><dt>错误类型</dt><dd>"
        + escape(module["error_type"] or "无")
        + "</dd></dl><details><summary>原始技术证据</summary><pre>"
        + escape(json.dumps(module["evidence"], ensure_ascii=False, indent=2))
        + "</pre></details></section>"
        for module in data["modules"]
    )
    conclusions = "".join(
        '<section class="card"><h3>'
        + escape(item["title"])
        + '</h3><p class="muted">置信程度：'
        + escape(item["confidence"])
        + "</p><h4>检测依据</h4>"
        + bullet(item["evidence"])
        + "<h4>可能原因</h4>"
        + bullet(item["possible_causes"] or ["无足够证据"])
        + "<h4>下一步建议</h4>"
        + bullet(item["next_steps"])
        + '<p class="knowledge">'
        + escape(item["knowledge"])
        + "</p></section>"
        for item in data["conclusions"]
    )
    source = "用户导入，未重新验证" if record.source == "imported" else "NetCase 本机实际检测"
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>NetCase 网络诊断报告</title><style>"
        ":root{color-scheme:light}body{font:15px/1.65 system-ui,sans-serif;"
        "background:#f6f8f8;color:#20313b;margin:0}main{max-width:840px;margin:40px auto;"
        "padding:0 22px 50px}header,.card,.foot{background:white;border:1px solid #dbe2e5;"
        "border-radius:12px;padding:22px 26px;margin:14px 0}header{border-top:4px solid #c45532}"
        "h1{font-size:28px;margin:0}h2{font-size:18px;margin:30px 0 12px}h3{font-size:16px;"
        "margin:0 0 8px}h4{margin:18px 0 4px;font-size:13px}p{margin:7px 0}"
        ".muted,dt,small{color:#647680}.row{display:flex;justify-content:space-between;gap:15px}"
        ".badge{font-size:12px;background:#edf4f2;padding:3px 10px;border-radius:20px}"
        "dl{display:grid;grid-template-columns:100px 1fr;gap:4px}dd{margin:0}"
        "li{margin:4px 0}.knowledge,.foot{color:#53656f}details{margin-top:15px}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7f8;"
        "padding:14px;border-radius:8px}code{overflow-wrap:anywhere}</style></head><body><main>"
        "<header><small>NETCASE · 网络诊断报告</small><h1>"
        + escape(data["summary"])
        + '</h1><p class="muted">目标：<code>'
        + escape(data["target"])
        + '</code></p><p class="muted">检测时间（UTC）：'
        + escape(data["created_at"])
        + " · "
        + escape(source)
        + "</p><p>环境："
        + escape(data["environment"])
        + " · "
        + escape(data["context"].get("platform", "未记录"))
        + " · "
        + escape(data["context"].get("protocol", "未记录"))
        + ":"
        + escape(data["context"].get("port", "未记录"))
        + " · 规则："
        + escape(data["rule_version"])
        + "</p>"
        + (f"<p>备注：{escape(data['notes'])}</p>" if data["notes"] else "")
        + "</header><h2>检测模块</h2>"
        + modules
        + "<h2>分析与下一步</h2>"
        + conclusions
        + '<div class="foot"><strong>限制与隐私</strong><p>单次结果仅适用于本次目标、'
        "网络环境和检测时间。HTTP 耗时仅到响应头；"
        "ICMP 中间节点不回应不一定代表网站不可访问。</p><p>"
        + escape(data["export_notice"])
        + "</p></div></main></body></html>"
    )
