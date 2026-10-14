import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from app.main import create_app
from app.models.schemas import DiagnosisRecord, ModuleResult
from app.reports.export import EXPORT_NOTICE, html_report, markdown, safe_record

HEADERS = {"x-netcase-client": "dashboard"}


def fixture_record(record_id="test-record") -> DiagnosisRecord:
    return DiagnosisRecord(
        id=record_id,
        created_at=datetime.now(UTC),
        target="https://example.com/status?token=supersecret",
        mode="quick",
        status="success",
        duration_ms=134.3,
        summary="DNS 与 TCP 已通过。",
        rule_version="rules-1",
        environment="测试网络",
        notes="password=hunter2",
        modules=[
            ModuleResult(
                name="dns",
                status="success",
                duration_ms=13,
                detail="获得 A 记录。",
                evidence={"A": ["192.168.1.2"], "cookie": "abc"},
            )
        ],
    )


def test_export_masks_secrets_private_addresses_and_escapes_html():
    record = fixture_record()
    record.notes += " <script>alert('x')</script>"
    record.modules[0].evidence["ipv6"] = "fd00::1"
    assert "supersecret" not in markdown(record)
    assert "hunter2" not in markdown(record)
    assert "192.168.1.2" not in markdown(record)
    assert "fd00::1" not in markdown(record)
    assert "abc" not in markdown(record)
    assert "[REDACTED]" in str(safe_record(record))
    assert "<script>" not in html_report(record)
    assert "&lt;script&gt;" in html_report(record)


def test_api_storage_history_settings_and_security(tmp_path, monkeypatch):
    async def fake_run(body, progress):
        progress("dns", "running", [])
        record = fixture_record("actual-job")
        record.source = "runtime"
        return record

    monkeypatch.setattr("app.main.run", fake_run)
    app = create_app(f"sqlite:///{tmp_path / 'netcase.db'}")

    async def exercise():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000"
            ) as client:
                assert (await client.get("/api/health")).json()["engine_available"]
                assert (await client.get("/api/dashboard")).json()["stats"]["total"] == 0
                assert (
                    await client.post("/api/diagnoses", json={"target": "example.com"})
                ).status_code == 403
                assert (
                    await client.post(
                        "/api/favorites",
                        json={"target": "x.com"},
                        headers={**HEADERS, "origin": "https://malicious.test"},
                    )
                ).status_code == 403
                assert (
                    await client.get("/api/health", headers={"host": "evil.test"})
                ).status_code == 400
                assert (
                    await client.post(
                        "/api/diagnoses", json={"target": "invalid host"}, headers=HEADERS
                    )
                ).status_code == 422
                assert (
                    await client.put(
                        "/api/settings",
                        json={},
                        headers={
                            **HEADERS,
                            "host": "127.0.0.1:8001",
                            "origin": "http://127.0.0.1:8001",
                        },
                    )
                ).status_code == 200
                started = await client.post(
                    "/api/diagnoses", json={"target": "example.com"}, headers=HEADERS
                )
                assert started.status_code == 202
                job_id = started.json()["id"]
                for _ in range(20):
                    job = (await client.get(f"/api/diagnoses/{job_id}")).json()
                    if job["status"] == "completed":
                        break
                    await asyncio.sleep(0.01)
                assert job["record_id"] == "actual-job", job
                latest = (await client.get("/api/dashboard")).json()
                assert latest["stats"]["total"] == 1
                assert latest["latest"]["id"] == "actual-job"
                assert (await client.get("/api/records?target=example.com")).json()["total"] == 1
                assert (await client.get("/api/records?target=no-match")).json()["total"] == 0
                assert (
                    await client.get("/api/records/compare?left=actual-job&right=actual-job")
                ).status_code == 422
                report = await client.get("/api/records/actual-job/report?format=json")
                assert "supersecret" not in report.text
                assert "hunter2" not in report.text
                assert "192.168.1.2" not in report.text
                export = await client.get("/api/records/export")
                assert "supersecret" not in export.text
                assert "hunter2" not in export.text
                settings = await client.put(
                    "/api/settings",
                    json={
                        "timeout_seconds": 4,
                        "default_mode": "custom",
                        "default_modules": ["dns", "tcp"],
                        "theme": "dark",
                    },
                    headers=HEADERS,
                )
                assert settings.status_code == 200
                assert (await client.get("/api/settings")).json()["timeout_seconds"] == 4
                assert (
                    await client.delete("/api/records/actual-job", headers=HEADERS)
                ).status_code == 204
                assert (await client.get("/api/records")).json()["total"] == 0

    asyncio.run(exercise())


