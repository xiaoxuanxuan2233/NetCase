"""Input normalization only. This module never resolves or contacts targets."""

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


def normalize_target(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("请输入一个有效的域名、IP 或 HTTP(S) URL")
    if "\\" in value:
        raise ValueError("目标不能包含反斜杠")
    # Unbracketed IP literals are valid; an IPv6 port requires brackets in a URL.
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    explicit_scheme = "://" in value
    try:
        parsed = urlsplit(value if explicit_scheme else f"https://{value}")
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            raise ValueError("仅支持 HTTP(S)，且 URL 不能包含账号或密码")
        if not parsed.hostname:
            raise ValueError("缺少目标主机")
        port = parsed.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("端口必须在 1–65535 之间")
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        try:
            address = ipaddress.ip_address(host)
            host = f"[{address}]" if address.version == 6 else str(address)
        except ValueError:
            if len(host) > 253 or not all(
                re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in host.split(".")
            ):
                raise ValueError("域名格式无效") from None
        netloc = host + (f":{port}" if port is not None else "")
        if not explicit_scheme and (parsed.path or parsed.query or parsed.fragment):
            raise ValueError("含路径的目标请补充 http:// 或 https://")
        if not explicit_scheme:
            return netloc
        return urlunsplit((parsed.scheme, netloc, parsed.path or "/", parsed.query, ""))
    except (UnicodeError, ValueError) as exc:
        raise ValueError(str(exc)) from None


def addresses_allowed(addresses: list[str], allow_local: bool) -> bool:
    """Reject an entire DNS answer set if any address needs an explicit local opt-in."""
    try:
        return bool(addresses) and all(
            ipaddress.ip_address(address).is_global or allow_local for address in addresses
        )
    except ValueError:
        return False
