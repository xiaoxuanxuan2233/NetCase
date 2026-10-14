"""Native build: run on the OS and architecture being packaged."""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "release-dist"
BUILD = ROOT / "build"
VERSION = "0.1.0-preview.1"


def platform_label() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64" if machine in {"amd64", "x86_64"} else ""
    if system not in {"Windows", "Darwin", "Linux"} or not arch:
        raise RuntimeError(f"不支持的打包平台：{system} {machine}")
    return {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}[system] + f"-{arch}"


def build() -> Path:
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        raise RuntimeError("请先在 frontend 执行 npm ci && npm run build")
    label = platform_label()
    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", "NetCase", "--distpath", str(DIST),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
        "--paths", str(ROOT / "backend"),
        "--collect-submodules", "uvicorn",
        "--add-data", f"{ROOT / 'frontend' / 'dist'}{os.pathsep}frontend/dist",
        str(ROOT / "backend" / "launcher.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)  # noqa: S603
    folder = DIST / "NetCase"
    executable = folder / ("NetCase.exe" if os.name == "nt" else "NetCase")
    if not executable.is_file():
        raise RuntimeError("打包后没有找到 NetCase 可执行文件")
    # The executable must serve both the API and the built UI before it can be distributed.
    env = os.environ.copy()
    env["NETCASE_DATA_DIR"] = str(BUILD / "smoke-data")
    subprocess.run(  # noqa: S603
        [str(executable), "--self-test"], cwd=ROOT, env=env, timeout=45, check=True
    )
    (folder / "LICENSE").write_bytes((ROOT / "LICENSE").read_bytes())
    (folder / "README.md").write_bytes((ROOT / "README.md").read_bytes())
    filename = f"NetCase-{VERSION}-{label}"
    if platform.system() == "Linux":
        archive = DIST / f"{filename}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(folder, arcname="NetCase")
    else:
        archive = DIST / f"{filename}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in folder.rglob("*"):
                if path.is_file():
                    bundle.write(path, Path("NetCase") / path.relative_to(folder))
    shutil.rmtree(folder)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (DIST / f"{archive.name}.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii"
    )
    print(f"Built and smoke-tested: {archive}", flush=True)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and smoke-test NetCase on this OS")
    parser.parse_args()
    build()
