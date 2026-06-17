"""Text User Interface for the Pardus Package Manager Add-On Tool.

Built with Textual. The aesthetic is deliberately plain and keyboard-driven --
a 1990s UNIX administration feel: a list of package managers on the left, a
details/description pane, an activity log, and a footer of key bindings.

Keyboard:
  Up / Down   move selection
  i           install the highlighted package manager
  r           remove the highlighted package manager
  enter       show details (focuses the description)
  q / Esc     quit
"""

from __future__ import annotations

import threading

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Footer, Header, Label, ListItem, ListView, Log, Static,
)

from parduspm import registry
from parduspm.backend import Backend, Status
from parduspm.logger import ActivityLog, Entry


class PMRow(ListItem):
    """One package manager line: name on the left, status on the right."""

    def __init__(self, pm, status: Status):
        super().__init__()
        self.pm = pm
        self.status = status

    def compose(self) -> ComposeResult:
        marker = "●" if self.status is Status.INSTALLED else "○"
        klass = "installed" if self.status is Status.INSTALLED else "absent"
        yield Static(
            f"{marker} {self.pm.name:<12} [{self.status.value}]",
            classes=klass,
        )


class ConfirmScreen(ModalScreen[bool]):
    """Modal confirmation dialog required before any system change."""

    def __init__(self, title: str, message: str, confirm_label: str):
        super().__init__()
        self._title = title
        self._message = message
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, id="dialog-title")
            yield Static(self._message, id="dialog-message")
            with Horizontal(id="dialog-buttons"):
                yield Button(self._confirm_label, variant="primary", id="ok")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "ok")


class PardusPMApp(App):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #list-pane { width: 34; border: round $accent; }
    #detail-pane { width: 1fr; border: round $accent; padding: 0 1; }
    #log-pane { height: 10; border: round $accent; }
    .installed { color: $success; }
    .absent { color: $text-muted; }
    #pm-list { height: 1fr; }
    #detail-title { text-style: bold; color: $warning; }
    #dialog {
        width: 60; height: auto; padding: 1 2;
        border: thick $warning; background: $surface;
    }
    #dialog-title { text-style: bold; color: $warning; width: 100%; }
    #dialog-message { margin: 1 0; }
    #dialog-buttons { height: auto; align: center middle; }
    #dialog-buttons Button { margin: 0 1; }
    """

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("i", "install", "Install"),
        ("r", "remove", "Remove"),
        ("enter", "details", "Details"),
        ("q", "quit", "Exit"),
        ("escape", "quit", "Exit"),
    ]

    TITLE = "Pardus Package Manager Add-On Tool"

    def __init__(self):
        super().__init__()
        self.activity = ActivityLog()
        self.backend = Backend(self.activity)
        self.statuses: dict[str, Status] = {}
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="list-pane"):
                yield Label("Package Managers", classes="installed")
                yield ListView(id="pm-list")
            with Vertical(id="detail-pane"):
                yield Static("", id="detail-title")
                yield Static("", id="detail-body")
        with Vertical(id="log-pane"):
            yield Label("Activity Log")
            yield Log(id="activity", highlight=False)
        yield Footer()

    def on_mount(self) -> None:
        # Forward backend log entries into the on-screen activity panel.
        self.activity.subscribe(self._on_log_entry)
        self.refresh_list(detect_quiet=False)

    # -- data --------------------------------------------------------------

    def refresh_list(self, *, detect_quiet: bool = True) -> None:
        self.statuses = self.backend.detect_all(quiet=detect_quiet)
        lv = self.query_one("#pm-list", ListView)
        index = lv.index or 0
        lv.clear()
        for pm in registry.ALL:
            lv.append(PMRow(pm, self.statuses[pm.id]))
        lv.index = min(index, len(registry.ALL) - 1)
        self._show_details()

    def _current_pm(self):
        lv = self.query_one("#pm-list", ListView)
        item = lv.highlighted_child
        return item.pm if isinstance(item, PMRow) else None

    def _show_details(self) -> None:
        pm = self._current_pm()
        if not pm:
            return
        status = self.statuses[pm.id].value
        self.query_one("#detail-title", Static).update(f"{pm.name}  —  {status}")
        features = "\n".join(f"  • {f}" for f in pm.features)
        note = f"\n\nNote: {pm.notes}" if pm.notes else ""
        self.query_one("#detail-body", Static).update(
            f"{pm.description}\n\nFeatures:\n{features}{note}"
        )

    def _on_log_entry(self, entry: Entry) -> None:
        # Subscribers may fire on the app thread (detection during mount) or a
        # worker thread (during install/remove). Only marshal when off-thread.
        write = self.query_one("#activity", Log).write_line
        if threading.get_ident() == self._thread_id:
            write(entry.formatted())
            return
        self.call_from_thread(write, entry.formatted())

    # -- actions -----------------------------------------------------------

    def action_cursor_up(self) -> None:
        self.query_one("#pm-list", ListView).action_cursor_up()
        self._show_details()

    def action_cursor_down(self) -> None:
        self.query_one("#pm-list", ListView).action_cursor_down()
        self._show_details()

    def on_list_view_highlighted(self, _: ListView.Highlighted) -> None:
        self._show_details()

    def action_details(self) -> None:
        self._show_details()

    def action_install(self) -> None:
        self._operate("install")

    def action_remove(self) -> None:
        self._operate("remove")

    def _operate(self, action: str) -> None:
        if self._busy:
            return
        pm = self._current_pm()
        if not pm:
            return

        installed = self.statuses[pm.id] is Status.INSTALLED
        if action == "install" and installed:
            self.activity.info(f"{pm.name} is already installed")
            return
        if action == "remove" and not installed:
            self.activity.info(f"{pm.name} is not installed")
            return

        title = "Install Package Manager" if action == "install" else "Remove Package Manager"
        verb = "install" if action == "install" else "remove"
        prep = "on" if action == "install" else "from"
        message = f"You are about to {verb} {pm.name} {prep} this system.\n\nContinue?"
        label = "Install" if action == "install" else "Remove"

        def after_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self._run_in_background(pm, action)

        self.push_screen(ConfirmScreen(title, message, label), after_confirm)

    def _run_in_background(self, pm, action: str) -> None:
        self._busy = True

        def worker() -> None:
            log = self.query_one("#activity", Log)
            fn = self.backend.install if action == "install" else self.backend.remove
            fn(pm, on_line=lambda line: self.call_from_thread(log.write_line, f"    {line}"))
            self._busy = False
            self.call_from_thread(self.refresh_list)

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    PardusPMApp().run()


if __name__ == "__main__":
    main()
