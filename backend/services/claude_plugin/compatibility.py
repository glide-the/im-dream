"""Real SemVer parsing and range checks for plugin compatibility.

Compatibility declarations (e.g. platform-builtin source config) use ranges
like ``>=1.0.0 <2.0.0``.  Comparisons here are true SemVer comparisons — never
environment booleans standing in for version judgment.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_VERSION_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)
_CLAUSE_RE = re.compile(r"^(>=|<=|>|<|=|!=)?\s*(\S+)$")


@dataclass(frozen=True, order=False)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    @classmethod
    def parse(cls, text: str) -> "SemVer":
        match = _VERSION_RE.match(text.strip())
        if not match:
            raise ValueError(f"not a SemVer string: {text!r}")
        prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=prerelease,
        )

    def _key(self) -> tuple:
        # SemVer §11: prerelease < same-core release; numeric identifiers
        # compare numerically and sort before alphanumeric ones; a larger
        # identifier set sorts after a smaller prefix.
        if not self.prerelease:
            return (self.major, self.minor, self.patch, 1)
        identifiers = tuple(
            (0, int(part)) if part.isdigit() else (1, part)
            for part in self.prerelease
        )
        return (self.major, self.minor, self.patch, 0, identifiers)

    def __lt__(self, other: "SemVer") -> bool:
        return self._key() < other._key()

    def __le__(self, other: "SemVer") -> bool:
        return self._key() <= other._key()

    def __gt__(self, other: "SemVer") -> bool:
        return self._key() > other._key()

    def __ge__(self, other: "SemVer") -> bool:
        return self._key() >= other._key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += "-" + ".".join(self.prerelease)
        return base


def version_satisfies(version: str, range_expr: str) -> bool:
    """Return True when *version* satisfies a space-separated clause list.

    Supported clauses: ``>=`` ``<=`` ``>`` ``<`` ``=`` ``!=`` followed by a
    SemVer.  Example: ``">=1.0.0 <2.0.0"``.  An empty range matches anything.
    """
    parsed_version = SemVer.parse(version)
    expr = range_expr.strip()
    if not expr:
        return True
    for clause in expr.split():
        match = _CLAUSE_RE.match(clause)
        if not match:
            raise ValueError(f"invalid range clause: {clause!r}")
        operator = match.group(1) or "="
        bound = SemVer.parse(match.group(2))
        if operator == ">=" and not parsed_version >= bound:
            return False
        if operator == "<=" and not parsed_version <= bound:
            return False
        if operator == ">" and not parsed_version > bound:
            return False
        if operator == "<" and not parsed_version < bound:
            return False
        if operator == "=" and not parsed_version == bound:
            return False
        if operator == "!=" and not parsed_version != bound:
            return False
    return True


def cli_version_to_semver(cli_version_output: str) -> str:
    """Extract ``X.Y.Z`` from a ``claude --version`` line.

    Example: ``"2.1.220 (Claude Code)"`` → ``"2.1.220"``.
    """
    match = re.search(r"(\d+\.\d+\.\d+)", cli_version_output)
    if not match:
        raise ValueError(f"cannot parse CLI version: {cli_version_output!r}")
    return match.group(1)
