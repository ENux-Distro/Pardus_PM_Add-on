"""Cross-package-manager operations for pardus-pmm.

Each package ecosystem is described by a :class:`PackageSource` that knows how
to perform a set of operations: search, install, remove, update (refresh the
package metadata) and upgrade (update everything installed). Not every manager
supports every operation -- EPkg, for example, only supports install -- so each
operation is optional and the UI only offers the ones a manager declares.

Inspired by Bedrock Linux's pmm, but each manager's syntax is defined here
directly rather than via external configuration.

Output formats differ wildly between managers, so each source carries its own
search parser. Where a manager offers a machine-readable format we use it (nix
``--json``, flatpak ``--columns``); otherwise we parse defensively and degrade
to "name only" rather than guess.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from .registry import Privilege, Step

OPERATIONS = ["search", "install", "remove", "update", "upgrade"]


@dataclass(frozen=True)
class SearchResult:
    source_id: str       # which manager (apt, flatpak, ...)
    source_name: str     # human label
    name: str            # display name
    install_id: str      # token passed to the install command
    version: str
    description: str


@dataclass(frozen=True)
class PackageSource:
    id: str
    name: str
    command: str                                   # binary used to detect availability
    install_steps: Callable[[str], list[Step]]     # the one operation every manager has
    search_argv: Callable[[str], list[str]] | None = None
    parse: Callable[["PackageSource", str], list[SearchResult]] | None = None
    remove_steps: Callable[[str], list[Step]] | None = None
    update_steps: Callable[[], list[Step]] | None = None
    upgrade_steps: Callable[[], list[Step]] | None = None
    # Absolute paths to check when the command is not on PATH. Needed for
    # managers like Homebrew that deliberately stay off PATH after install.
    detect_paths: list[str] = field(default_factory=list)
    notes: str = ""

    def resolve(self) -> str | None:
        """Return the runnable path to this manager, or None if not installed."""
        found = shutil.which(self.command)
        if found:
            return found
        for path in self.detect_paths:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                return expanded
        return None

    def supports(self, operation: str) -> bool:
        if operation == "search":
            return self.search_argv is not None and self.parse is not None
        if operation == "install":
            return True
        if operation == "remove":
            return self.remove_steps is not None
        if operation == "update":
            return self.update_steps is not None
        if operation == "upgrade":
            return self.upgrade_steps is not None
        return False


# ---------------------------------------------------------------------------
# Search parsers (small and defensive; a malformed line is skipped, not fatal)
# ---------------------------------------------------------------------------

def _parse_apt(src: PackageSource, text: str) -> list[SearchResult]:
    out = []
    for line in text.splitlines():
        if " - " not in line:
            continue
        name, _, desc = line.partition(" - ")
        name = name.strip()
        if name:
            out.append(SearchResult(src.id, src.name, name, name, "", desc.strip()))
    return out


def _parse_flatpak(src: PackageSource, text: str) -> list[SearchResult]:
    # `flatpak search --columns=name,description,application,version` -> TSV.
    out = []
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 3 or not cols[0].strip():
            continue
        name, desc, appid = cols[0].strip(), cols[1].strip(), cols[2].strip()
        version = cols[3].strip() if len(cols) > 3 else ""
        out.append(SearchResult(src.id, src.name, name, appid, version, desc))
    return out


def _parse_snap(src: PackageSource, text: str) -> list[SearchResult]:
    # `snap find` columns: Name Version Publisher Notes Summary (Summary last).
    out = []
    lines = text.splitlines()
    for line in lines[1:] if lines and lines[0].startswith("Name") else lines:
        parts = line.split(None, 4)
        if len(parts) < 1 or not parts[0]:
            continue
        name = parts[0]
        version = parts[1] if len(parts) > 1 else ""
        desc = parts[4] if len(parts) > 4 else ""
        out.append(SearchResult(src.id, src.name, name, name, version, desc))
    return out


def _parse_nix(src: PackageSource, text: str) -> list[SearchResult]:
    # `nix search ... --json` -> {attr_path: {pname, version, description}}.
    out = []
    try:
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError:
        return out
    for key, info in data.items():
        # key looks like "legacyPackages.x86_64-linux.<attr...>"; the install
        # token is everything after the system component.
        parts = key.split(".", 2)
        attr = parts[2] if len(parts) == 3 else key
        out.append(SearchResult(
            src.id, src.name,
            info.get("pname") or attr, attr,
            info.get("version", ""), info.get("description", ""),
        ))
    return out


def _parse_brew(src: PackageSource, text: str) -> list[SearchResult]:
    # `brew search` prints names, sometimes under "==> Formulae"/"==> Casks".
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("==>"):
            continue
        for name in line.split():
            out.append(SearchResult(src.id, src.name, name, name, "", ""))
    return out


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

SOURCES: list[PackageSource] = [
    PackageSource(
        id="apt", name="APT", command="apt-cache",
        search_argv=lambda t: ["apt-cache", "search", t],
        parse=_parse_apt,
        install_steps=lambda p: [Step(["apt-get", "install", "-y", p], Privilege.ROOT,
                                      description=f"apt install {p}")],
        remove_steps=lambda p: [Step(["apt-get", "remove", "-y", "--purge", p], Privilege.ROOT,
                                     description=f"apt remove {p}")],
        update_steps=lambda: [Step(["apt-get", "update"], Privilege.ROOT, description="apt update")],
        upgrade_steps=lambda: [
            Step(["apt-get", "update"], Privilege.ROOT, description="apt update"),
            Step(["apt-get", "upgrade", "-y"], Privilege.ROOT, description="apt upgrade"),
        ],
    ),
    PackageSource(
        id="flatpak", name="Flatpak", command="flatpak",
        search_argv=lambda t: ["flatpak", "search",
                               "--columns=name,description,application,version", t],
        parse=_parse_flatpak,
        install_steps=lambda p: [Step(["flatpak", "install", "-y", "--user", "flathub", p],
                                      Privilege.USER, description=f"flatpak install {p}")],
        remove_steps=lambda p: [Step(["flatpak", "uninstall", "-y", "--user", p],
                                     Privilege.USER, description=f"flatpak uninstall {p}")],
        update_steps=lambda: [Step(["flatpak", "update", "--appstream"], Privilege.USER,
                                   description="flatpak appstream refresh")],
        upgrade_steps=lambda: [Step(["flatpak", "update", "-y"], Privilege.USER,
                                    description="flatpak update")],
    ),
    PackageSource(
        id="snap", name="Snap", command="snap",
        search_argv=lambda t: ["snap", "find", t],
        parse=_parse_snap,
        install_steps=lambda p: [Step(["snap", "install", p], Privilege.ROOT,
                                      description=f"snap install {p}")],
        remove_steps=lambda p: [Step(["snap", "remove", p], Privilege.ROOT,
                                     description=f"snap remove {p}")],
        update_steps=lambda: [Step(["snap", "refresh", "--list"], Privilege.PLAIN,
                                   description="snap list refreshable")],
        upgrade_steps=lambda: [Step(["snap", "refresh"], Privilege.ROOT, description="snap refresh")],
    ),
    PackageSource(
        id="nix", name="Nix", command="nix",
        search_argv=lambda t: ["nix", "--extra-experimental-features", "nix-command flakes",
                               "search", "nixpkgs", t, "--json"],
        parse=_parse_nix,
        install_steps=lambda p: [Step(["nix", "--extra-experimental-features", "nix-command flakes",
                                       "profile", "install", f"nixpkgs#{p}"],
                                      Privilege.USER, description=f"nix profile install {p}")],
        remove_steps=lambda p: [Step(["nix", "--extra-experimental-features", "nix-command flakes",
                                      "profile", "remove", p],
                                     Privilege.USER, description=f"nix profile remove {p}")],
        update_steps=lambda: [Step(["nix-channel", "--update"], Privilege.USER,
                                   description="nix-channel update")],
        upgrade_steps=lambda: [Step(["nix", "--extra-experimental-features", "nix-command flakes",
                                     "profile", "upgrade", "--all"],
                                    Privilege.USER, description="nix profile upgrade")],
    ),
    PackageSource(
        id="homebrew", name="Homebrew", command="brew",
        search_argv=lambda t: ["brew", "search", t],
        parse=_parse_brew,
        install_steps=lambda p: [Step(["brew", "install", p], Privilege.USER,
                                      description=f"brew install {p}")],
        remove_steps=lambda p: [Step(["brew", "uninstall", p], Privilege.USER,
                                     description=f"brew uninstall {p}")],
        update_steps=lambda: [Step(["brew", "update"], Privilege.USER, description="brew update")],
        upgrade_steps=lambda: [Step(["brew", "upgrade"], Privilege.USER, description="brew upgrade")],
        # Homebrew does not put itself on PATH after install.
        detect_paths=["/home/linuxbrew/.linuxbrew/bin/brew", "~/.linuxbrew/bin/brew"],
    ),
    PackageSource(
        # EPkg only supports install -- no search, remove, update, or upgrade.
        id="epkg", name="EPkg", command="epkg",
        install_steps=lambda p: [Step(["epkg", "install", p], Privilege.ROOT,
                                      description=f"epkg install {p}")],
        notes="EPkg supports install only; its syntax is a best-effort guess.",
    ),
]

BY_ID: dict[str, PackageSource] = {s.id: s for s in SOURCES}


class SearchEngine:
    def __init__(self, backend, timeout: int = 60):
        self.backend = backend
        self.timeout = timeout

    def sources_for(self, operation: str) -> list[PackageSource]:
        """Installed managers that support the given operation."""
        return [s for s in SOURCES if s.resolve() and s.supports(operation)]

    def _resolve_argv(self, source: PackageSource, argv: list[str]) -> list[str]:
        """Replace a bare command name with its absolute path (e.g. brew)."""
        path = source.resolve()
        if path and argv and argv[0] == source.command:
            return [path, *argv[1:]]
        return argv

    def search_one(self, source: PackageSource, term: str) -> list[SearchResult]:
        """Run one manager's search. Network/parse errors yield no results."""
        if not source.supports("search"):
            return []
        try:
            proc = subprocess.run(
                self._resolve_argv(source, source.search_argv(term)),
                capture_output=True, text=True, timeout=self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        return source.parse(source, proc.stdout)

    def _steps_for(self, source: PackageSource, operation: str, pkg: str) -> list[Step] | None:
        if operation == "install":
            return source.install_steps(pkg)
        if operation == "remove" and source.remove_steps:
            return source.remove_steps(pkg)
        if operation == "update" and source.update_steps:
            return source.update_steps()
        if operation == "upgrade" and source.upgrade_steps:
            return source.upgrade_steps()
        return None

    def run_op(self, source: PackageSource, operation: str, pkg: str = "", on_line=None) -> tuple[bool, str]:
        steps = self._steps_for(source, operation, pkg)
        if not steps:
            return False, f"{source.name} does not support {operation}."
        # Run by absolute path when the manager is not on PATH (e.g. Homebrew).
        steps = [replace(s, argv=self._resolve_argv(source, s.argv)) for s in steps]
        label = f"{operation.capitalize()} via {source.name}" + (f": {pkg}" if pkg else "")
        return self.backend.run_steps(label, steps, on_line)

    def install(self, result: SearchResult, on_line=None) -> tuple[bool, str]:
        return self.run_op(BY_ID[result.source_id], "install", result.install_id, on_line)
