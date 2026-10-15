"""Native build: run on the OS and architecture being packaged."""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from unix_packages import appimage, dmg

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
    macos = label.startswith("macos-")
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
    ]
    if macos:
        command += [
            "--windowed",
            "--osx-bundle-identifier",
            "io.github.xiaoxuanxuan2233.NetCase",
            "--icon",
            str(ROOT / "packaging" / "assets" / "netcase.icns"),
        ]
    entrypoint = "launcher.py" if single_file else "desktop.py"
    command.append(str(ROOT / "backend" / entrypoint))
    subprocess.run(command, cwd=ROOT, check=True)  # noqa: S603
    folder = DIST / "NetCase"
    executable = DIST / "NetCase.exe" if single_file else folder / "NetCase"
    if not executable.is_file():
        raise RuntimeError("打包后没有找到 NetCase 可执行文件")
    filename = f"NetCase-{VERSION}-{label}"
    if single_file:
        # Keep the verified Windows build independent of the new desktop formats.
        with tempfile.TemporaryDirectory(prefix="NetCase package ") as temporary:
            smoke_root = Path(temporary) / "独立运行"
            smoke_root.mkdir()
            smoke_executable = smoke_root / executable.name
            shutil.copy2(executable, smoke_executable)
            env = os.environ.copy()
            env["NETCASE_DATA_DIR"] = str(smoke_root / "data")
            subprocess.run(  # noqa: S603
                [str(smoke_executable), "--self-test"],
                cwd=smoke_root,
                env=env,
                timeout=60,
                check=True,
            )
        artifact = DIST / f"{filename}.exe"
        executable.replace(artifact)
    elif macos:
        artifact = DIST / f"{filename}.dmg"
        dmg(DIST / "NetCase.app", artifact)
    else:
        artifact = DIST / f"{filename}.AppImage"
        appimage(folder, artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (DIST / f"{artifact.name}.sha256").write_text(f"{digest}  {artifact.name}\n", encoding="ascii")
    print(f"Built and smoke-tested: {artifact}", flush=True)
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and smoke-test NetCase on this OS")
    parser.parse_args()
    build()
