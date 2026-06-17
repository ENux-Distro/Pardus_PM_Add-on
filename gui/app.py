"""Graphical User Interface for the Pardus Package Manager Add-On Tool.

Built with GTK 4 (PyGObject). The look deliberately mirrors the TUI: a single
monospace, black / yellow / white "terminal" surface with bordered panels,
inverted selection, and bracketed buttons. This keeps one visual identity
across both frontends instead of a half-themed default-GTK window.

Layout (per spec):
  * left panel   -- package manager list
  * center panel -- description and details
  * right panel  -- status and actions
  * bottom       -- activity log
"""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Gdk, Pango  # noqa: E402

from parduspm import registry  # noqa: E402
from parduspm.backend import Backend, Status  # noqa: E402
from parduspm.logger import ActivityLog, Entry  # noqa: E402


# Application id; also the icon name (matches the shipped icon + .desktop file).
APP_ID = "org.pardus.PackageManagerAddon"


# Colours sampled from the TUI's textual-dark theme so both frontends match:
# soft greys (not pure black) with yellow reserved as the single Pardus accent.
PARDUS_CSS = b"""
window, .term {
    background-color: #121212;
    color: #e0e0e0;
    font-family: monospace;
    font-size: 13px;
}
.header {
    color: #121212;
    background-color: #ffd400;
    padding: 8px 14px;
    font-weight: bold;
    font-size: 15px;
}
.panel {
    border: 1px solid #3a3a3a;
    margin: 8px;
    padding: 6px 8px;
    background-color: #1e1e1e;
}
.panel-title { color: #ffd400; font-weight: bold; }
.pm-list { background-color: #1e1e1e; }
.pm-list row { padding: 4px 6px; }
.pm-list label { color: #e0e0e0; }
.pm-list row:selected { background-color: #ffd400; }
.pm-list row:selected label { color: #121212; }
.dot-on  { color: #4ebf71; font-weight: bold; }
.dot-off { color: #808080; }
.detail-title { color: #ffd400; font-weight: bold; font-size: 16px; }
.detail-body  { color: #e0e0e0; }
.status-on  { color: #4ebf71; font-weight: bold; }
.status-off { color: #b0b0b0; }
button.term-btn {
    background-image: none;
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    border-radius: 0;
    padding: 6px 10px;
    font-family: monospace;
    font-weight: bold;
}
button.term-btn:hover { background-color: #343f49; }
button.term-btn:disabled { color: #6a6a6a; border-color: #2a2a2a; }
button.term-btn-primary { color: #ffd400; border-color: #ffd400; }
.dialog {
    background-color: #1e1e1e;
    border: 1px solid #3a3a3a;
    padding: 18px 20px;
}
.dialog .detail-title { margin-bottom: 10px; }
.activity {
    background-color: #1e1e1e;
    color: #4ebf71;
    font-family: monospace;
    padding: 6px;
}
"""


class PardusPMWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="Pardus Package Manager Add-On Tool")
        self.set_default_size(940, 620)

        self.activity = ActivityLog()
        self.backend = Backend(self.activity)
        self.statuses: dict[str, Status] = {}
        self.selected_id: str | None = None
        self._busy = False

        self.activity.subscribe(self._on_log_entry)
        self._build_ui()
        self.refresh(detect_quiet=False)

    # -- UI construction ---------------------------------------------------

    def _build_ui(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.add_css_class("term")
        self.set_child(root)

        header = Gtk.Label(label=" Pardus Package Manager Add-On Tool", xalign=0)
        header.add_css_class("header")
        root.append(header)

        panels = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        root.append(panels)

        panels.append(self._build_list_panel())
        panels.append(self._build_detail_panel())
        panels.append(self._build_action_panel())
        root.append(self._build_log_panel())

    def _panel(self, title: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.add_css_class("panel")
        label = Gtk.Label(label=title, xalign=0)
        label.add_css_class("panel-title")
        box.append(label)
        return box

    def _build_list_panel(self) -> Gtk.Widget:
        panel = self._panel("Package Managers")
        panel.set_size_request(250, -1)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("pm-list")
        self.listbox.connect("row-selected", self._on_row_selected)
        scroll.set_child(self.listbox)
        panel.append(scroll)
        return panel

    def _build_detail_panel(self) -> Gtk.Widget:
        panel = self._panel("Details")
        panel.set_hexpand(True)
        self.detail_title = Gtk.Label(xalign=0)
        self.detail_title.add_css_class("detail-title")
        self.detail_body = Gtk.Label(xalign=0, yalign=0, wrap=True, vexpand=True)
        self.detail_body.add_css_class("detail-body")
        self.detail_body.set_wrap_mode(Pango.WrapMode.WORD)
        panel.append(self.detail_title)
        panel.append(self.detail_body)
        return panel

    def _build_action_panel(self) -> Gtk.Widget:
        panel = self._panel("Status & Actions")
        panel.set_size_request(210, -1)
        self.status_label = Gtk.Label(label="", xalign=0)
        self.install_btn = Gtk.Button(label="[ Install ]")
        self.install_btn.add_css_class("term-btn")
        self.install_btn.connect("clicked", lambda _b: self._operate("install"))
        self.remove_btn = Gtk.Button(label="[ Remove ]")
        self.remove_btn.add_css_class("term-btn")
        self.remove_btn.connect("clicked", lambda _b: self._operate("remove"))
        self.spinner = Gtk.Spinner()
        panel.append(self.status_label)
        panel.append(self.install_btn)
        panel.append(self.remove_btn)
        panel.append(self.spinner)
        return panel

    def _build_log_panel(self) -> Gtk.Widget:
        panel = self._panel("Activity Log")
        panel.set_size_request(-1, 110)
        panel.set_vexpand(False)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.log_view = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        self.log_view.add_css_class("activity")
        self.log_buffer = self.log_view.get_buffer()
        scroll.set_child(self.log_view)
        panel.append(scroll)
        return panel

    # -- data --------------------------------------------------------------

    def refresh(self, *, detect_quiet: bool = True) -> None:
        self.statuses = self.backend.detect_all(quiet=detect_quiet)
        previous = self.selected_id
        child = self.listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt

        target_row = None
        for pm in registry.ALL:
            installed = self.statuses[pm.id] is Status.INSTALLED
            row = Gtk.ListBoxRow()
            row.pm_id = pm.id
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            dot = Gtk.Label(label="●" if installed else "○")
            dot.add_css_class("dot-on" if installed else "dot-off")
            name = Gtk.Label(label=pm.name, xalign=0, hexpand=True)
            box.append(dot)
            box.append(name)
            row.set_child(box)
            self.listbox.append(row)
            if pm.id == previous:
                target_row = row

        if target_row is None:
            target_row = self.listbox.get_row_at_index(0)
        self.listbox.select_row(target_row)

    def _selected_pm(self):
        return registry.BY_ID.get(self.selected_id) if self.selected_id else None

    def _on_row_selected(self, _listbox, row) -> None:
        if row is None:
            return
        self.selected_id = row.pm_id
        self._show_details()

    def _show_details(self) -> None:
        pm = self._selected_pm()
        if not pm:
            return
        installed = self.statuses[pm.id] is Status.INSTALLED
        self.detail_title.set_text(pm.name)
        features = "\n".join(f"  - {f}" for f in pm.features)
        note = f"\n\nNote: {pm.notes}" if pm.notes else ""
        self.detail_body.set_text(f"{pm.description}\n\nFeatures:\n{features}{note}")

        self.status_label.set_text(f"● {self.statuses[pm.id].value}" if installed
                                   else f"○ {self.statuses[pm.id].value}")
        self.status_label.remove_css_class("status-on")
        self.status_label.remove_css_class("status-off")
        self.status_label.add_css_class("status-on" if installed else "status-off")
        self.install_btn.set_sensitive(not installed and not self._busy)
        self.remove_btn.set_sensitive(installed and not self._busy)

    # -- logging -----------------------------------------------------------

    def _on_log_entry(self, entry: Entry) -> None:
        GLib.idle_add(self._append_log, entry.formatted())

    def _append_log(self, text: str) -> bool:
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text + "\n")
        mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
        self.log_view.scroll_mark_onscreen(mark)
        return False

    # -- operations --------------------------------------------------------

    def _operate(self, action: str) -> None:
        pm = self._selected_pm()
        if not pm or self._busy:
            return

        title = "Install Package Manager" if action == "install" else "Remove Package Manager"
        verb = "install" if action == "install" else "remove"
        prep = "on" if action == "install" else "from"
        message = f"You are about to {verb} {pm.name} {prep} this system.\n\nContinue?"
        confirm_label = "Install" if action == "install" else "Remove"

        self._confirm(title, message, confirm_label,
                      lambda: self._run_in_background(pm, action))

    def _confirm(self, title: str, message: str, confirm_label: str, on_ok) -> None:
        """A modal confirmation styled to match the app (not the system dialog)."""
        dialog = Gtk.Window(transient_for=self, modal=True, resizable=False)
        dialog.set_title(title)
        dialog.set_default_size(440, -1)
        dialog.add_css_class("term")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.add_css_class("dialog")
        dialog.set_child(outer)

        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("detail-title")
        body = Gtk.Label(label=message, xalign=0, wrap=True)
        body.set_wrap_mode(Pango.WrapMode.WORD)
        outer.append(heading)
        outer.append(body)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, halign=Gtk.Align.END)
        buttons.set_margin_top(14)
        cancel = Gtk.Button(label="[ Cancel ]")
        cancel.add_css_class("term-btn")
        cancel.connect("clicked", lambda _b: dialog.close())
        ok = Gtk.Button(label=f"[ {confirm_label} ]")
        ok.add_css_class("term-btn")
        ok.add_css_class("term-btn-primary")
        ok.connect("clicked", lambda _b: (dialog.close(), on_ok()))
        buttons.append(cancel)
        buttons.append(ok)
        outer.append(buttons)

        dialog.present()

    def _run_in_background(self, pm, action: str) -> None:
        self._busy = True
        self._show_details()
        self.spinner.start()

        def worker():
            fn = self.backend.install if action == "install" else self.backend.remove
            fn(pm, on_line=lambda line: GLib.idle_add(self._append_log, f"    {line}"))
            GLib.idle_add(self._finish)

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self) -> bool:
        self._busy = False
        self.spinner.stop()
        self.refresh()
        return False


class PardusPMApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        self._install_css()
        self._install_icon()
        win = PardusPMWindow(self)
        win.set_icon_name(APP_ID)
        win.present()

    def _install_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(PARDUS_CSS)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _install_icon(self):
        # Register our shipped icon so the app shows the Pardus mark instead of
        # the generic interpreter icon, even when not installed system-wide.
        display = Gdk.Display.get_default()
        if display is None:
            return
        icons_dir = str(Path(__file__).resolve().parent.parent / "packaging" / "icons")
        Gtk.IconTheme.get_for_display(display).add_search_path(icons_dir)
        Gtk.Window.set_default_icon_name(APP_ID)


def main() -> None:
    PardusPMApplication().run(None)


if __name__ == "__main__":
    main()
