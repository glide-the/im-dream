"""Fail-closed adoption contract for the three pre-existing canonical tables."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping


BASELINE_TABLE_NAMES = frozenset(
    {"users", "story_workspace_workspaces", "story_workspace_stories"}
)


class BaselineAdoptionError(RuntimeError):
    """The existing canonical baseline cannot be adopted without ambiguity."""


@dataclass(frozen=True)
class ColumnContract:
    name: str
    pg_type: str
    nullable: bool
    default: str | None = None
    identity: bool = False


@dataclass(frozen=True)
class TableContract:
    columns: tuple[ColumnContract, ...]
    primary_key: tuple[str, ...]
    indexes: Mapping[str, tuple[bool, tuple[str, ...]]]
    foreign_keys: Mapping[str, tuple[tuple[str, ...], str, tuple[str, ...], str]]
    checks: Mapping[str, tuple[str, ...]]


BASELINE_CONTRACTS: dict[str, TableContract] = {
    "users": TableContract(
        columns=(
            ColumnContract("id", "bigint", False, identity=True),
            ColumnContract("email", "text", False),
            ColumnContract("password_hash", "text", False),
            ColumnContract("display_name", "text", True),
            ColumnContract("created_at", "timestamptz", False, "now()"),
            ColumnContract("avatar_url", "text", True),
            ColumnContract("role", "text", False, "'user'"),
            ColumnContract("updated_at", "timestamptz", False, "now()"),
            ColumnContract("status", "text", False, "'active'"),
        ),
        primary_key=("id",),
        indexes={
            "users_email_uidx": (True, ("email",)),
            "users_status_updated_idx": (False, ("status", "updated_at")),
        },
        foreign_keys={},
        checks={"users_status_check": ("status", "active", "disabled")},
    ),
    "story_workspace_workspaces": TableContract(
        columns=(
            ColumnContract("id", "text", False),
            ColumnContract("name", "text", False),
            ColumnContract("owner_id", "bigint", False),
            ColumnContract("settings", "jsonb", False, "'{}'"),
            ColumnContract("created_at", "timestamptz", False, "now()"),
            ColumnContract("updated_at", "timestamptz", False, "now()"),
            ColumnContract("status", "text", False, "'active'"),
        ),
        primary_key=("id",),
        indexes={
            "story_workspace_workspaces_owner_idx": (False, ("owner_id",)),
            "story_workspace_workspaces_status_updated_idx": (
                False,
                ("status", "updated_at"),
            ),
        },
        foreign_keys={
            "story_workspace_workspaces_owner_id_users_id_fk": (
                ("owner_id",),
                "users",
                ("id",),
                "RESTRICT",
            )
        },
        checks={
            "story_workspace_workspaces_status_check": (
                "status",
                "active",
                "archived",
            )
        },
    ),
    "story_workspace_stories": TableContract(
        columns=(
            ColumnContract("id", "text", False),
            ColumnContract("identifier", "text", False),
            ColumnContract("title", "text", False),
            ColumnContract("description", "text", True),
            ColumnContract("status", "text", False, "'draft'"),
            ColumnContract("review_status", "text", False, "'pending'"),
            ColumnContract("type", "text", False, "'short'"),
            ColumnContract("content", "text", True),
            ColumnContract("author_id", "bigint", False),
            ColumnContract("workspace_id", "text", False),
            ColumnContract("character_count", "integer", False, "0"),
            ColumnContract("scene_count", "integer", False, "0"),
            ColumnContract("agent_generated", "integer", False, "1"),
            ColumnContract("agent_session_id", "text", True),
            ColumnContract("review_notes", "text", True),
            ColumnContract("created_at", "timestamptz", False, "now()"),
            ColumnContract("updated_at", "timestamptz", False, "now()"),
            ColumnContract("confirmed_at", "timestamptz", True),
            ColumnContract("published_at", "timestamptz", True),
        ),
        primary_key=("id",),
        indexes={
            "story_workspace_stories_author_updated_idx": (
                False,
                ("author_id", "updated_at"),
            ),
            "story_workspace_stories_workspace_updated_idx": (
                False,
                ("workspace_id", "updated_at"),
            ),
            "story_workspace_stories_status_updated_idx": (
                False,
                ("status", "updated_at"),
            ),
            "story_workspace_stories_review_updated_idx": (
                False,
                ("review_status", "updated_at"),
            ),
            "story_workspace_stories_type_updated_idx": (
                False,
                ("type", "updated_at"),
            ),
            "story_workspace_stories_title_idx": (False, ("title",)),
        },
        foreign_keys={
            "story_workspace_stories_author_id_users_id_fk": (
                ("author_id",),
                "users",
                ("id",),
                "RESTRICT",
            ),
            # PostgreSQL truncates identifiers to 63 bytes.  This is the
            # physical constraint name produced by the Admin-head migration;
            # adoption must compare against the catalog, not the untruncated
            # logical spelling from the source SQL.
            "story_workspace_stories_workspace_id_story_workspace_workspaces": (
                ("workspace_id",),
                "story_workspace_workspaces",
                ("id",),
                "RESTRICT",
            ),
        },
        checks={
            "story_workspace_stories_status_check": ("status", "draft", "published", "archived"),
            "story_workspace_stories_review_status_check": ("review_status", "pending", "confirmed", "rejected"),
            "story_workspace_stories_type_check": ("type", "short", "long", "script", "outline"),
            "story_workspace_stories_agent_generated_check": ("agent_generated", "0", "1"),
            "story_workspace_stories_character_count_check": ("character_count", "0"),
            "story_workspace_stories_scene_count_check": ("scene_count", "0"),
        },
    ),
}


def decide_baseline_action(
    table_names: Iterable[str],
    view_names: Iterable[str] = (),
) -> str:
    tables = BASELINE_TABLE_NAMES.intersection(table_names)
    views = BASELINE_TABLE_NAMES.intersection(view_names)
    if views:
        raise BaselineAdoptionError(
            f"canonical baseline name collision with non-table relation: {sorted(views)!r}"
        )
    if not tables:
        return "create"
    if tables == BASELINE_TABLE_NAMES:
        return "adopt"
    raise BaselineAdoptionError(
        "canonical baseline is only partially present; refusing mixed create/adopt: "
        f"present={sorted(tables)!r}, missing={sorted(BASELINE_TABLE_NAMES - tables)!r}"
    )


def _normalize_type(column_type: Any) -> str:
    name = column_type.__class__.__name__.lower()
    rendered = str(column_type).lower()
    timezone = bool(getattr(column_type, "timezone", False))
    if "bigint" in name or rendered in {"bigint", "int8"}:
        return "bigint"
    if name in {"integer", "int", "int4"} or rendered in {"integer", "int", "int4"}:
        return "integer"
    if "timestamp" in name or "timestamp" in rendered:
        return "timestamptz" if timezone or "with time zone" in rendered else "timestamp"
    if "text" in name or rendered == "text":
        return "text"
    return rendered


def _normalize_default(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().split()).lower()
    normalized = re.sub(
        r"::(?:text|character varying|timestamp with time zone|jsonb)",
        "",
        normalized,
    )
    if normalized in {"current_timestamp", "now()", "timezone('utc', now())"}:
        return "now()"
    if normalized.startswith("nextval("):
        return None
    return normalized


def _column_signature(column: Mapping[str, Any]) -> ColumnContract:
    return ColumnContract(
        name=str(column["name"]),
        pg_type=_normalize_type(column["type"]),
        nullable=bool(column["nullable"]),
        default=_normalize_default(column.get("default")),
        identity=bool(column.get("identity")),
    )


def validate_table_contract(inspector: Any, table_name: str) -> None:
    expected = BASELINE_CONTRACTS[table_name]
    actual_columns = tuple(
        _column_signature(column) for column in inspector.get_columns(table_name)
    )
    if actual_columns != expected.columns:
        raise BaselineAdoptionError(f"{table_name} column contract drift")

    primary_key = inspector.get_pk_constraint(table_name)
    if tuple(primary_key.get("constrained_columns") or ()) != expected.primary_key:
        raise BaselineAdoptionError(f"{table_name} primary key drift")

    actual_indexes = {
        str(index["name"]): (
            bool(index.get("unique")),
            tuple(index.get("column_names") or ()),
        )
        for index in inspector.get_indexes(table_name)
    }
    if actual_indexes != dict(expected.indexes):
        raise BaselineAdoptionError(f"{table_name} index contract drift")

    unique_constraints = inspector.get_unique_constraints(table_name)
    if unique_constraints:
        raise BaselineAdoptionError(f"{table_name} has unexpected UNIQUE constraints")

    actual_foreign_keys: dict[str, tuple[tuple[str, ...], str, tuple[str, ...], str]] = {}
    for foreign_key in inspector.get_foreign_keys(table_name):
        options = foreign_key.get("options") or {}
        actual_foreign_keys[str(foreign_key["name"])] = (
            tuple(foreign_key.get("constrained_columns") or ()),
            str(foreign_key.get("referred_table")),
            tuple(foreign_key.get("referred_columns") or ()),
            str(options.get("ondelete") or "NO ACTION").upper(),
        )
    if actual_foreign_keys != dict(expected.foreign_keys):
        raise BaselineAdoptionError(f"{table_name} foreign key contract drift")

    actual_checks = {
        str(check["name"]): " ".join(str(check.get("sqltext") or "").lower().split())
        for check in inspector.get_check_constraints(table_name)
    }
    if set(actual_checks) != set(expected.checks):
        raise BaselineAdoptionError(f"{table_name} check constraint names drift")
    for name, required_tokens in expected.checks.items():
        if any(token.lower() not in actual_checks[name] for token in required_tokens):
            raise BaselineAdoptionError(f"{table_name}.{name} check definition drift")


def validate_baseline_for_adoption(
    bind: Any,
    *,
    expected_owner: str | None,
    expected_acl_sha256: str | None,
    inspector: Any | None = None,
) -> None:
    """Validate structure, physical owner, and data readability before adopt."""

    if not expected_owner:
        raise BaselineAdoptionError(
            "DREAM_EXPECTED_BASELINE_OWNER is required when adopting existing canonical tables"
        )
    if not expected_acl_sha256 or not re.fullmatch(
        r"[0-9a-f]{64}", expected_acl_sha256
    ):
        raise BaselineAdoptionError(
            "DREAM_EXPECTED_BASELINE_ACL_SHA256 is required when adopting existing canonical tables"
        )
    if inspector is None:
        from sqlalchemy import inspect

        inspector = inspect(bind)

    for table_name in sorted(BASELINE_TABLE_NAMES):
        validate_table_contract(inspector, table_name)

    from sqlalchemy import text

    owner_rows = bind.execute(
        text(
            "SELECT c.relname, pg_get_userbyid(c.relowner) "
            "FROM pg_catalog.pg_class AS c "
            "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
            "WHERE n.nspname = current_schema() AND c.relname = ANY(:names) "
            "ORDER BY c.relname"
        ),
        {"names": sorted(BASELINE_TABLE_NAMES)},
    ).all()
    owners = {str(row[0]): str(row[1]) for row in owner_rows}
    if set(owners) != BASELINE_TABLE_NAMES:
        raise BaselineAdoptionError("canonical baseline owner catalog is incomplete")
    if any(owner != expected_owner for owner in owners.values()):
        raise BaselineAdoptionError("canonical baseline physical owner mismatch")

    acl_rows = bind.execute(
        text(
            "SELECT table_name, grantee, privilege_type, is_grantable "
            "FROM information_schema.role_table_grants "
            "WHERE table_schema = current_schema() AND table_name = ANY(:names) "
            "ORDER BY table_name, grantee, privilege_type, is_grantable"
        ),
        {"names": sorted(BASELINE_TABLE_NAMES)},
    ).all()
    canonical_acl = [
        [str(value) for value in row]
        for row in acl_rows
    ]
    actual_acl_sha256 = hashlib.sha256(
        json.dumps(
            canonical_acl,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if actual_acl_sha256 != expected_acl_sha256:
        raise BaselineAdoptionError("canonical baseline ACL fingerprint mismatch")

    # Read only existence/readability; no row or secret value is returned.
    for table_name in sorted(BASELINE_TABLE_NAMES):
        bind.execute(text(f'SELECT 1 FROM "{table_name}" LIMIT 1')).all()
