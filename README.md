# Pardus Package Manager Add-On Tool

# **Status: Stable**

A desktop and terminal tool for **Pardus Linux** that installs and removes
additional package-management *ecosystems* — Flatpak, Snap, Nix, Homebrew, and
EPkg.

It does **not** manage application packages. It manages the package managers
themselves, so a user can pick the ecosystem that fits their needs without
hunting through documentation or pasting shell one-liners blindly.

> "Choose the package ecosystem that best fits your needs."

## What it does

- Detects which package managers are already installed
- Explains each one before you commit to anything
- Installs or removes them **one at a time**, only on explicit request
- Always confirms before changing the system
- Logs every action to screen and to a file
- Offers the same backend behind a **TUI** and a **GUI**

It never installs everything automatically and never runs a destructive command
without confirmation.

## Supported package managers

| Manager  | Source of truth                         | Privilege |
|----------|-----------------------------------------|-----------|
| Flatpak  | Pardus apt repositories + Flathub remote| root      |
| Snap     | Pardus apt repositories (`snapd`)       | root      |
| Nix      | Official multi-user installer           | mixed     |
| Homebrew | Official installer (runs as your user)  | user      |
| EPkg     | ENux-Distro repository (single script)         | root      |

## Requirements

- Python 3.11+
- **GUI:** GTK 4 via PyGObject — on Pardus install the system packages:
  ```bash
  sudo apt install python3-gi gir1.2-gtk-4.0
  ```
