"""Text UI for pardus-pmm -- cross-package-manager operations.

Same look and feel as the pardus-pm TUI. A left-hand menu selects the
operation; the main area adapts to it:

  Search    type a query, every search-capable manager is queried, pick a
            result and press 'i' to install it from that manager
  Install   type a package, pick a manager, press 'i'
  Remove    type a package, pick a manager, press 'r'
  Update    refresh package metadata across all capable managers ('u')
  Upgrade   upgrade everything installed across all capable managers ('u')

Keyboard:
  up / down    move within the focused list (modes, results, managers)
  enter        dive into the highlighted mode / run a search
  i            install (search result, or typed package in Install mode)
  r            remove the typed package (Remove mode)
  u            run Update / Upgrade across all listed managers
  q / Esc      quit
"""

from __future__ import annotations

import threading

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    ContentSwitcher, Footer, Header, Input, Label, ListItem, ListView, Log, Static,
)

from parduspm import i18n
from parduspm.backend import Backend
from parduspm.logger import ActivityLog, Entry
from parduspm.search import SearchEngine, SearchResult, PackageSource, BY_ID

from tui.app import ConfirmScreen

MODES = [
    ("search", i18n.t("op_search")),
    ("install", i18n.t("op_install")),
    ("remove", i18n.t("op_remove")),
    ("update", i18n.t("op_update")),
    ("upgrade", i18n.t("op_upgrade")),
]


class ResultRow(ListItem):
    """One search hit: [manager] name version."""

    def __init__(self, result: SearchResult):
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        r = self.result
        version = f" {r.version}" if r.version else ""
        # markup=False so the literal "[APT]" tag is not parsed as Textual markup.
        yield Static(f"[{r.source_name:<8}] {r.name}{version}", markup=False)


class ManagerRow(ListItem):
    """One package manager available for the current operation."""

    def __init__(self, source: PackageSource):
        super().__init__()
        self.source = source

    def compose(self) -> ComposeResult:
        yield Static(f"● {self.source.name}", markup=False)


