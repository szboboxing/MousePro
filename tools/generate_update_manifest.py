#!/usr/bin/env python3
"""Generate MousePro update metadata from release assets."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.update_installer import (
    APP_ID,
    MANIFEST_SCHEMA_VERSION,
    STABLE_CHANNEL,
    build_number_from_version,
    sha256_file,
)


_ASSET_PLATFORM_KEYS = {
    "MousePro-Windows.zip": "windows-x64",
    "MousePro-macOS.zip": "macos-arm64",
    "MousePro-macOS-intel.zip": "macos-x86_64",
    "MousePro-Linux.zip": "linux-x64",
    "MousePro-Windows-arm64.zip": "windows-arm64",
}


def _version_from_tag(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def _asset_platform_keys(tag: str) -> dict[str, str]:
    version = _version_from_tag(tag)
    return {
        **_ASSET_PLATFORM_KEYS,
        f"MousePro-v{version}-Windows.zip": "windows-x64",
    }


def build_payload(args) -> dict:
    asset_dir = Path(args.asset_dir)
    version = _version_from_tag(args.tag)
    assets = {}
    for name, platform_key in _asset_platform_keys(args.tag).items():
        path = asset_dir / name
        if not path.exists():
            continue
        assets[platform_key] = {
            "name": name,
            "url": f"https://github.com/{args.repo}/releases/download/{args.tag}/{name}",
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    if not assets:
        raise SystemExit(f"No known MousePro assets found in {asset_dir}")
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=int(args.expires_days))
    ).replace(microsecond=0)
    return {
        "schema": MANIFEST_SCHEMA_VERSION,
        "app_id": APP_ID,
        "channel": STABLE_CHANNEL,
        "version": version,
        "tag": args.tag,
        "build_number": int(args.build_number or build_number_from_version(version)),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "commit": args.commit,
        "release_notes_url": f"https://github.com/{args.repo}/releases/tag/{args.tag}",
        "assets": assets,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--asset-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expires-days", default="30")
    parser.add_argument("--build-number", default="")
    args = parser.parse_args()

    payload = build_payload(args)
    Path(args.output).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
