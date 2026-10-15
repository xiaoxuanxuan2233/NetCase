"""Create and verify the actual macOS and Linux downloads."""

import os
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(command: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True, timeout=180)  # noqa: S603


def self_test(executable: Path, directory: Path, appimage: bool = False) -> None:
    env = os.environ.copy()
    env["NETCASE_DATA_DIR"] = str(directory / "data")
    command = [str(executable)]
    if appimage:
        command.append("--appimage-extract-and-run")
    check([*command, "--self-test"], cwd=directory, env=env)
    gui = [*command, "--self-test-gui"]
    if appimage:
        xvfb = shutil.which("xvfb-run")
        if not xvfb:
            raise RuntimeError("Install xvfb to verify the AppImage desktop window")
        gui = [xvfb, "-a", *gui]
    check(gui, cwd=directory, env=env)
    print("Packaged API, web UI, desktop startup and shutdown passed", flush=True)


def dmg(app: Path, destination: Path) -> None:
    # Version the bundle before re-signing it with an ad-hoc signature.
    info = app / "Contents" / "Info.plist"
    data = plistlib.loads(info.read_bytes())
    data.update(CFBundleShortVersionString="0.1.0", CFBundleVersion="0.1.0")
    info.write_bytes(plistlib.dumps(data))
    check(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(app)])
    check(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
    with tempfile.TemporaryDirectory(prefix="NetCase DMG ") as temporary:
        base = Path(temporary)
        stage = base / "stage"
        stage.mkdir()
        shutil.copytree(app, stage / "NetCase.app", symlinks=True)
        (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
        shutil.copy2(ROOT / "LICENSE", stage / "LICENSE")
        check(
            [
                "/usr/bin/hdiutil",
                "create",
                "-ov",
                "-format",
                "UDZO",
                "-volname",
                "NetCase",
                "-srcfolder",
                str(stage),
                str(destination),
            ]
        )
        check(["/usr/bin/hdiutil", "verify", str(destination)])
        mount = base / "mounted"
        mount.mkdir()
        check(
            [
                "/usr/bin/hdiutil",
                "attach",
                "-readonly",
                "-nobrowse",
                "-mountpoint",
                str(mount),
                str(destination),
            ]
        )
        isolated = base / "独立运行"
        isolated.mkdir()
        try:
            installed = isolated / "NetCase.app"
            shutil.copytree(mount / "NetCase.app", installed, symlinks=True)
        finally:
            check(["/usr/bin/hdiutil", "detach", str(mount)])
        check(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(installed)])
        self_test(installed / "Contents" / "MacOS" / "NetCase", isolated)


def appimage(folder: Path, destination: Path) -> None:
    if not destination.name.endswith("linux-x64.AppImage"):
        raise RuntimeError("Only x86_64 AppImage builds are currently supported")
    with tempfile.TemporaryDirectory(prefix="NetCase AppDir ") as temporary:
        base = Path(temporary)
        appdir = base / "NetCase.AppDir"
        payload = appdir / "usr" / "bin" / "netcase"
        shutil.copytree(folder, payload, symlinks=True)
        licenses = appdir / "usr" / "share" / "doc" / "netcase"
        licenses.mkdir(parents=True)
        shutil.copy2(ROOT / "LICENSE", licenses / "LICENSE")
        shutil.copy2(ROOT / "packaging" / "licenses" / "AppImage-runtime.txt", licenses)
        (appdir / "AppRun").write_text(
            '#!/bin/sh\nHERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\n'
            'exec "$HERE/usr/bin/netcase/NetCase" "$@"\n',
            encoding="utf-8",
        )
        (appdir / "AppRun").chmod(0o755)
        (appdir / "netcase.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=NetCase\n"
            "Comment=Local network diagnostics\nExec=AppRun\nIcon=netcase\n"
            "Terminal=false\nCategories=Network;Utility;\n",
            encoding="utf-8",
        )
        shutil.copy2(ROOT / "frontend" / "public" / "favicon.svg", appdir / "netcase.svg")
        (appdir / ".DirIcon").symlink_to("netcase.svg")
        tools = ROOT / "build" / "appimage-tools"
        if not (tools / "appimagetool.AppImage").is_file():
            raise RuntimeError("Run packaging/fetch_appimage_tools.py before building an AppImage")
        env = os.environ.copy()
        env["ARCH"] = "x86_64"
        check(
            [
                str(tools / "appimagetool.AppImage"),
                "--appimage-extract-and-run",
                "--no-appstream",
                "--runtime-file",
                str(tools / "runtime-x86_64"),
                str(appdir),
                str(destination),
            ],
            cwd=base,
            env=env,
        )
        isolated = base / "独立运行"
        isolated.mkdir()
        copy = isolated / destination.name
        shutil.copy2(destination, copy)
        copy.chmod(0o755)
        self_test(copy, isolated, appimage=True)
