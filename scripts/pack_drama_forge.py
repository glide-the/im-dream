#!/usr/bin/env python3
"""Pack vendor/drama-forge into a distributable Claude Code plugin + local marketplace.

Implements docs/design/deck/drama-forge-workspace-init-design.md §3:

- whitelist copy (drops .venv/tests/evals/logs/dev artifacts, skill-gen,
  .claude/settings.json, statusline.sh),
- C1 rewrite: CWD-relative invocations (``python3 scripts/...``,
  ``bash .claude/hooks/...``) become ``${CLAUDE_PLUGIN_ROOT}``-relative,
- injects ``.ink/workspace-init.json`` (init profile, digest-pinned with the
  artifact) and ``.ink/workspace-claude.md`` (workspace CLAUDE.md, C4),
- emits ``marketplaces/drama-studio/.claude-plugin/marketplace.json``.

Usage:
    python3 scripts/pack_drama_forge.py [--src vendor/drama-forge/drama-forge]
                                        [--dest marketplaces/drama-studio]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]

# §3.1 whitelist (top-level entries copied into the plugin package)
WHITELIST = [
    ".claude-plugin",
    ".claude",
    "schemas",
    "references",
    "scripts",
    "docs",
    "CLAUDE.md",
    "dramaforge.manifest.yaml",
    "pyproject.toml",
    "README.md",
]

# entries dropped inside whitelisted dirs
EXCLUDE_DIR_NAMES = {"__pycache__", "evals", ".pytest_cache", "node_modules"}
EXCLUDE_FILES = {
    ".claude/settings.json",       # C3: repo-local permissions, not shippable
    ".claude/statusline.sh",       # dev convenience bound to dropped settings
    ".DS_Store",
}
EXCLUDE_SKILL_DIRS = {"skill-gen"}  # kind: development (B2)

# C1 rewrite rules applied to every packaged .md file
REWRITE_RULES = [
    (re.compile(r"(?<![\w./-])python3\s+scripts/"), 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/'),
    (re.compile(r"(?<![\w./-])python\s+scripts/"), 'python "${CLAUDE_PLUGIN_ROOT}/scripts/'),
    (re.compile(r"(?<![\w./-])(pip3?)\s+install\s+-r\s+scripts/"),
     lambda m: f'{m.group(1)} install -r "${{CLAUDE_PLUGIN_ROOT}}/scripts/'),
    (re.compile(r"(?<![\w./-])bash\s+\.claude/hooks/"), 'bash "${CLAUDE_PLUGIN_ROOT}/.claude/hooks/'),
]

INIT_PROFILE = {
    "schema_version": "workspace-init/v1",
    "runtime_dirs": ["stories", "assets", "exports", ".dramaforge"],
    "workspace_files": [
        {
            "path": "CLAUDE.md",
            "source": ".ink/workspace-claude.md",
            "mode": "create-if-missing",
        }
    ],
    "python": {"requirements": "scripts/requirements.txt", "min_version": "3.11"},
}

WORKSPACE_CLAUDE_MD = """\
# DramaForge 工作区约定（插件注入版）

本工作区由 Deck 对话自动初始化。drama-forge 插件通过 `--plugin-dir` 加载，
插件根（`${CLAUDE_PLUGIN_ROOT}`，位于 `.ink/plugins/<drama-forge@drama-studio@…>/`）
**只读**；一切产物写入本工作区。

## 目录契约

- `stories/{project}/` — 项目源文件（剧本、大纲、设定集、集级合同/提交）
- `assets/` — 可复用资产（角色/场景/道具卡）
- `exports/` — 派生导出物（可删除重建）
- `.dramaforge/` — 运行状态（state.yaml 等）

## 插件资源解析

skills/agents 文档中引用的模板、规则、题材包、schema 与脚本，一律从插件根解析：
`${CLAUDE_PLUGIN_ROOT}/.claude/docs/…`、`${CLAUDE_PLUGIN_ROOT}/schemas/…`、
`${CLAUDE_PLUGIN_ROOT}/references/…`、`${CLAUDE_PLUGIN_ROOT}/scripts/…`。
调用 Python 工具链：`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dramaforge.py" …`
（解释器由运行时注入 PATH 提供，依赖已预装）。

