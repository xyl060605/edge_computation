"""Restore an unavailable registry component from its exact public Git commit.

Run only after strict upstream verification/camera patch application. This
changes the component source location, keeping image_player version 1.1.0~1.
No network, credentials, SDK installation or flashing happens in this script.
"""
import argparse
import hashlib
import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
COMMIT = "d61e0ccb1d7b0a2a214d0c90f5451fd683f41682"
REPOSITORY = "https://github.com/espressif2022/image_player.git"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    manifest = json.loads((PACKAGE / "upstream-manifest.json").read_text(encoding="utf-8"))
    original = next(item for item in manifest["files"] if item["path"] == "main/idf_component.yml")
    path = source / "main" / "idf_component.yml"
    if hashlib.sha256(path.read_bytes()).hexdigest() != original["sha256"]:
        raise SystemExit("Dependency manifest differs from the pinned official baseline")
    text = path.read_text(encoding="utf-8")
    old = "  espressif2022/image_player: ==1.1.0~1\n"
    if text.count(old) != 1:
        raise SystemExit("Expected exact legacy component declaration is missing")
    new = ("  espressif2022/image_player:\n"
           f"    git: {REPOSITORY}\n"
           f"    version: {COMMIT}\n")
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    report = {"component": "espressif2022/image_player", "component_version": "1.1.0~1",
              "source_repository": REPOSITORY, "source_commit": COMMIT,
              "reason": "Original registry release cannot be resolved; exact-version Git source remains available",
              "upstream_manifest_sha256": original["sha256"],
              "modified_manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (source / "build-dependency-overrides.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
