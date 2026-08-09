from __future__ import annotations

from backend.script.bootstrap_postgres_roles import RoleNames, _dream_tables


def test_role_names_are_non_login_and_domain_specific() -> None:
    roles = RoleNames.from_prefix("ink_r46_test")
    assert roles.all() == (
        "ink_r46_test_admin_migration",
        "ink_r46_test_admin_runtime",
        "ink_r46_test_dream_migration",
        "ink_r46_test_dream_runtime",
    )


def test_role_bootstrap_uses_exact_dream_43_plus_5_manifest() -> None:
    tables = _dream_tables()
    assert len(tables) == 49
    assert "users" in tables
    assert "story_workspace_workspaces" in tables
    assert "story_workspace_stories" in tables
    assert "connector_resources" in tables
    assert "dream_alembic_version" in tables