- **TUI:** [Textual](https://textual.textualize.io/) (pip)
- `pkexec` (preferred) or `sudo` for privileged operations

### Setup

The simplest path is the Makefile (`make help` lists every target):

```bash
make dev          # set up a local venv (./.venv) for development
```

This creates a venv with `--system-site-packages` so the system GTK bindings
stay available while Textual is installed alongside them.

## Installation

### Installation From the Git Cloned Repository

```bash
make install      # copy to /usr/share/pardus-pm and link `pardus-pm` into /usr/bin
```

Override the prefix or stage into a packaging root:

```bash
make install PREFIX=/usr/local
make install DESTDIR=/tmp/pkg SUDO=   # unprivileged staging for packaging
```

### Installation via the .deb Package

```bash
wget https://github.com/ENux-Distro/Pardus_PM_Add-on/releases/download/Pardus_PM_Add-on/pardus-pm-add-on_amd64.deb      # Downloads the .deb package
sudo apt install ./pardus-pm-add-on_amd64.deb      # Installs the .deb package via apt using sudo
```

### Manual dev setup (without make)

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

## Running

```bash
make run                   # TUI (default)
make gui                   # graphical UI
```

Or call the launcher directly for the headless subcommands:

```bash
./bin/pardus-pm            # TUI (default)
./bin/pardus-pm tui        # text UI
./bin/pardus-pm gui        # graphical UI
./bin/pardus-pm status     # JSON detection report, no UI
./bin/pardus-pm install flatpak   # headless single operation
./bin/pardus-pm remove  flatpak
```

## pardus-pmm — cross-manager package search

`pardus-pmm` is a companion TUI (same look as the pardus-pm text UI) that drives
all the installed package ecosystems from one place — inspired by Bedrock
Linux's `pmm`. A left-hand menu picks the operation and the main area adapts:

```bash
make pmm            # or: ./bin/pardus-pmm
```

| Operation | What it does                                                        |
|-----------|---------------------------------------------------------------------|
| Search    | Query every search-capable manager at once; results are tagged by manager (`[APT]`, `[Flatpak]`, …). Highlight one and press `i` to install it from that manager. |
| Install   | Type a package, pick a manager, press `i`.                          |
| Remove    | Type a package, pick a manager, press `r`.                          |
| Update    | Press `u` to refresh package metadata across all capable managers.  |
| Upgrade   | Press `u` to upgrade everything installed across all capable managers. |

Searches and operations run in the background, so a slow network manager never
blocks the others. Only managers present on the system are offered, and only for
the operations they support.

| Manager  | search | install | remove | update | upgrade |
|----------|:------:|:-------:|:------:|:------:|:-------:|
| APT      | ✓ | ✓ | ✓ | ✓ | ✓ |
| Flatpak  | ✓ | ✓ | ✓ | ✓ | ✓ |
| Snap     | ✓ | ✓ | ✓ | ✓ | ✓ |
| Nix      | ✓ | ✓ | ✓ | ✓ | ✓ |
| Homebrew | ✓ | ✓ | ✓ | ✓ | ✓ |
| EPkg     |   | ✓ |   |   |   |

| Key         | Action                                          |
|-------------|-------------------------------------------------|
| ↑ / ↓       | Move within the focused list                    |
| `Enter`     | Dive into the highlighted operation / run search|
| `i`         | Install (search result or typed package)        |
| `r`         | Remove the typed package                        |
| `u`         | Run Update / Upgrade across all listed managers |
| `q` / `Esc` | Exit                                            |

> **EPkg note:** EPkg supports install only, and its `install` syntax is a
> best-effort guess in [`parduspm/search.py`](parduspm/search.py); adjust it to
> match your actual `epkg` build.

### Desktop integration (menu + taskbar icon)

The GUI sets its own Pardus icon at runtime, so it no longer shows the generic
Python icon when launched directly. To get the icon and a launcher in your
application menu and taskbar, install the user-level entry (no root):

```bash
./packaging/install-user.sh
```

This copies the icon to `~/.local/share/icons/hicolor` and a `.desktop` file
(with `Exec` pointing at this checkout) to `~/.local/share/applications`. A
panel restart or re-login may be needed for the taskbar icon to refresh.

### TUI keys

| Key        | Action               |
|------------|----------------------|
| ↑ / ↓      | Move selection       |
| `i`        | Install highlighted  |
| `r`        | Remove highlighted   |
| `Enter`    | Show details         |
| `q` / `Esc`| Exit                 |

## Language (Turkish / English)

Both tools are bilingual. The language is chosen automatically from the locale:
a locale starting with `tr` (e.g. `tr_TR.UTF-8`) shows Turkish, everything else
falls back to English. Force it explicitly with `PARDUS_PM_LANG`:

```bash
PARDUS_PM_LANG=tr ./bin/pardus-pm      # Türkçe
PARDUS_PM_LANG=en ./bin/pardus-pm      # English
```

Translations live in [`parduspm/i18n.py`](parduspm/i18n.py) — a small dict-based
table (no gettext/`.mo` build step), covering UI strings, status words, package
descriptions, and the main activity-log messages.

## Architecture

```
parduspm/            shared backend (no UI code)
  registry.py        static definitions of each package manager + its steps
  backend.py         detection, privilege escalation, streaming execution
  search.py          cross-manager package search + per-manager install (pmm)
  i18n.py            locale-based Turkish / English translations
  logger.py          activity log (in-memory ring + file + live subscribers)
  __main__.py        CLI dispatcher (tui / gui / status / install / remove)
tui/app.py           Textual text UI for pardus-pm
tui/pmm.py           Textual text UI for pardus-pmm (cross-manager search)
gui/app.py           GTK 4 graphical UI
tests/               unit tests (no real system changes)
bin/pardus-pm        launcher for the management tool
bin/pardus-pmm       launcher for the cross-manager search TUI
```

Both frontends depend only on `parduspm.backend`. The backend is the single
place where privileged commands run and where the "one manager at a time, only
on request" guarantee lives. Each install/remove procedure is a list of
explicit `Step` objects (argv tokens, never shell strings unless marked), which
keeps the supported set easy to audit.

### Privilege model

- `Privilege.ROOT` steps are wrapped in `pkexec` (or `sudo`) when not already root.
- `Privilege.USER` steps (Homebrew) are dropped back to the invoking user with
  `runuser` if the tool itself was launched as root.
- If a root step is needed and no escalation tool exists, the operation is
  refused with a clear message instead of failing halfway.

## Logging

Activity is written to `$XDG_STATE_HOME/pardus-pm/activity.log`
(default `~/.local/state/pardus-pm/activity.log`) and shown live in both UIs:

```
[12:03:41] Detected Flatpak
[12:03:42] User requested installation of Homebrew
[12:04:10] Homebrew installed successfully
```

## Tests

```bash
make test
```

The tests stub command execution and privilege checks, so they never modify the
system.

## Notes and caveats

- **Nix** and **Homebrew** use their official network installers; they require
  internet access and are best-effort to remove cleanly. A reboot is
  recommended after installing or removing Nix.
- **Snap** is not pre-configured on Pardus; `snapd` is pulled from the repos.
- The tool assumes an apt-based base system (Pardus/Debian).
