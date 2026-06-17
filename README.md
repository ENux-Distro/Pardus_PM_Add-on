# Pardus Package Manager Add-On Tool

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
| EPkg     | ENux repository (single script)         | root      |

## Requirements

- Python 3.11+
- **GUI:** GTK 4 via PyGObject — on Pardus install the system packages:
  ```bash
  sudo apt install python3-gi gir1.2-gtk-4.0
  ```
- **TUI:** [Textual](https://textual.textualize.io/) (pip)
- `pkexec` (preferred) or `sudo` for privileged operations

### Setup

The repo ships with a virtualenv created with `--system-site-packages` so the
system GTK bindings stay available while Textual is installed in the venv:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
```

## Running

```bash
./bin/pardus-pm            # TUI (default)
./bin/pardus-pm tui        # text UI
./bin/pardus-pm gui        # graphical UI
./bin/pardus-pm status     # JSON detection report, no UI
./bin/pardus-pm install flatpak   # headless single operation
./bin/pardus-pm remove  flatpak
```

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

## Architecture

```
parduspm/            shared backend (no UI code)
  registry.py        static definitions of each package manager + its steps
  backend.py         detection, privilege escalation, streaming execution
  logger.py          activity log (in-memory ring + file + live subscribers)
  __main__.py        CLI dispatcher (tui / gui / status / install / remove)
tui/app.py           Textual text UI
gui/app.py           GTK 4 graphical UI
tests/               backend unit tests (no real system changes)
bin/pardus-pm        launcher (uses .venv if present)
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
.venv/bin/python -m pytest tests/ -q
```

The tests stub command execution and privilege checks, so they never modify the
system.

## Notes and caveats

- **Nix** and **Homebrew** use their official network installers; they require
  internet access and are best-effort to remove cleanly. A reboot is
  recommended after installing or removing Nix.
- **Snap** is not pre-configured on Pardus; `snapd` is pulled from the repos.
- The tool assumes an apt-based base system (Pardus/Debian).
