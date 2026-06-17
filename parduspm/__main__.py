"""Command-line entry point and dispatcher.

Usage:
  python -m parduspm tui        launch the text UI (default)
  python -m parduspm gui        launch the graphical UI
  python -m parduspm status     print detection status as JSON and exit
  python -m parduspm install <id> | remove <id>
                                run a single operation headless (JSON result)

The headless subcommands exist so the same backend can be scripted or tested
without a UI. They still perform exactly one operation at a time.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import registry
from .backend import Backend


def _cmd_status(backend: Backend) -> int:
    statuses = backend.detect_all(quiet=True)
    out = {
        pm.id: {"name": pm.name, "status": statuses[pm.id].value}
        for pm in registry.ALL
    }
    print(json.dumps(out, indent=2))
    return 0


def _cmd_operate(backend: Backend, action: str, pm_id: str) -> int:
    pm = registry.BY_ID.get(pm_id)
    if not pm:
        print(json.dumps({"ok": False, "message": f"Unknown package manager: {pm_id}"}))
        return 2
    fn = backend.install if action == "install" else backend.remove
    result = fn(pm, on_line=lambda line: print(line, file=sys.stderr))
    print(result.to_json())
    return 0 if result.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pardus-pm", description="Pardus Package Manager Add-On Tool")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("tui", help="launch the text UI (default)")
    sub.add_parser("gui", help="launch the graphical UI")
    sub.add_parser("status", help="print detection status as JSON")
    for action in ("install", "remove"):
        p = sub.add_parser(action, help=f"{action} a single package manager")
        p.add_argument("id", choices=list(registry.BY_ID))

    args = parser.parse_args(argv)
    command = args.command or "tui"

    if command == "tui":
        from tui.app import main as tui_main
        tui_main()
        return 0
    if command == "gui":
        from gui.app import main as gui_main
        gui_main()
        return 0

    backend = Backend()
    if command == "status":
        return _cmd_status(backend)
    return _cmd_operate(backend, command, args.id)


if __name__ == "__main__":
    raise SystemExit(main())
