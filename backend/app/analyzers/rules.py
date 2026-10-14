"""Deterministic explanations. Every conclusion cites a performed module."""

from app.models.schemas import Conclusion, ModuleResult

RULE_VERSION = "rules-1"


def analyze(modules: list[ModuleResult]) -> tuple[str, list[Conclusion]]:
    by_name = {module.name: module for module in modules}
    conclusions: list[Conclusion] = []

    def add(
        level: str,
        confidence: str,
        title: str,
        evidence: list[str],
        causes: list[str],
        steps: list[str],
        knowledge: str,
    ) -> None:
        conclusions.append(
            Conclusion(
                level=level,
                confidence=confidence,
                title=title,
                evidence=evidence,
                possible_causes=causes,
                next_steps=steps,
                knowledge=knowledge,
            )
        )

    dns = by_name.get("dns")
    tcp = by_name.get("tcp")
    tls = by_name.get("tls")
    http = by_name.get("http")

    if dns and dns.status in {"failed", "warning"}:
        add(
            "error" if dns.status == "failed" else "warning",
            "确认",
            "本次域名解析没有得到可连接的地址。",
            [f"DNS：{dns.detail}"],
            ["DNS 配置、解析器状态或目标域名可能有问题；无法据此判断网站服务器状态。"],
            [
                "核对域名拼写与系统 DNS 设置。",
                "在明确同意向第三方发起查询后，可选择公开解析器作对比。",
            ],
            "NXDOMAIN 表示解析器报告域名不存在；SERVFAIL 表示查询处理失败。"
            "无地址记录也可能是查询成功但记录类型缺失。",
        )
    if dns and dns.evidence.get("comparison", {}).get("different_addresses"):
        add(
            "info",
            "确认",
            "两个解析器返回了不同的 IP 地址。",
            ["DNS 对比结果不同"],
            ["CDN、负载均衡和地理调度都可能造成不同地址。"],
            ["核对各解析器的返回地址和测试地点；只有更多证据才能判断是否异常。"],
            "DNS 结果不一致本身不等于污染。",
        )
    if tcp and tcp.status == "failed":
        add(
            "error",
            "确认",
            "本次 TCP 连接没有建立。",
            [f"TCP：{tcp.detail}", f"错误类型：{tcp.error_type or '未分类'}"],
            ["服务未监听、网络不可达、连接超时或访问策略都可能造成此现象。"],
            ["确认端口和目标地址。", "对比其他网络或时间点的结果，再检查服务端日志。"],
            "连接失败不能仅凭一次测试归因于防火墙封锁。",
        )
    elif tcp and tcp.status == "warning":
        add(
            "warning",
            "确认",
            "部分地址可以连接，部分连接失败。",
            [f"TCP：{tcp.detail}"],
            ["不同 IP 或 IPv4/IPv6 路径的可达性可能不同。"],
            ["展开地址明细，核对失败的是哪个 IP 与地址族。"],
            "同一域名可以对应多个地址；一次成功不代表所有地址都可用。",
        )
    if tls and tls.status == "failed":
        causes = {
            "TLS_CERT_EXPIRED": ["证书有效期已结束。"],
            "TLS_NAME_MISMATCH": ["证书名称与所访问主机名不一致。"],
            "TLS_CHAIN_UNTRUSTED": ["证书链无法通过当前系统的信任校验。"],
        }.get(tls.error_type or "", ["协议兼容性、服务配置或传输问题等均可能导致握手失败。"])
        add(
            "error",
            "确认",
            "TCP 可达，但 HTTPS 安全连接未成功。"
            if tcp and tcp.status in {"success", "warning"}
            else "HTTPS 安全连接未成功。",
            (["TCP：至少一个地址连接成功"] if tcp and tcp.status in {"success", "warning"} else [])
            + [f"TLS：{tls.detail}", f"错误类型：{tls.error_type or '未分类'}"],
            causes,
            ["核对本机时间、目标域名和证书信息。", "如你管理服务器，检查证书、信任链与 TLS 配置。"],
            "TLS 默认验证证书；握手失败本身不能证明存在中间人攻击。",
        )
    if http and http.status == "warning":
        code = http.evidence.get("status_code")
        if isinstance(code, int):
            title = f"连接已建立，服务器返回 HTTP {code}。"
            causes = (
                ["可能是网站服务暂时异常。"]
                if code >= 500
                else ["可能是访问控制、请求频率或资源权限。"]
            )
            add(
                "warning",
                "确认",
                title,
                [f"HTTP：{http.detail}"],
                causes,
                ["检查网站状态、账号权限或服务端日志。", "在相同条件下复测。"],
                "HTTP 错误码表示服务器已返回响应，不等同于 DNS 或 TCP 故障。",
            )
        else:
            add(
                "warning",
                "确认",
                "HTTP 请求没有得到预期的最终响应。",
                [f"HTTP：{http.detail}"],
                ["重定向次数或目标不符合安全限制。"],
                ["查看重定向链与最终 URL。"],
                "重定向可能导致请求到另一台主机。",
            )
    elif http and http.status == "failed":
        add(
            "error",
            "确认",
            "HTTP 请求没有收到响应头。",
            [f"HTTP：{http.detail}"],
            ["连接、TLS 或服务端响应阶段都可能发生错误。"],
            ["对照 DNS、TCP 和 TLS 模块查看故障出现在哪一层。"],
            "HTTP 计时仅到响应头，不包括下载正文。",
        )
    if not conclusions:
        performed = [m for m in modules if m.status != "unsupported"]
        if performed and all(m.status == "success" for m in performed):
            add(
                "success",
                "确认",
                "本次已选检测项目均通过。",
                [f"{m.name.upper()}：{m.detail}" for m in performed[:6]],
                [],
                ["如网站仍不可用，请检查浏览器、代理、登录状态或应用层功能。"],
                "单次检测通过仅说明当前时刻、目标和测试条件下这些步骤成功。",
            )
        elif any(m.status == "warning" for m in performed):
            add(
                "warning",
                "较可能",
                "部分检测结果需要进一步核对。",
                [f"{m.name.upper()}：{m.detail}" for m in performed if m.status == "warning"],
                ["辅助检测可能因权限或目标配置受限。"],
                ["查看各模块原始证据，必要时在相同条件下复测。"],
                "Ping 或中间路由节点不响应，不一定意味着网站不可访问。",
            )
        else:
            add(
                "info",
                "无法判断",
                "所选项目没有足够的可用结果。",
                [f"{m.name.upper()}：{m.detail}" for m in modules],
                ["目标与检测类型可能不适用，或本机缺少必要工具。"],
                ["更换适用模块后再试。"],
                "不能从未执行的检查推断故障原因。",
            )
    return conclusions[0].title, conclusions
