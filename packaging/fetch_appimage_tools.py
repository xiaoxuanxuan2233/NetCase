"""Fetch upstream build tools, refusing changed release binaries."""

import hashlib
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "build" / "appimage-tools"
FILES = (
    (
        "appimagetool.AppImage",
        "https://github.com/AppImage/appimagetool/releases/download/continuous/"
        "appimagetool-x86_64.AppImage",
        "95cbe7cce9717fce90c484e34052ee7c7f1d7635b33c12525b4776826a7d29b6",
    ),
    (
        "runtime-x86_64",
        "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64",
        "156f4bdbde9c52d01814600013e0a273f0118dc2de98975f3c8c63427ec79074",
    ),
)


def fetch() -> None:
    TOOLS.mkdir(parents=True, exist_ok=True)
    for name, url, expected in FILES:
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
            data = response.read(64 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError(
                f"Upstream checksum changed; review the new release before using {name}"
            )
        destination = TOOLS / name
        destination.write_bytes(data)
        destination.chmod(0o755)
        print(f"Verified upstream SHA-256: {name}", flush=True)


if __name__ == "__main__":
    fetch()
