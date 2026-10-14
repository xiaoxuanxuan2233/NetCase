from datetime import UTC
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from app.core.targets import normalize_target

Target = Annotated[str, AfterValidator(normalize_target)]
Status = Literal["success", "warning", "failed", "unsupported"]
ModuleName = Literal["dns", "tcp", "tls", "http", "ping", "traceroute"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ModuleResult(StrictModel):
    name: ModuleName
    status: Status
    duration_ms: float | None = Field(default=None, ge=0, le=3_600_000)
    error_type: str | None = Field(default=None, max_length=120)
    detail: str = Field(default="", max_length=1000)
    evidence: dict[str, JsonValue] = Field(default_factory=dict, max_length=40)


class Conclusion(StrictModel):
    level: Literal["info", "success", "warning", "error"]
    confidence: Literal["确认", "较可能", "无法判断"]
    title: str = Field(max_length=140)
    evidence: list[str] = Field(max_length=8)
    possible_causes: list[str] = Field(max_length=8)
    next_steps: list[str] = Field(max_length=8)
    knowledge: str = Field(max_length=600)


class DiagnosisRecord(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    created_at: AwareDatetime
    target: Target
    mode: Literal["quick", "full", "custom"]
    status: Status
    duration_ms: float = Field(ge=0, le=3_600_000)
    summary: str = Field(min_length=1, max_length=500)
    rule_version: str = Field(default="unversioned", max_length=64)
    environment: str = Field(default="未标注", max_length=120)
    notes: str = Field(default="", max_length=1000)
    modules: list[ModuleResult] = Field(min_length=1, max_length=6)
    conclusions: list[Conclusion] = Field(default_factory=list, max_length=12)
    context: dict[str, JsonValue] = Field(default_factory=dict, max_length=30)
    source: Literal["imported", "runtime"] = "imported"

    @field_validator("created_at")
    @classmethod
    def utc(cls, value: AwareDatetime) -> AwareDatetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def consistent_modules(self) -> "DiagnosisRecord":
        if len({module.name for module in self.modules}) != len(self.modules):
            raise ValueError("检测模块不能重复")
        statuses = {module.status for module in self.modules if module.status != "unsupported"}
        expected = (
            "unsupported"
            if not statuses
            else "failed"
            if "failed" in statuses
            else "warning"
            if "warning" in statuses
            else "success"
        )
        if self.status != expected:
            raise ValueError("总体状态与模块结果不一致")
        return self


class FavoriteInput(StrictModel):
    target: Target
    label: str = Field(default="", max_length=60)


class DraftInput(StrictModel):
    target: Target
    port: int | None = Field(default=None, ge=1, le=65535, strict=True)
    mode: Literal["quick", "full"] = "quick"


class DiagnosisInput(StrictModel):
    target: Target
    port: int | None = Field(default=None, ge=1, le=65535, strict=True)
    mode: Literal["quick", "full", "custom"] = "quick"
    modules: list[ModuleName] | None = Field(default=None, min_length=1, max_length=6)
    timeout_seconds: float = Field(default=3.0, ge=1.0, le=10.0)
    resolver: Literal["system", "cloudflare", "google"] = "system"
    compare_resolver: Literal["cloudflare", "google"] | None = None
    network_label: str = Field(default="", max_length=60)
    allow_local: bool = False

    @model_validator(mode="after")
    def valid_selection(self) -> "DiagnosisInput":
        if self.mode == "custom" and not self.modules:
            raise ValueError("自定义模式需要至少一个检测模块")
        if self.mode != "custom" and self.modules:
            raise ValueError("只有自定义模式可以指定检测模块")
        if self.modules and len(set(self.modules)) != len(self.modules):
            raise ValueError("检测模块不能重复")
        return self


class ReportImport(StrictModel):
    schema_version: Literal[1]
    records: list[DiagnosisRecord] = Field(min_length=1, max_length=500)
    export_notice: str | None = Field(default=None, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def legacy_export_notice(cls, value: object) -> object:
        if not isinstance(value, dict) or not isinstance(value.get("records"), list):
            return value
        # Preview 1 exported the notice inside every record. It is metadata,
        # not a DiagnosisRecord field; accept those existing files on import.
        records = []
        for record in value["records"]:
            if isinstance(record, dict):
                cleaned = {key: item for key, item in record.items() if key != "export_notice"}
                if isinstance(cleaned.get("target"), str) and "[PRIVATE-IP" in cleaned["target"]:
                    # Older exports masked IP literals into invalid target syntax.
                    cleaned["target"] = "redacted.invalid"
                records.append(cleaned)
            else:
                records.append(record)
        return {**value, "records": records}

    @model_validator(mode="after")
    def unique_ids(self) -> "ReportImport":
        ids = [record.id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("文件中有重复的记录 ID")
        return self


class Settings(StrictModel):
    timeout_seconds: float = Field(default=3.0, ge=1.0, le=10.0)
    default_mode: Literal["quick", "full", "custom"] = "quick"
    default_modules: list[ModuleName] = Field(
        default_factory=lambda: ["dns", "tcp", "tls"], min_length=1, max_length=6
    )
    theme: Literal["light", "dark", "system"] = "system"

    @field_validator("default_modules")
    @classmethod
    def unique_modules(cls, value: list[ModuleName]) -> list[ModuleName]:
        if len(set(value)) != len(value):
            raise ValueError("默认模块不能重复")
        return value


class NoteInput(StrictModel):
    notes: str = Field(max_length=1000)
