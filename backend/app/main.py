import asyncio
import json
import logging
import platform
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.dashboard import summarize
from app.diagnostics.engine import run, selected_modules
from app.diagnostics.target import parse_target
from app.models.schemas import (
    DiagnosisInput,
    DiagnosisRecord,
    DraftInput,
    FavoriteInput,
    NoteInput,
    ReportImport,
    Settings,
)
from app.reports.export import html_report, markdown, safe_record
from app.storage.database import Base, Draft, Favorite, Preference, Record, make_database

MAX_BODY_BYTES = 2 * 1024 * 1024
logger = logging.getLogger("netcase")


def create_app(database_url: str | None = None) -> FastAPI:
    engine, sessions = make_database(database_url)
    jobs: dict[str, dict] = {}
    active: set[str] = set()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="NetCase", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        allowed_origins = {
            f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (8000, 5173)
        }
        # The production UI may be started on another explicit loopback port.
        allowed_origins.add(f"http://{request.headers.get('host', '')}")
        if origin and origin not in allowed_origins:
            return JSONResponse({"detail": "仅允许本地界面访问"}, status_code=403)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.headers.get("x-netcase-client") != "dashboard":
                return JSONResponse({"detail": "缺少本地客户端标记"}, status_code=403)
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BODY_BYTES:
                    return JSONResponse({"detail": "导入文件不能超过 2 MiB"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)  # Replay the bounded body to FastAPI's parser.
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    @app.get("/api/health")
    async def health():
        return {"version": "0.1.0", "platform": platform.system(), "engine_available": True}

    @app.post("/api/diagnoses", status_code=202)
    async def start_diagnosis(body: DiagnosisInput):
        if len(active) >= 2:
            raise HTTPException(429, "已有两项诊断在运行，请等待其中一项结束")
        target = parse_target(body)
        job_id = str(uuid4())
        names = selected_modules(body, target.scheme, target.is_ip)
        jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "current": None,
            "modules": {name: "pending" for name in names},
            "results": [],
            "record_id": None,
            "error": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
        active.add(job_id)

        def progress(name: str, status: str, completed: list) -> None:
            job = jobs[job_id]
            job["status"] = "running"
            job["current"] = name if status == "running" else None
            job["modules"][name] = status
            job["results"] = [m.model_dump(mode="json") for m in completed]

        async def execute() -> None:
            try:
                record = await asyncio.wait_for(run(body, progress), timeout=90)
                with sessions() as db:
                    db.add(
                        Record(
                            id=record.id,
                            created_at=record.created_at.isoformat(),
                            target=record.target,
                            payload=record.model_dump(mode="json"),
                        )
                    )
                    db.commit()
                jobs[job_id].update(
                    {"status": "completed", "record_id": record.id, "current": None}
                )
            except TimeoutError:
                logger.warning("diagnosis_timeout job_id=%s", job_id)
                jobs[job_id].update(
                    {"status": "failed", "current": None, "error": "诊断超过 90 秒上限，已停止。"}
                )
            except Exception as exc:
                logger.error("diagnosis_failed job_id=%s error_type=%s", job_id, type(exc).__name__)
                # Never return exception text, targets, or credentials through the API.
                jobs[job_id].update(
                    {
                        "status": "failed",
                        "current": None,
                        "error": "诊断未能保存，请检查本地数据目录与服务状态。",
                    }
                )
            finally:
                active.discard(job_id)

        asyncio.create_task(execute())
        return {"id": job_id, "status": "pending", "modules": jobs[job_id]["modules"]}

    @app.get("/api/diagnoses/{job_id}")
    async def get_diagnosis(job_id: str):
        now = datetime.now(UTC)
        for key, value in list(jobs.items()):
            if (
                value["status"] in {"completed", "failed"}
                and (now - datetime.fromisoformat(value["created_at"])).total_seconds() > 3600
            ):
                jobs.pop(key, None)
        if job_id not in jobs:
            raise HTTPException(404, "任务不存在或已过期，请到历史记录查看结果")
        return jobs[job_id]

    @app.get("/api/dashboard")
    async def dashboard(days: int = Query(7, ge=1, le=30), offset: int = Query(0, ge=-840, le=840)):
        tz = timezone(timedelta(minutes=offset))
        today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        since = (today - timedelta(days=days - 1)).astimezone(UTC).isoformat()
        with sessions() as db:
            rows = db.scalars(select(Record).where(Record.created_at >= since)).all()
            result = summarize(
                [DiagnosisRecord.model_validate(r.payload) for r in rows], days, offset
            )
            result["favorites"] = [
                {"id": f.id, "target": f.target, "label": f.label}
                for f in db.scalars(select(Favorite).order_by(Favorite.target)).all()
            ]
            result["drafts"] = [
                {"id": d.id, "created_at": d.created_at, **d.payload}
                for d in db.scalars(select(Draft).order_by(Draft.created_at.desc())).all()
            ]
        return result

    @app.post("/api/favorites", status_code=201)
    async def add_favorite(body: FavoriteInput):
        with sessions() as db:
            if db.scalar(select(func.count()).select_from(Favorite)) >= 100:
                raise HTTPException(409, "最多保存 100 个常用目标")
            item = Favorite(id=str(uuid4()), **body.model_dump())
            db.add(item)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(409, "此目标已收藏") from None
            return {"id": item.id, "target": item.target, "label": item.label}

    @app.delete("/api/favorites/{item_id}", status_code=204)
    async def delete_favorite(item_id: str):
        with sessions() as db:
            item = db.get(Favorite, item_id)
            if not item:
                raise HTTPException(404, "目标不存在")
            db.delete(item)
            db.commit()

    @app.post("/api/drafts", status_code=201)
    async def add_draft(body: DraftInput):
        with sessions() as db:
            if db.scalar(select(func.count()).select_from(Draft)) >= 20:
                raise HTTPException(409, "已有 20 个草稿，请先移除不需要的草稿")
            item = Draft(
                id=str(uuid4()), created_at=datetime.now(UTC).isoformat(), payload=body.model_dump()
            )
            db.add(item)
            db.commit()
            return {"id": item.id, "created_at": item.created_at, **item.payload}

    @app.delete("/api/drafts/{item_id}", status_code=204)
    async def delete_draft(item_id: str):
        with sessions() as db:
            item = db.get(Draft, item_id)
            if not item:
                raise HTTPException(404, "草稿不存在")
            db.delete(item)
            db.commit()

    @app.post("/api/records/import", status_code=201)
    async def import_records(body: ReportImport):
        if any(r.created_at > datetime.now(UTC) + timedelta(minutes=5) for r in body.records):
            raise HTTPException(422, "检测时间不能在未来（允许 5 分钟时钟偏差）")
        with sessions() as db:
            ids = [r.id for r in body.records]
            existing = set(db.scalars(select(Record.id).where(Record.id.in_(ids))).all())
            for record in body.records:
                if record.id in existing:
                    continue
                # Imported reports are never represented as probes executed by NetCase.
                record.source = "imported"
                db.add(
                    Record(
                        id=record.id,
                        created_at=record.created_at.isoformat(),
                        target=record.target,
                        payload=record.model_dump(mode="json"),
                    )
                )
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(409, "存在并发导入，请刷新后重试") from None
        return {"imported": len(body.records) - len(existing), "skipped": len(existing)}

    @app.get("/api/records/export")
    async def export_records():
        with sessions() as db:
            records = [
                safe_record(DiagnosisRecord.model_validate(r.payload))
                for r in db.scalars(select(Record).order_by(Record.created_at)).all()
            ]
        return Response(
            json.dumps({"schema_version": 1, "records": records}, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="netcase-records.json"'},
        )

    @app.get("/api/records")
    async def list_records(
        target: str = Query("", max_length=200),
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = Query(30, ge=1, le=200),
        offset: int = Query(0, ge=0, le=10000),
    ):
        if any(value and value.tzinfo is None for value in (since, until)):
            raise HTTPException(422, "时间筛选必须包含时区")
        if since and until and since > until:
            raise HTTPException(422, "起始时间不得晚于结束时间")
        stmt = select(Record)
        if since:
            stmt = stmt.where(Record.created_at >= since.astimezone(UTC).isoformat())
        if until:
            stmt = stmt.where(Record.created_at <= until.astimezone(UTC).isoformat())
        with sessions() as db:
            rows = db.scalars(stmt.order_by(Record.created_at.desc())).all()
        # Literal substring; a user-supplied '%' never becomes a SQL wildcard.
        matched = [r for r in rows if target.casefold() in r.target.casefold()]
        return {
            "total": len(matched),
            "items": [r.payload for r in matched[offset : offset + limit]],
        }

    @app.get("/api/records/compare")
    async def compare_records(left: str, right: str):
        if left == right:
            raise HTTPException(422, "请选择两条不同的记录")
        with sessions() as db:
            first, second = db.get(Record, left), db.get(Record, right)
        if not first or not second:
            raise HTTPException(404, "比较记录不存在")
        a, b = (
            DiagnosisRecord.model_validate(first.payload),
            DiagnosisRecord.model_validate(second.payload),
        )
        conditions = {
            "target": a.target == b.target,
            "network_label": a.context.get("network_label") == b.context.get("network_label"),
            "resolver": a.context.get("resolver") == b.context.get("resolver"),
            "address_families": a.context.get("address_families")
            == b.context.get("address_families"),
            "port": a.context.get("port") == b.context.get("port"),
            "modules": {m.name for m in a.modules} == {m.name for m in b.modules},
            "time": a.created_at == b.created_at,
        }
        ma = {m.name: m for m in a.modules}
        mb = {m.name: m for m in b.modules}
        changes = [
            {
                "module": name,
                "before": ma[name].model_dump(mode="json"),
                "after": mb[name].model_dump(mode="json"),
                "duration_delta_ms": round(mb[name].duration_ms - ma[name].duration_ms, 1)
                if ma[name].duration_ms is not None and mb[name].duration_ms is not None
                else None,
            }
            for name in sorted(ma.keys() & mb.keys())
        ]
        return {
            "left": a.model_dump(mode="json"),
            "right": b.model_dump(mode="json"),
            "conditions_equal": conditions,
            "changes": changes,
            "caution": "只描述两次检测的差异，不据此推断运营商或网站故障原因。",
        }

    @app.get("/api/records/{record_id}")
    async def get_record(record_id: str):
        with sessions() as db:
            row = db.get(Record, record_id)
            if not row:
                raise HTTPException(404, "记录不存在")
            return row.payload

    @app.patch("/api/records/{record_id}")
    async def update_note(record_id: str, body: NoteInput):
        with sessions() as db:
            row = db.get(Record, record_id)
            if not row:
                raise HTTPException(404, "记录不存在")
            value = DiagnosisRecord.model_validate({**row.payload, "notes": body.notes})
            row.payload = value.model_dump(mode="json")
            db.commit()
            return row.payload

    @app.delete("/api/records/{record_id}", status_code=204)
    async def delete_record(record_id: str):
        with sessions() as db:
            row = db.get(Record, record_id)
            if not row:
                raise HTTPException(404, "记录不存在")
            db.delete(row)
            db.commit()

    @app.delete("/api/records", status_code=204)
    async def clear_records(before: datetime | None = None):
        if before and before.tzinfo is None:
            raise HTTPException(422, "清理时间必须包含时区")
        with sessions() as db:
            statement = delete(Record)
            if before:
                statement = statement.where(Record.created_at < before.astimezone(UTC).isoformat())
            db.execute(statement)
            db.commit()

    @app.get("/api/records/{record_id}/report")
    async def export_report(
        record_id: str, format: Literal["json", "markdown", "html"] = "markdown"
    ):
        with sessions() as db:
            row = db.get(Record, record_id)
            if not row:
                raise HTTPException(404, "记录不存在")
            record = DiagnosisRecord.model_validate(row.payload)
        contents = {
            "json": lambda: json.dumps(
                {"schema_version": 1, "records": [safe_record(record)]},
                ensure_ascii=False,
                indent=2,
            ),
            "markdown": lambda: markdown(record),
            "html": lambda: html_report(record),
        }
        media = {"json": "application/json", "markdown": "text/markdown", "html": "text/html"}
        extension = {"markdown": "md", "json": "json", "html": "html"}[format]
        return Response(
            contents[format](),
            media_type=media[format],
            headers={
                "Content-Disposition": f'attachment; filename="netcase-{record_id}.{extension}"'
            },
        )

    @app.get("/api/settings")
    async def get_settings():
        with sessions() as db:
            row = db.get(Preference, "settings")
            return Settings.model_validate(row.value if row else {}).model_dump(mode="json")

    @app.put("/api/settings")
    async def update_settings(value: Settings):
        with sessions() as db:
            db.merge(Preference(key="settings", value=value.model_dump(mode="json")))
            db.commit()
        return value

    @app.get("/api/{unknown_path:path}", include_in_schema=False)
    async def unknown_api(unknown_path: str):
        raise HTTPException(404, "API 不存在")

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    dist = bundle_root / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
