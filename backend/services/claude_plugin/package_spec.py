"""Package-spec parsing and validation for Claude Code plugins.

A package spec has the form ``<plugin-name>@<marketplace-name>`` — exactly the
shape accepted by ``claude plugin install`` (verified against Claude Code
2.1.220).  Validation is intentionally strict: specs become argv elements of a
real subprocess call and registry keys, so shell metacharacters, whitespace,
path separators and traversal segments are rejected outright.  An optional
third ``@<version>`` segment records a *requested* version hint; the resolved
version always comes from the real CLI install result, never from the hint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Marketplace/plugin names observed in the wild: kebab-case tokens such as
# ``superpowers`` and ``claude-plugins-official``.  Allow alphanumerics, dot,
# underscore and dash; forbid everything else (no shell metacharacters, no
# path separators, no whitespace).
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# Loose SemVer (optional leading v, optional pre-release/build metadata).
_VERSION_PATTERN = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)


class PackageSpecError(ValueError):
    """Raised when a package spec fails validation."""


@dataclass(frozen=True)
class PackageSpec:
    package_name: str
    marketplace: str
    requested_version: str | None = None

    @property
    def canonical(self) -> str:
        return f"{self.package_name}@{self.marketplace}"

    @property
    def install_argv_spec(self) -> str:
        """The exact argv element passed to ``claude plugin install``."""
        return self.canonical


def _validate_name(value: str, *, label: str) -> str:
    if not _NAME_PATTERN.match(value):
        raise PackageSpecError(
            f"invalid {label} {value!r}: only letters, digits, '.', '_' and '-' "
            "are allowed, and the value must start with a letter or digit"
        )
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise PackageSpecError(f"invalid {label} {value!r}: path segments are not allowed")
    return value


def parse_package_spec(raw: str) -> PackageSpec:
    """Parse and validate ``<plugin>@<marketplace>[@<version>]``.

    Raises :class:`PackageSpecError` for malformed input.  Callers must treat
    the exception message as user-facing (it contains no shell payload).
    """
    if not isinstance(raw, str):
        raise PackageSpecError("package spec must be a string")
    text = raw.strip()
    if not text:
        raise PackageSpecError("package spec must not be empty")
    if len(text) > 300:
        raise PackageSpecError("package spec is too long")
    # Reject any character that could smuggle shell syntax even though we
    # never use a shell; defense in depth for logging and registry keys.
    for ch in text:
        if ch.isspace() or ch in ";&|`$<>\\\"'!#%*?[]{}()~\n\r":
            raise PackageSpecError(
                f"package spec contains forbidden character {ch!r}"
            )
    parts = text.split("@")
    if len(parts) not in (2, 3) or any(not part for part in parts):
        raise PackageSpecError(
            "package spec must have the form <plugin>@<marketplace>[@<version>]"
        )
    name = _validate_name(parts[0], label="plugin name")
    marketplace = _validate_name(parts[1], label="marketplace name")
    version: str | None = None
    if len(parts) == 3:
        candidate = parts[2]
        if not _VERSION_PATTERN.match(candidate):
            raise PackageSpecError(
                f"invalid requested version {candidate!r}: expected SemVer"
            )
        version = candidate.lstrip("v")
    return PackageSpec(
        package_name=name,
        marketplace=marketplace,
        requested_version=version,
    )