def test_import_compare_clear_and_body_limit(tmp_path):
    first = fixture_record("first")
    second = fixture_record("second")
    second.created_at = first.created_at + timedelta(seconds=1)
    second.modules[0].duration_ms = 25
    app = create_app(f"sqlite:///{tmp_path / 'history.db'}")

    async def exercise():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000"
            ) as client:
                too_large = await client.put(
                    "/api/settings",
                    headers=HEADERS,
                    content=b" " * (2 * 1024 * 1024 + 1),
                )
                assert too_large.status_code == 413
                payload = {
                    "schema_version": 1,
                    "records": [first.model_dump(mode="json"), second.model_dump(mode="json")],
                }
                imported = await client.post("/api/records/import", headers=HEADERS, json=payload)
                assert imported.status_code == 201
                assert imported.json()["imported"] == 2
                assert (
                    await client.post("/api/records/import", headers=HEADERS, json=payload)
                ).json()["skipped"] == 2
                comparison = (
                    await client.get("/api/records/compare?left=first&right=second")
                ).json()
                assert comparison["conditions_equal"]["time"] is False
                assert comparison["changes"][0]["duration_delta_ms"] == 12
                assert comparison["left"]["source"] == "imported"
                assert (await client.delete("/api/records", headers=HEADERS)).status_code == 204
                assert (await client.get("/api/records")).json()["total"] == 0

    asyncio.run(exercise())


def test_redacted_json_export_import_roundtrip_and_legacy_notice(tmp_path):
    record = fixture_record("private-target")
    record.target = "https://192.168.1.2/status?token=supersecret"
    record.context["http_resolution"] = "HTTP 初始目标沿用本次 DNS；跨主机重定向单独解析并校验。"
    assert "HTTP 地址条件" in markdown(record)
    assert "跨主机重定向" in html_report(record)
    app = create_app(f"sqlite:///{tmp_path / 'roundtrip.db'}")

    async def exercise():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8000"
            ) as client:
                source = {"schema_version": 1, "records": [record.model_dump(mode="json")]}
                assert (
                    await client.post("/api/records/import", headers=HEADERS, json=source)
                ).status_code == 201
                single = (await client.get("/api/records/private-target/report?format=json")).json()
                bulk = (await client.get("/api/records/export")).json()
                for exported in (single, bulk):
                    assert exported["export_notice"] == EXPORT_NOTICE
                    assert exported["records"][0]["target"] == "redacted.invalid"
                    assert "export_notice" not in exported["records"][0]
                    assert "supersecret" not in str(exported)
                    assert "192.168.1.2" not in str(exported)
                assert (await client.delete("/api/records", headers=HEADERS)).status_code == 204
                imported = await client.post("/api/records/import", headers=HEADERS, json=bulk)
                assert imported.status_code == 201, imported.text
                restored = (await client.get("/api/records/private-target")).json()
                assert restored["target"] == "redacted.invalid"
                assert restored["source"] == "imported"
                assert "supersecret" not in str(restored)
                assert "192.168.1.2" not in str(restored)
                legacy = {
                    "schema_version": 1,
                    "records": [
                        {
                            **safe_record(record),
                            "id": "legacy",
                            "target": "https://[PRIVATE-IP]/status",
                            "export_notice": "旧版逐条附加的提示",
                        }
                    ],
                }
                older = await client.post("/api/records/import", headers=HEADERS, json=legacy)
                assert older.status_code == 201, older.text
                assert (await client.get("/api/records/legacy")).json()[
                    "target"
                ] == "redacted.invalid"

    asyncio.run(exercise())
