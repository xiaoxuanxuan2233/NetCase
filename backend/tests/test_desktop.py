import socket
import time

import httpx

from desktop import LocalService


def test_desktop_service_starts_on_loopback_and_stops(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCASE_DATA_DIR", str(tmp_path))
    service = LocalService()
    service.start()
    try:
        deadline = time.monotonic() + 5
        while not service.address and service.error is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert service.error is None
        assert service.address is not None
        assert service.address.startswith("http://127.0.0.1:")
        with httpx.Client(trust_env=False) as client:
            health = client.get(f"{service.address}/api/health")
        assert health.status_code == 200
        assert health.json()["engine_available"] is True
    finally:
        service.stop()
        service.thread.join(timeout=5)
    assert not service.thread.is_alive()


def test_desktop_reports_bind_error_without_leaking_path(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCASE_DATA_DIR", str(tmp_path))
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        occupied.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen()
    service = LocalService(occupied.getsockname()[1])
    try:
        service.start()
        service.thread.join(timeout=5)
        assert not service.thread.is_alive()
        assert service.address is None
        assert service.error in {
            "本地服务未能启动（OSError）。",
            "本地服务未能启动（PermissionError）。",
        }
        assert str(tmp_path) not in service.error
    finally:
        service.stop()
        occupied.close()


def test_desktop_can_stop_during_startup(tmp_path, monkeypatch):
    monkeypatch.setenv("NETCASE_DATA_DIR", str(tmp_path))
    service = LocalService()
    service.start()
    service.stop()
    service.thread.join(timeout=5)
    assert not service.thread.is_alive()
    assert service.error is None
