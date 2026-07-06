"""
PortSlayer interactive TUI — powered by Textual.

Launch with a bare ``portslayer`` (no subcommand). Navigate with arrow keys,
type to fuzzy-filter, press a single key to kill — no memorizing flags.
"""

from __future__ import annotations

from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Static

from .core import PortInfo, PortScanner, ProcessKiller
from .utils import is_admin

REFRESH_INTERVAL = 3.0

COLUMNS = ("Port", "Proto", "State", "PID", "Process", "Local Address", "Remote Address")


def _state_style(state: str) -> str:
    s = state.upper()
    if "LISTEN" in s:
        return "bold green"
    if "ESTABLISHED" in s:
        return "cyan"
    if "TIME_WAIT" in s or "CLOSE" in s:
        return "yellow"
    return "white"


class ConfirmKillScreen(ModalScreen[bool]):
    """Modal asking the user to confirm a kill before acting."""

    BINDINGS = [
        Binding("y", "confirm", "Confirm"),
        Binding("n,escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ConfirmKillScreen {
        align: center middle;
    }
    #dialog {
        width: 64;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    #dialog .title {
        text-style: bold;
        color: $error;
    }
    #dialog .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, entries: list[PortInfo]) -> None:
        super().__init__()
        self._entries = entries

    def compose(self) -> ComposeResult:
        pids = sorted({e.pid for e in self._entries if e.pid > 0})
        names = ", ".join(sorted({e.process_name for e in self._entries}))
        lines = "\n".join(
            f"  • port {e.port}/{e.protocol}  pid {e.pid}  {e.process_name}"
            for e in self._entries
        )
        with Vertical(id="dialog"):
            yield Static("Kill process?", classes="title")
            yield Static(f"{lines}\n\nPID(s): {', '.join(str(p) for p in pids)}  ({names})")
            yield Static("[y] confirm kill    [n / esc] cancel", classes="hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class PortSlayerApp(App[None]):
    """Full-screen interactive dashboard for inspecting and killing ports."""

    TITLE = "PortSlayer"
    SUB_TITLE = "↑↓ navigate · / search · k kill · r refresh · q quit"

    CSS = """
    Screen {
        layout: vertical;
    }
    #search {
        dock: top;
        display: none;
    }
    #search.visible {
        display: block;
    }
    DataTable {
        height: 1fr;
    }
    #status {
        dock: bottom;
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_now", "Refresh"),
        Binding("k,delete", "kill_selected", "Kill"),
        Binding("slash", "toggle_search", "Search"),
        Binding("escape", "clear_search", "Clear search", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._scanner = PortScanner()
        self._killer = ProcessKiller()
        self._all_entries: list[PortInfo] = []
        self._filter_text: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        search = Input(placeholder="filter by port, process, protocol or state…", id="search")
        search.can_focus = False
        yield search
        yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*COLUMNS)
        if not is_admin():
            self._set_status(
                "[yellow]Warning: run as Administrator/root to see all processes.[/]"
            )
        self.refresh_ports()
        self.set_interval(REFRESH_INTERVAL, self.refresh_ports)
        table.focus()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def refresh_ports(self) -> None:
        self._all_entries = self._scanner.list_ports()
        self._render_table()

    def action_refresh_now(self) -> None:
        self.refresh_ports()
        self._set_status("Refreshed.")

    def _filtered_entries(self) -> list[PortInfo]:
        q = self._filter_text.strip().lower()
        if not q:
            return self._all_entries
        out = []
        for e in self._all_entries:
            haystack = f"{e.port} {e.protocol} {e.state} {e.pid} {e.process_name} {e.local_address}".lower()
            if q in haystack:
                out.append(e)
        return out

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        prev_row = table.cursor_row
        table.clear()
        entries = self._filtered_entries()
        for e in entries:
            table.add_row(
                str(e.port),
                e.protocol,
                f"[{_state_style(e.state)}]{e.state}[/]",
                str(e.pid) if e.pid else "—",
                e.process_name,
                e.local_address,
                e.remote_address,
                key=str(id(e)),
            )
        self._visible_entries = entries
        if entries:
            table.move_cursor(row=min(prev_row, len(entries) - 1))
        self._set_status(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} shown")

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def action_toggle_search(self) -> None:
        search = self.query_one("#search", Input)
        if search.has_class("visible"):
            search.remove_class("visible")
            search.can_focus = False
            self.query_one(DataTable).focus()
        else:
            search.add_class("visible")
            search.can_focus = True
            search.focus()

    def action_clear_search(self) -> None:
        search = self.query_one("#search", Input)
        search.value = ""
        self._filter_text = ""
        search.remove_class("visible")
        search.can_focus = False
        self._render_table()
        self.query_one(DataTable).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self._filter_text = event.value
            self._render_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search":
            self.query_one(DataTable).focus()

    # ------------------------------------------------------------------
    # Kill
    # ------------------------------------------------------------------

    def action_kill_selected(self) -> None:
        table = self.query_one(DataTable)
        entries = getattr(self, "_visible_entries", [])
        if not entries or table.cursor_row is None or table.cursor_row >= len(entries):
            self._set_status("[yellow]No process selected.[/]")
            return

        selected = entries[table.cursor_row]
        matching = [e for e in entries if e.port == selected.port and e.protocol == selected.protocol]

        def handle_result(confirmed: Optional[bool]) -> None:
            if not confirmed:
                self._set_status("Kill cancelled.")
                return
            results = self._killer.kill_by_port(matching)
            ok = [r for r in results if r.success]
            fail = [r for r in results if not r.success]
            msg = f"[green]Killed {len(ok)} process(es).[/]" if ok else ""
            if fail:
                msg += f" [red]{len(fail)} failed: {fail[0].message}[/]"
            self._set_status(msg or "Nothing to kill.")
            self.refresh_ports()

        self.push_screen(ConfirmKillScreen(matching), handle_result)


def run_tui() -> None:
    PortSlayerApp().run()


if __name__ == "__main__":
    run_tui()