class PardusPMMApp(App):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #modes-pane { width: 16; border: round $accent; }
    #modes { height: 1fr; }
    #main { width: 1fr; border: round $accent; padding: 0 1; }
    #log-pane { height: 8; border: round $accent; }
    .pkg-input { margin: 0 0 1 0; }
    .hint { color: $text-muted; }
    #results { height: 1fr; }
    #search-detail { width: 44; padding: 0 1; }
    #detail-title { text-style: bold; color: $warning; }
    ListView { height: auto; max-height: 1fr; }
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
        ("i", "install", i18n.t("install")),
        ("r", "remove", i18n.t("remove")),
        ("u", "run_all", i18n.t("update_upgrade")),
        ("q", "quit", i18n.t("exit")),
        ("escape", "quit", i18n.t("exit")),
    ]

    TITLE = i18n.t("pmm_title")

    def __init__(self):
        super().__init__()
        self.activity = ActivityLog()
        self.backend = Backend(self.activity)
        self.engine = SearchEngine(self.backend)
        self.mode = "search"
        self.results: list[SearchResult] = []
        self._searching = False
        self._busy = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="modes-pane"):
                yield Label(i18n.t("operations"))
                yield ListView(*[ListItem(Label(name)) for _, name in MODES], id="modes")
            with ContentSwitcher(initial="search", id="main"):
                # Search
                with Horizontal(id="search"):
                    with Vertical():
                        yield Input(placeholder=i18n.t("search_placeholder"), id="search-input",
                                    classes="pkg-input")
                        yield ListView(id="results")
                    with Vertical(id="search-detail"):
                        yield Static("", id="detail-title")
                        yield Static(i18n.t("type_query"), id="detail-body")
                # Install
                with Vertical(id="install"):
                    yield Input(placeholder=i18n.t("install_placeholder"), id="install-input",
                                classes="pkg-input")
                    yield Label(i18n.t("pick_manager_i"), classes="hint")
                    yield ListView(id="install-mgrs")
                # Remove
                with Vertical(id="remove"):
                    yield Input(placeholder=i18n.t("remove_placeholder"), id="remove-input",
                                classes="pkg-input")
                    yield Label(i18n.t("pick_manager_r"), classes="hint")
                    yield ListView(id="remove-mgrs")
                # Update
                with Vertical(id="update"):
                    yield Label(i18n.t("update_hint"), classes="hint")
                    yield ListView(id="update-mgrs")
                # Upgrade
                with Vertical(id="upgrade"):
                    yield Label(i18n.t("upgrade_hint"), classes="hint")
                    yield ListView(id="upgrade-mgrs")
        with Vertical(id="log-pane"):
            yield Label(i18n.t("activity_log"))
            yield Log(id="activity", highlight=False)
        yield Footer()

    def on_mount(self) -> None:
        self.activity.subscribe(self._on_log_entry)
        for op in ("install", "remove", "update", "upgrade"):
            self._populate_managers(op)
        names = ", ".join(s.name for s in self.engine.sources_for("search")) or "—"
        self.activity.info(i18n.t("search_capable", names=names))
        self.query_one("#modes", ListView).focus()

    def _populate_managers(self, op: str) -> None:
        lv = self.query_one(f"#{op}-mgrs", ListView)
        lv.clear()
        sources = self.engine.sources_for(op)
        for s in sources:
            lv.append(ManagerRow(s))
        if sources:
            lv.index = 0

    # -- mode switching ----------------------------------------------------

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "modes":
            idx = event.list_view.index or 0
            self.mode = MODES[idx][0]
            self.query_one("#main", ContentSwitcher).current = self.mode
            return
        if event.list_view.id == "results":
            self._show_result_details()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Enter on the modes menu dives into that mode's primary widget.
        if event.list_view.id != "modes":
            return
        focus_targets = {
            "search": "#search-input", "install": "#install-input",
            "remove": "#remove-input", "update": "#update-mgrs", "upgrade": "#upgrade-mgrs",
        }
        target = self.query_one(focus_targets[self.mode])
        target.focus()

    # -- search ------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            term = event.value.strip()
            if term and not self._searching:
                self._run_search(term)
            return
        # In install/remove, Enter just moves focus to the manager list.
        if event.input.id == "install-input":
            self.query_one("#install-mgrs", ListView).focus()
        elif event.input.id == "remove-input":
            self.query_one("#remove-mgrs", ListView).focus()

    def _run_search(self, term: str) -> None:
        self._searching = True
        self.results = []
        self.query_one("#results", ListView).clear()
        sources = self.engine.sources_for("search")
        self.activity.action(i18n.t("searching", n=len(sources), term=term))

        def worker() -> None:
            for source in sources:
                hits = self.engine.search_one(source, term)
                self.call_from_thread(self._add_results, source.name, hits)
            self._searching = False
            self.call_from_thread(self._search_done, term)

        threading.Thread(target=worker, daemon=True).start()

    def _add_results(self, source_name: str, hits: list[SearchResult]) -> None:
        self.activity.info(i18n.t("results_count", name=source_name, n=len(hits)))
        lv = self.query_one("#results", ListView)
        for r in hits:
            self.results.append(r)
            lv.append(ResultRow(r))
        if lv.index is None and self.results:
            lv.index = 0
            self._show_result_details()

    def _search_done(self, term: str) -> None:
        self.activity.success(i18n.t("search_complete", n=len(self.results), term=term))

    def _show_result_details(self) -> None:
        item = self.query_one("#results", ListView).highlighted_child
        r = item.result if isinstance(item, ResultRow) else None
        if not r:
            return
        self.query_one("#detail-title", Static).update(r.name)
        body = i18n.t("d_manager", name=r.source_name) + "\n" + i18n.t("d_install_id", id=r.install_id)
        if r.version:
            body += "\n" + i18n.t("d_version", v=r.version)
        if r.description:
            body += f"\n\n{r.description}"
        body += "\n\n" + i18n.t("d_press_i", name=r.source_name)
        self.query_one("#detail-body", Static).update(body)

    # -- actions -----------------------------------------------------------

    def _highlighted_manager(self, op: str) -> PackageSource | None:
        item = self.query_one(f"#{op}-mgrs", ListView).highlighted_child
        return item.source if isinstance(item, ManagerRow) else None

    def action_install(self) -> None:
        if self._busy:
            return
        if self.mode == "search":
            item = self.query_one("#results", ListView).highlighted_child
            r = item.result if isinstance(item, ResultRow) else None
            if not r:
                return
            source = BY_ID[r.source_id]
            msg = i18n.t("confirm_install_result", name=r.name, id=r.install_id,
                         mgr=r.source_name) + "\n\n" + i18n.t("continue_q")

            def after(confirmed: bool | None) -> None:
                if confirmed:
                    self._run_single(source, "install", r.install_id)

            self.push_screen(ConfirmScreen(i18n.t("dlg_install_pkg"), msg, i18n.t("install")), after)
            return
        if self.mode == "install":
            self._typed_op("install", "install-input", "install-mgrs")

    def action_remove(self) -> None:
        if self._busy or self.mode != "remove":
            return
        self._typed_op("remove", "remove-input", "remove-mgrs")

    def action_run_all(self) -> None:
        if self._busy or self.mode not in ("update", "upgrade"):
            return
        op = self.mode
        sources = self.engine.sources_for(op)
        if not sources:
            self.activity.info(i18n.t("no_manager_supports", op=op))
            return
        names = ", ".join(s.name for s in sources)
        if op == "update":
            title, label = i18n.t("dlg_update_title"), i18n.t("op_update")
            msg = i18n.t("confirm_update_all", names=names) + "\n\n" + i18n.t("continue_q")
        else:
            title, label = i18n.t("dlg_upgrade_title"), i18n.t("op_upgrade")
            msg = i18n.t("confirm_upgrade_all", names=names) + "\n\n" + i18n.t("continue_q")

        def after(confirmed: bool | None) -> None:
            if confirmed:
                self._run_many(op, sources)

        self.push_screen(ConfirmScreen(title, msg, label), after)

    def _typed_op(self, op: str, input_id: str, mgrs_id: str) -> None:
        pkg = self.query_one(f"#{input_id}", Input).value.strip()
        source = self._highlighted_manager(op)
        if not pkg:
            self.activity.info(i18n.t("type_pkg_first"))
            return
        if not source:
            self.activity.info(i18n.t("no_manager_selected"))
            return
        if op == "install":
            title, label = i18n.t("dlg_install_pkg"), i18n.t("install")
            msg = i18n.t("confirm_install_pkg", pkg=pkg, mgr=source.name)
        else:
            title, label = i18n.t("dlg_remove_pkg"), i18n.t("remove")
            msg = i18n.t("confirm_remove_pkg", pkg=pkg, mgr=source.name)
        msg += "\n\n" + i18n.t("continue_q")

        def after(confirmed: bool | None) -> None:
            if confirmed:
                self._run_single(source, op, pkg)

        self.push_screen(ConfirmScreen(title, msg, label), after)

    # -- execution ---------------------------------------------------------

    def _run_single(self, source: PackageSource, op: str, pkg: str) -> None:
        self._busy = True
        log = self.query_one("#activity", Log)

        def worker() -> None:
            self.engine.run_op(source, op, pkg,
                               on_line=lambda l: self.call_from_thread(log.write_line, f"    {l}"))
            self._busy = False

        threading.Thread(target=worker, daemon=True).start()

    def _run_many(self, op: str, sources: list[PackageSource]) -> None:
        self._busy = True
        log = self.query_one("#activity", Log)

        def worker() -> None:
            for source in sources:
                self.engine.run_op(source, op, "",
                                   on_line=lambda l: self.call_from_thread(log.write_line, f"    {l}"))
            self._busy = False

        threading.Thread(target=worker, daemon=True).start()

    # -- logging -----------------------------------------------------------

    def _on_log_entry(self, entry: Entry) -> None:
        write = self.query_one("#activity", Log).write_line
        if threading.get_ident() == self._thread_id:
            write(entry.formatted())
            return
        self.call_from_thread(write, entry.formatted())


def main() -> None:
    PardusPMMApp().run()


if __name__ == "__main__":
    main()
