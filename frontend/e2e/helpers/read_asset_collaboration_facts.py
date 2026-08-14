#!/usr/bin/env python3
"""Read one real Dream workspace's canonical and private asset facts as JSON."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def _frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        boundary = text.find("\n---\n", 4)
        if boundary >= 0:
            payload = yaml.safe_load(text[4:boundary]) or {}
            return (payload if isinstance(payload, dict) else {}, text)
    payload = yaml.safe_load(text) if path.suffix.lower() in {".yaml", ".yml"} else {}
    return (payload if isinstance(payload, dict) else {}, text)


def _asset_map(root: Path, kind: str) -> dict[str, dict[str, object]]:
    identity_fields = {
        "characters": ("char_id", "character_id", "id"),
        "scenes": ("scene_id", "id"),
        "props": ("prop_id", "id"),
    }[kind]
    name_fields = {
        "characters": ("char_name", "character_name", "name", "display_name"),
        "scenes": ("scene_name", "name", "display_name"),
        "props": ("name", "prop_name", "display_name"),
    }[kind]
    values: dict[str, dict[str, object]] = {}
    directory = root / "assets" / kind
    for path in sorted(directory.glob("*")) if directory.is_dir() else ():
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        metadata, text = _frontmatter(path)
        identity = next((str(metadata.get(key) or "").strip() for key in identity_fields if metadata.get(key)), path.stem)
        name = next((str(metadata.get(key) or "").strip() for key in name_fields if metadata.get(key)), path.stem)
        values[identity] = {
            "name": name,
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text": text,
        }
    return values


def main() -> None:
    thread_id, run_id = sys.argv[1:3]
    workspace_base = Path(os.environ.get("AGENT_CWD") or REPO_ROOT / "backend/data/agent-workspace")
    root = (workspace_base / thread_id).resolve(strict=True)
    projects = [path for path in (root / "stories").iterdir() if path.is_dir() and (path / "project.yaml").is_file()]
    assert len(projects) == 1, f"expected one canonical Project, got {len(projects)}"
    project = projects[0]
    storyboard_path = project / "episodes" / "EP01" / "storyboard.yaml"
    storyboard = yaml.safe_load(storyboard_path.read_text(encoding="utf-8")) or {}
    assert isinstance(storyboard, dict)
    run_root = root / ".dream" / "runtime" / "runs" / run_id
    stages: dict[str, object] = {}
    for stage in ("characters", "scenes", "storyboards"):
        stage_path = run_root / "stages" / f"{stage}.json"
        stages[stage] = json.loads(stage_path.read_text(encoding="utf-8")) if stage_path.is_file() else None
    workbench = root / ".dream" / "WORKBENCH.md"
    asset_contract = root / ".dream" / "ASSET-COLLABORATION.md"
    print(json.dumps({
        "workspaceRoot": str(root),
        "projectSlug": project.name,
        "characters": _asset_map(root, "characters"),
        "scenes": _asset_map(root, "scenes"),
        "props": _asset_map(root, "props"),
        "storyboardPath": storyboard_path.relative_to(root).as_posix(),
        "storyboard": storyboard,
        "stages": stages,
        "workbenchPath": str(workbench),
        "assetContractPath": str(asset_contract),
        "workbenchExists": workbench.is_file(),
        "assetContractExists": asset_contract.is_file(),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
