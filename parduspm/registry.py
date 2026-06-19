"""Static definitions of the package managers this tool can manage.

This module is pure data: it knows *what* each package manager is and *how*
to detect / install / remove it, but it never runs anything itself. The
backend (see ``backend.py``) is responsible for execution. Keeping the two
separate makes the supported-set easy to audit and extend.

Each command step is a list of argv tokens (never a shell string) so that we
never pass user-influenced data through a shell. A step also declares how it
must be run via the ``Privilege`` enum.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Privilege(enum.Enum):
    """How a single command step must be executed."""

    ROOT = "root"            # must run as root (apt, writing to /usr/bin, ...)
    USER = "user"            # must run as the unprivileged invoking user (Homebrew)
    PLAIN = "plain"          # run as whoever launched the tool, no escalation


@dataclass(frozen=True)
class Step:
    """A single command in an install or remove procedure."""

    argv: list[str]
    privilege: Privilege = Privilege.ROOT
    # Some official installers (Homebrew, Nix) read from a piped script and
    # need a shell. We allow an explicit shell step but keep it opt-in and
    # visible rather than hiding shell usage everywhere.
    shell: bool = False
    description: str = ""


@dataclass(frozen=True)
class PackageManager:
    id: str
    name: str
    description: str
    features: list[str]
    # Detection: a command name to resolve on PATH, and/or absolute paths that
    # indicate the manager is installed. Either matching means "installed".
    detect_command: str | None = None
    detect_paths: list[str] = field(default_factory=list)
    install_steps: list[Step] = field(default_factory=list)
    remove_steps: list[Step] = field(default_factory=list)
    # Free-form caveats shown to the user before they commit to an action.
    notes: str = ""


# ---------------------------------------------------------------------------
# Supported package managers
# ---------------------------------------------------------------------------
# Pardus is Debian-based, so apt/dpkg are assumed present and used for the
# managers that ship in the distribution repositories (Flatpak, Snap).

FLATPAK = PackageManager(
    id="flatpak",
    name="Flatpak",
    description=(
        "Flatpak is a sandboxed application distribution system commonly used "
        "for desktop applications. It provides isolation and cross-distribution "
        "compatibility."
    ),
    features=[
        "Sandboxed desktop applications",
        "Cross-distribution compatibility",
        "Per-application permissions",
    ],
    detect_command="flatpak",
    install_steps=[
        Step(["apt-get", "install", "-y", "flatpak"],
             description="Install the flatpak package"),
        Step(["flatpak", "remote-add", "--if-not-exists", "flathub",
              "https://flathub.org/repo/flathub.flatpakrepo"],
             description="Add the Flathub remote"),
    ],
    remove_steps=[
        Step(["apt-get", "remove", "-y", "--purge", "flatpak"],
             description="Remove the flatpak package"),
        Step(["apt-get", "autoremove", "-y"],
             description="Remove now-unused dependencies"),
    ],
    notes="A reboot or re-login is recommended so Flathub apps appear in your menu.",
)

SNAP = PackageManager(
    id="snap",
    name="Snap",
    description=(
        "Snap is Canonical's application packaging system. Applications are "
        "distributed as self-contained packages and are updated automatically."
    ),
    features=[
        "Self-contained packages",
        "Automatic background updates",
        "Confined runtime",
    ],
    detect_command="snap",
    detect_paths=["/usr/bin/snap"],
    install_steps=[
        Step(["apt-get", "install", "-y", "snapd"],
             description="Install snapd"),
        Step(["systemctl", "enable", "--now", "snapd.socket"],
             description="Enable and start the snapd socket"),
    ],
    remove_steps=[
        Step(["systemctl", "disable", "--now", "snapd.socket"],
             description="Stop and disable the snapd socket"),
        Step(["apt-get", "remove", "-y", "--purge", "snapd"],
             description="Remove snapd"),
        Step(["apt-get", "autoremove", "-y"],
             description="Remove now-unused dependencies"),
    ],
    notes="Snap is not pre-configured on Pardus; snapd is pulled from the repositories.",
)

NIX = PackageManager(
    id="nix",
    name="Nix",
    description=(
        "Nix is a reproducible package manager that allows multiple package "
        "versions and declarative system configurations."
    ),
    features=[
        "Reproducible builds",
        "Multiple versions side by side",
        "Declarative configuration",
    ],
    detect_command="nix",
    detect_paths=["/nix/var/nix/profiles/default/bin/nix"],
    install_steps=[
        # A previous Nix install leaves *.backup-before-nix copies; the
        # installer aborts if one already exists. Restore each backup over its
        # original first, which clears the stale backup and gives the installer
        # a clean rc file to work from. (Needs root to write under /etc.)
        Step(["sh", "-c",
              "for f in /etc/bash.bashrc /etc/bashrc /etc/zshrc /etc/profile "
              "/etc/zsh/zshrc /etc/zsh/zprofile; do "
              "[ -e \"$f.backup-before-nix\" ] && mv -f \"$f.backup-before-nix\" \"$f\"; "
              "done; true"],
             privilege=Privilege.ROOT, shell=True,
             description="Clear any stale Nix backups of shell rc files"),
        # Official multi-user installer. --daemon for a system-wide install,
        # --yes to skip the interactive confirmation.
        Step(["sh", "-c",
              "curl -L https://nixos.org/nix/install | sh -s -- --daemon --yes"],
             privilege=Privilege.PLAIN, shell=True,
             description="Run the official Nix multi-user installer"),
    ],
    remove_steps=[
        Step(["systemctl", "stop", "nix-daemon.socket", "nix-daemon.service"],
             description="Stop the nix daemon"),
        Step(["systemctl", "disable", "nix-daemon.socket", "nix-daemon.service"],
             description="Disable the nix daemon"),
        Step(["sh", "-c",
              "rm -rf /nix /etc/nix /etc/profile.d/nix.sh /etc/profile.d/nix.sh.backup-before-nix "
              "/root/.nix-profile /root/.nix-defexpr /root/.nix-channels"],
             shell=True,
             description="Remove the Nix store and configuration"),
        # The installer copies each shell rc file to *.backup-before-nix before
        # editing it. Restore the backup over the original where one exists --
        # this both undoes Nix's edits and clears the backup, so a later
        # reinstall does not abort complaining the backup is already there.
        Step(["sh", "-c",
              "for f in /etc/bash.bashrc /etc/bashrc /etc/zshrc /etc/profile "
              "/etc/zsh/zshrc /etc/zsh/zprofile; do "
              "[ -e \"$f.backup-before-nix\" ] && mv -f \"$f.backup-before-nix\" \"$f\"; "
              "done; true"],
             shell=True,
             description="Restore shell rc files from Nix's pre-install backups"),
    ],
    notes=(
        "Nix uses the official network installer and creates /nix plus system "
        "users (nixbld*). Install first clears stale *.backup-before-nix files so "
        "the installer does not abort. Removal is best-effort; a reboot is "
        "recommended afterwards."
    ),
)

HOMEBREW = PackageManager(
    id="homebrew",
    name="Homebrew",
    description=(
        "Homebrew is a cross-platform package manager originally developed for "
        "macOS and now available on Linux."
    ),
    features=[
        "Large formula collection",
        "Installs under /home/linuxbrew",
        "No root required at runtime",
    ],
    detect_command="brew",
    detect_paths=[
        "/home/linuxbrew/.linuxbrew/bin/brew",
        # also covers per-user installs under ~/.linuxbrew (resolved at runtime)
    ],
    install_steps=[
        # Homebrew refuses to run as root; it must run as the invoking user.
        Step(["bash", "-c",
              'NONINTERACTIVE=1 /bin/bash -c '
              '"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'],
             privilege=Privilege.USER, shell=True,
             description="Run the official Homebrew installer as your user"),
        # The installer does not put brew on PATH; add `brew shellenv` to the
        # user's shell startup files (idempotently) so `brew` works in new
        # shells without manual setup.
        Step(["sh", "-c",
              'BREW=/home/linuxbrew/.linuxbrew/bin/brew; '
              '[ -x "$BREW" ] || BREW="$HOME/.linuxbrew/bin/brew"; '
              'for f in "$HOME/.bashrc" "$HOME/.profile"; do '
              'touch "$f"; '
              'grep -qF "brew shellenv" "$f" || '
              'printf \'\\neval "$(%s shellenv)"\\n\' "$BREW" >> "$f"; '
              'done'],
             privilege=Privilege.USER, shell=True,
             description="Add Homebrew to your shell PATH"),
    ],
    remove_steps=[
        Step(["bash", "-c",
              'NONINTERACTIVE=1 /bin/bash -c '
              '"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"'],
             privilege=Privilege.USER, shell=True,
             description="Run the official Homebrew uninstaller as your user"),
        # Drop the `brew shellenv` line we added on install, so removed shells
        # don't error trying to eval a now-missing brew.
        Step(["sh", "-c",
              'for f in "$HOME/.bashrc" "$HOME/.profile"; do '
              '[ -f "$f" ] && sed -i "/brew shellenv/d" "$f"; done; true'],
             privilege=Privilege.USER, shell=True,
             description="Remove Homebrew from your shell PATH"),
    ],
    notes=("Homebrew must be installed and removed as a normal user, never as root. "
           "Install adds `brew shellenv` to your ~/.bashrc and ~/.profile."),
)

EPKG = PackageManager(
    id="epkg",
    name="EPkg",
    description=(
        "EPkg is a source-based package manager developed for the ENux "
        "ecosystem."
    ),
    features=[
        "Source-based package installation",
        "Seven-mirror support",
        "Lightweight implementation",
    ],
    detect_command="epkg",
    detect_paths=["/usr/bin/epkg"],
    install_steps=[
        Step(["wget",
              "https://raw.githubusercontent.com/ENux-Distro/epkg/refs/heads/main/epkg",
              "-O", "/usr/bin/epkg"],
             description="Download the epkg script to /usr/bin"),
        Step(["chmod", "+x", "/usr/bin/epkg"],
             description="Make epkg executable"),
    ],
    remove_steps=[
        Step(["sh", "-c", "rm -rf /usr/bin/epkg /tmp/epkg*"], shell=True,
             description="Remove epkg and its temporary files"),
    ],
    notes="EPkg is a single self-contained script fetched from the ENux repository.",
)


ALL: list[PackageManager] = [FLATPAK, SNAP, NIX, HOMEBREW, EPKG]
BY_ID: dict[str, PackageManager] = {pm.id: pm for pm in ALL}
