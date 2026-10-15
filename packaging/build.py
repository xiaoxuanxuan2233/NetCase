"""Native build: run on the OS and architecture being packaged."""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "release-dist"
BUILD = ROOT / "build"
VERSION = "0.1.0-preview.2"


def platform_label() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    arch = (
        "arm64"
        if machine in {"arm64", "aarch64"}
        else "x64"
        if machine in {"amd64", "x86_64"}
        else ""
    )
    if system not in {"Windows", "Darwin", "Linux"} or not arch:
        raise RuntimeError(f"不支持的打包平台：{system} {machine}")
    return {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}[system] + f"-{arch}"


def build() -> Path:
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        raise RuntimeError("请先在 frontend 执行 npm ci && npm run build")
    label = platform_label()
    single_file = label.startswith("windows-")
    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile" if single_file else "--onedir",
        "--name",
        "NetCase",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD / "pyinstaller"),
        "--specpath",
        str(BUILD),
        "--paths",
        str(ROOT / "backend"),
        "--collect-submodules",
        "uvicorn",
        "--add-data",
        f"{ROOT / 'frontend' / 'dist'}{os.pathsep}frontend/dist",
        "--add-data",
        f"{ROOT / 'LICENSE'}{os.pathsep}.",
        str(ROOT / "backend" / "launcher.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)  # noqa: S603
    folder = DIST / "NetCase"
    executable = DIST / "NetCase.exe" if single_file else folder / "NetCase"
    if not executable.is_file():
        raise RuntimeError("打包后没有找到 NetCase 可执行文件")
    # Test a relocated package with no source checkout or installed dependencies nearby.
    # The Windows test directory contains only the EXE before it is launched.
    with tempfile.TemporaryDirectory(prefix="NetCase package ") as temporary:
        smoke_root = Path(temporary) / "独立运行"
        smoke_root.mkdir()
        if single_file:
            smoke_executable = smoke_root / executable.name
            shutil.copy2(executable, smoke_executable)
        else:
            shutil.copytree(folder, smoke_root / "NetCase")
            smoke_executable = smoke_root / "NetCase" / executable.name
        env = os.environ.copy()
        env["NETCASE_DATA_DIR"] = str(smoke_root / "data")
        subprocess.run(  # noqa: S603
            [str(smoke_executable), "--self-test"],
            cwd=smoke_root,
            env=env,
            timeout=60,
            check=True,
        )
    filename = f"NetCase-{VERSION}-{label}"
    if single_file:
        artifact = DIST / f"{filename}.exe"
        executable.replace(artifact)
    else:
        (folder / "LICENSE").write_bytes((ROOT / "LICENSE").read_bytes())
        (folder / "README.md").write_bytes((ROOT / "README.md").read_bytes())
        if platform.system() == "Linux":
            artifact = DIST / f"{filename}.tar.gz"
            with tarfile.open(artifact, "w:gz") as bundle:
                bundle.add(folder, arcname="NetCase")
        else:
            artifact = DIST / f"{filename}.zip"
            with zipfile.ZipFile(artifact, "w", zipfile.ZIP_DEFLATED) as bundle:
                for path in folder.rglob("*"):
                    if path.is_file():
                        bundle.write(path, Path("NetCase") / path.relative_to(folder))
        shutil.rmtree(folder)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (DIST / f"{artifact.name}.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
    print(f"Built and smoke-tested: {artifact}", flush=True)
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and smoke-test NetCase on this OS")
    parser.parse_args()
    build()