## 协作协议

创作主导，AI 施工：Ask → Options → Decide → Draft → Approve。
一集一次提交；定稿资产是事实，变更必须走 retcon；审查隔离，编剧不能自审。
完整设计原则见 `${CLAUDE_PLUGIN_ROOT}/CLAUDE.md`。
"""

MARKETPLACE_JSON = {
    "name": "drama-studio",
    "owner": {"name": "Ink & Memory"},
    "description": "Ink & Memory 内置 marketplace：Dream 驱动插件",
    "plugins": [
        {
            "name": "drama-forge",
            "source": "./plugins/drama-forge",
            "description": "AI 短剧全流程协作系统（Dream 驱动插件）",
            "version": "1.0.1",
        }
    ],
}


def _iter_package_files(src: Path):
    """Yield (relative_path, absolute_path) for whitelisted package content."""
    for top in WHITELIST:
        base = src / top
        if not base.exists():
            continue
        if base.is_file():
            yield Path(top), base
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(src)
            rel_posix = rel.as_posix()
            if rel_posix in EXCLUDE_FILES:
                continue
            parts = set(rel.parts)
            if parts & EXCLUDE_DIR_NAMES:
                continue
            if rel.parts[:2] == (".claude", "skills") and rel.parts[2] in EXCLUDE_SKILL_DIRS:
                continue
            yield rel, path


def _rewrite_markdown(text: str, counters: dict[str, int]) -> str:
    for pattern, replacement in REWRITE_RULES:
        text, n = pattern.subn(replacement, text)
        counters["rewrites"] += n
    return text


def pack(src: Path, dest: Path) -> dict:
    plugin_dest = dest / "plugins" / "drama-forge"
    if plugin_dest.exists():
        shutil.rmtree(plugin_dest)
    plugin_dest.mkdir(parents=True)

    counters = {"files": 0, "rewrites": 0}
    for rel, abspath in _iter_package_files(src):
        target = plugin_dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel.suffix == ".md":
            target.write_text(
                _rewrite_markdown(abspath.read_text(encoding="utf-8"), counters),
                encoding="utf-8",
            )
        else:
            shutil.copy2(abspath, target)
        counters["files"] += 1

    # .ink payload: init profile + workspace CLAUDE.md (C4/C5, digest-pinned)
    ink_dir = plugin_dest / ".ink"
    ink_dir.mkdir(exist_ok=True)
    (ink_dir / "workspace-init.json").write_text(
        json.dumps(INIT_PROFILE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ink_dir / "workspace-claude.md").write_text(WORKSPACE_CLAUDE_MD, encoding="utf-8")

    # B1 guard: no bare CWD-relative script invocation may survive
    leftovers = []
    for md in plugin_dest.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for match in re.finditer(r"(?<![\w./-])python3?\s+scripts/", text):
            leftovers.append(f"{md.relative_to(plugin_dest)}: {match.group(0)}")
    if leftovers:
        raise SystemExit("C1 rewrite incomplete:\n" + "\n".join(leftovers[:20]))

    marketplace_dir = dest / ".claude-plugin"
    marketplace_dir.mkdir(parents=True, exist_ok=True)
    (marketplace_dir / "marketplace.json").write_text(
        json.dumps(MARKETPLACE_JSON, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return counters


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, default=REPO_ROOT / "vendor" / "drama-forge" / "drama-forge")
    parser.add_argument("--dest", type=Path, default=REPO_ROOT / "marketplaces" / "drama-studio")
    args = parser.parse_args()
    src = args.src.resolve()
    if not (src / ".claude-plugin" / "plugin.json").is_file():
        raise SystemExit(f"source is not a drama-forge checkout: {src}")
    counters = pack(src, args.dest.resolve())
    print(
        f"packed {counters['files']} files "
        f"({counters['rewrites']} C1 rewrites) -> {args.dest}"
    )


if __name__ == "__main__":
    sys.exit(main())
