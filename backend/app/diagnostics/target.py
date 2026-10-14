"""A single explicitly requested host and optional URL."""

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.models.schemas import DiagnosisInput


@dataclass(frozen=True)
class Target:
    host: str
    url: str
    port: int
    scheme: str
    is_ip: bool


def parse_target(request: DiagnosisInput) -> Target:
    raw = request.target
    if "://" not in raw:
        raw = f"https://[{raw}]" if ":" in raw and not raw.startswith("[") else f"https://{raw}"
    url = urlsplit(raw)
    host = url.hostname or ""
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    port = request.port or url.port or (443 if url.scheme == "https" else 80)
    # A user override applies to all connection modules, including HTTP.
    netloc = f"[{host}]" if ":" in host else host
    if port != (443 if url.scheme == "https" else 80):
        netloc += f":{port}"
    output_url = url._replace(netloc=netloc).geturl()
    if not url.path:
        output_url += "/"
    return Target(host=host, url=output_url, port=port, scheme=url.scheme, is_ip=is_ip)
