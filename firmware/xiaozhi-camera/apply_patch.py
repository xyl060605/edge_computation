"""Strict, offline patch application for the pinned upstream v2.0.3 only.

No network, package installation, compilation, flashing or credential handling.
Default mode validates without changing the supplied source checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parent
PINNED_COMMIT = "dd45d0de26bb64f339fb9f311a0952e474152166"
PATCH = PACKAGE / "mebot-camera-v2.0.3.patch"


def run(command: list[str], directory: Path) -> str:
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        raise ValueError("命令未通过：" + " ".join(command[:3]) + "\n" + result.stderr.strip())
    return result.stdout.strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_original_files(source: Path) -> dict:
    manifest = json.loads((PACKAGE / "upstream-manifest.json").read_text(encoding="utf-8"))
    if manifest.get("commit") != PINNED_COMMIT:
        raise ValueError("交付清单的版本不匹配，停止应用")
    for item in manifest["files"]:
        candidate = (source / item["path"]).resolve()
        if not candidate.is_relative_to(source.resolve()):
            raise ValueError("来源清单包含越界路径")
        if not candidate.is_file() or digest(candidate) != item["sha256"]:
            raise ValueError("源文件不匹配：" + item["path"] + "；需要原始 v2.0.3 LF 源码，不能强行套用3660变体")
    for relative in ("main/boards/common/mebot_camera_server.h", "main/boards/common/mebot_camera_server.cc"):
        if (source / relative).exists():
            raise ValueError("新增文件已经存在，请使用未修改的源码目录：" + relative)
    return manifest


def verify_checkout(source: Path) -> dict:
    if not source.is_dir():
        raise ValueError("指定源码目录不存在")
    root = Path(run(["git", "rev-parse", "--show-toplevel"], source)).resolve()
    if root != source.resolve():
        raise ValueError("--source 必须指向上游 Git 仓库根目录")
    if run(["git", "rev-parse", "HEAD"], source) != PINNED_COMMIT:
        raise ValueError("Git HEAD 不是指定的官方 v2.0.3 commit；拒绝应用到其他版本或自定义变体")
    if run(["git", "status", "--porcelain", "--untracked-files=normal"], source):
        raise ValueError("源码工作区有修改或未跟踪文件；请使用独立干净的源码副本")
    return verify_original_files(source)


def check_patch(source: Path) -> None:
    run(["git", "-c", "core.autocrlf=false", "apply", "--check", "--whitespace=error-all", str(PATCH)], source)


def reference_check() -> dict:
    """Apply against bundled, hash-verified reference files, never a user tree."""
    manifest = verify_original_files(PACKAGE / "upstream")
    with tempfile.TemporaryDirectory(prefix="static-check-", dir=PACKAGE) as name:
        target = Path(name).resolve()
        if not target.is_relative_to(PACKAGE):
            raise ValueError("静态校验目录不在交付文件夹内")
        shutil.copytree(PACKAGE / "upstream", target, dirs_exist_ok=True)
        # Anchor Git at this temporary tree even if its parent is a repository.
        run(["git", "init", "--quiet"], target)
        run(["git", "config", "core.autocrlf", "false"], target)
        check_patch(target)
        run(["git", "-c", "core.autocrlf=false", "apply", "--whitespace=error-all", str(PATCH)], target)
        modified = []
        for expected in sorted((PACKAGE / "patched-source").rglob("*")):
            if not expected.is_file():
                continue
            relative = expected.relative_to(PACKAGE / "patched-source")
            actual = target / relative
            if not actual.is_file() or digest(actual) != digest(expected):
                raise ValueError("补丁应用结果与审阅源码不一致：" + relative.as_posix())
            modified.append(relative.as_posix())
        report = {
            "upstream_commit": PINNED_COMMIT,
            "verified_reference_files": len(manifest["files"]),
            "patch_sha256": digest(PATCH),
            "patch_applies_exactly": True,
            "patched_files_match_review_sources": True,
            "modified_files": modified,
            "cxx_compilation_performed": False,
            "firmware_generated": False,
            "hardware_pin_3660_verified": False,
            "hardware_voice_camera_coexistence_tested": False,
            "note": "仅静态补丁应用校验，不代表C++编译、3660硬件适配或实机通过。",
        }
        (PACKAGE / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="精确官方commit的独立干净Git源码根目录")
    parser.add_argument("--apply", action="store_true", help="验证通过后实际应用补丁；默认只检查")
    parser.add_argument("--reference-check", action="store_true", help="在交付文件夹内临时验证参考源码与补丁，不修改外部源码")
    args = parser.parse_args()
    try:
        if args.reference_check:
            if args.source or args.apply:
                raise ValueError("参考校验不能与 --source/--apply 同用")
            print(json.dumps(reference_check(), ensure_ascii=False, indent=2))
        else:
            if args.source is None:
                raise ValueError("请提供 --source，或使用 --reference-check")
            source = args.source.resolve()
            verify_checkout(source)
            check_patch(source)
            if args.apply:
                run(["git", "-c", "core.autocrlf=false", "apply", "--whitespace=error-all", str(PATCH)], source)
            print("版本与补丁检查通过；" + ("已应用，尚未编译或验证硬件。" if args.apply else "未改动源码。"))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
