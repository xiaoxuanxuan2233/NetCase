param([int]$Port = 8000)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "请先安装 uv，并确认 Python 3.12+ 可用。详见 README.md。"
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "请先安装 Node.js 22.12+（含 npm）。详见 README.md。"
}
if ($Port -lt 1 -or $Port -gt 65535) { throw "端口必须在 1–65535 之间。" }
Push-Location (Join-Path $root "frontend")
try {
  npm ci
  if ($LASTEXITCODE -ne 0) { throw "前端依赖安装失败" }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
} finally { Pop-Location }
Push-Location (Join-Path $root "backend")
try {
  uv sync --locked
  if ($LASTEXITCODE -ne 0) { throw "后端依赖安装失败" }
  Write-Host "NetCase: http://127.0.0.1:$Port"
  uv run --no-sync uvicorn app.main:create_app --factory --host 127.0.0.1 --port $Port --no-access-log
  if ($LASTEXITCODE -ne 0) { throw "NetCase 服务启动失败" }
} finally { Pop-Location }
