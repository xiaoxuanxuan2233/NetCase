import importlib.util
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "netcase_unix_packages", Path(__file__).resolve().parents[2] / "packaging" / "unix_packages.py"
)
assert spec is not None and spec.loader is not None
packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packages)


@pytest.mark.parametrize(
    ("messages", "expected_calls", "fails"),
    [
        (["hdiutil: create failed - Resource busy", "created"], 2, False),
        (["hdiutil: create failed - Resource busy"] * 3, 3, True),
        (["hdiutil: create failed - Invalid argument"], 1, True),
    ],
)
def test_disk_image_retries_only_transient_busy_errors(
    monkeypatch, messages, expected_calls, fails
):
    calls = []

    def run(command, *, stdout, **kwargs):
        message = messages[len(calls)]
        calls.append(command)
        stdout.write(message)
        return subprocess.CompletedProcess(command, 0 if message == "created" else 1)

    monkeypatch.setattr(packages.subprocess, "run", run)
    monkeypatch.setattr(packages.time, "sleep", lambda _: None)
    if fails:
        with pytest.raises(subprocess.CalledProcessError):
            packages.disk_image(["/usr/bin/hdiutil", "create"])
    else:
        packages.disk_image(["/usr/bin/hdiutil", "create"])
    assert len(calls) == expected_calls
