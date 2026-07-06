"""
PortSlayer CLI — powered by Typer + Rich.

Commands:
  portslayer                   Launch the interactive TUI dashboard
  portslayer list              List all active ports
  portslayer find <port>       Show all bindings matching a port or prefix (e.g. '808' -> 8080/8081/8083)
  portslayer kill <port>       Kill the process(es) bound to an exact port
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from .core import PortInfo, PortScanner, ProcessKiller
from .utils import get_platform, is_admin, validate_port, validate_port_prefix

app = typer.Typer(
    name="portslayer",
    help="[bold cyan]PortSlayer[/] — inspect and kill processes by port.",
    rich_markup_mode="rich",
    no_args_is_help=False,
)

console = Console()
scanner = PortScanner()
killer = ProcessKiller()


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _state_style(state: str) -> str:
    s = state.upper()
    if "LISTEN" in s:
        return "bold green"
    if "ESTABLISHED" in s:
        return "cyan"
    if "TIME_WAIT" in s or "CLOSE" in s:
        return "yellow"
    return "white"


def _build_table(entries: list[PortInfo], title: str = "Active Ports") -> Table:
    table = Table(
        title=title,
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=False,
        expand=False,
    )
    table.add_column("Port", style="bold yellow", justify="right", no_wrap=True)
    table.add_column("Protocol", justify="center")
    table.add_column("State", no_wrap=True)
    table.add_column("PID", justify="right", style="dim")
    table.add_column("Process", style="bold")
    table.add_column("Local Address")
    table.add_column("Remote Address", style="dim")

    for e in entries:
        table.add_row(
            str(e.port),
            e.protocol,
            Text(e.state, style=_state_style(e.state)),
            str(e.pid) if e.pid else "—",
            e.process_name,
            e.local_address,
            e.remote_address,
        )
    return table


class _NullStatus:
    def __enter__(self) -> "_NullStatus":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def _status(message: str, *, quiet: bool = False):
    """Return a Rich status spinner, or a no-op context manager when *quiet*."""
    return _NullStatus() if quiet else console.status(message)


def _print_entries(entries: list[PortInfo], title: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps([e.as_dict() for e in entries], indent=2))
        return
    console.print(_build_table(entries, title=title))


def _abort(msg: str) -> None:
    console.print(f"[bold red]Error:[/] {msg}")
    raise typer.Exit(code=1)


def _check_port_arg(port: int) -> None:
    ok, reason = validate_port(port)
    if not ok:
        _abort(reason)


def _check_port_prefix_arg(port: str) -> None:
    ok, reason = validate_port_prefix(port)
    if not ok:
        _abort(reason)


def _warn_if_no_admin() -> None:
    if not is_admin():
        console.print(
            Panel(
                "[yellow]Warning:[/] Some processes may be hidden without "
                "root / Administrator privileges.",
                expand=False,
                border_style="yellow",
            )
        )


# ────────────────────────────────────────────────────────────────────────────
# Commands
# ────────────────────────────────────────────────────────────────────────────


@app.command("list")
def cmd_list(
    port: Optional[str] = typer.Option(
        None,
        "--port",
        "-p",
        help="Filter by port number or partial prefix, e.g. '808' matches 8080/8081/8083.",
    ),
    process: Optional[str] = typer.Option(None, "--process", "-n", help="Filter by process name."),
    protocol: Optional[str] = typer.Option(
        None, "--protocol", "-P", help="Filter by protocol (tcp|udp)."
    ),
    listening_only: bool = typer.Option(
        False, "--listening", "-l", help="Show only LISTENING ports."
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Output as JSON instead of a table (for scripting)."
    ),
) -> None:
    """List all active ports with process details."""
    if not as_json:
        _warn_if_no_admin()

    if port is not None:
        _check_port_prefix_arg(port)

    if protocol and protocol.upper() not in ("TCP", "UDP"):
        _abort("Protocol must be 'tcp' or 'udp'.")

    with _status("[cyan]Scanning ports…[/]", quiet=as_json):
        entries = scanner.list_ports(port_prefix=port, process=process, protocol=protocol)

    if listening_only:
        entries = [e for e in entries if e.is_listening]

    if not entries and not as_json:
        console.print("[yellow]No matching ports found.[/]")
        raise typer.Exit()

    _print_entries(entries, title=f"Active Ports ({len(entries)} entries)", as_json=as_json)


@app.command("find")
def cmd_find(
    port: str = typer.Argument(
        ...,
        help="Port number or partial prefix to inspect, e.g. '808' matches 8080/8081/8083.",
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Output as JSON instead of a table (for scripting)."
    ),
) -> None:
    """Show all processes bound to ports starting with PORT."""
    _check_port_prefix_arg(port)
    if not as_json:
        _warn_if_no_admin()

    with _status(f"[cyan]Looking up ports matching '{port}'…[/]", quiet=as_json):
        entries = scanner.find_ports_by_prefix(port)

    if not entries and not as_json:
        console.print(f"[yellow]No process found on any port matching '{port}'.[/]")
        raise typer.Exit()

    distinct_ports = sorted({e.port for e in entries})
    title = f"Port {port}" if distinct_ports == [int(port)] else f"Ports matching '{port}' ({len(distinct_ports)} ports)"
    _print_entries(entries, title=title, as_json=as_json)


@app.command("kill")
def cmd_kill(
    port: Optional[int] = typer.Argument(
        None, help="Exact port whose process(es) should be killed."
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Kill by process name instead of port (matches every port that process owns).",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation prompt (use with care)."
    ),
) -> None:
    """Kill the process(es) bound to PORT, or all processes matching --name, after confirmation."""
    if (port is None) == (name is None):
        _abort("Provide exactly one of PORT or --name.")

    _warn_if_no_admin()

    if port is not None:
        _check_port_arg(port)
        with console.status(f"[cyan]Looking up port {port}…[/]"):
            entries = scanner.find_port(port)
        not_found_msg = f"No process found on port {port}."
        title = f"[red]About to kill — Port {port}[/]"
    else:
        with console.status(f"[cyan]Looking up processes named '{name}'…[/]"):
            entries = scanner.list_ports(process=name)
        not_found_msg = f"No process found matching name '{name}'."
        title = f"[red]About to kill — processes matching '{name}'[/]"

    if not entries:
        console.print(f"[yellow]{not_found_msg}[/]")
        raise typer.Exit()

    # Show what will be killed
    console.print(_build_table(entries, title=title))

    unique_pids = {e.pid for e in entries if e.pid > 0}
    pid_summary = ", ".join(str(p) for p in sorted(unique_pids))
    console.print(
        f"\n[bold]PID(s) to terminate:[/] [red]{pid_summary}[/]\n"
    )

    if not force:
        confirmed = Confirm.ask(
            "[bold red]Confirm kill?[/] This cannot be undone",
            default=False,
        )
        if not confirmed:
            console.print("[yellow]Aborted.[/]")
            raise typer.Exit()

    results = killer.kill_by_port(entries)
    for r in results:
        if r.success:
            console.print(f"[bold green]OK[/] {r.message}")
        else:
            console.print(f"[bold red]FAIL[/] {r.message}")

    if not all(r.success for r in results):
        raise typer.Exit(code=1)


# ────────────────────────────────────────────────────────────────────────────
# Version command
# ────────────────────────────────────────────────────────────────────────────


def _version_callback(value: bool) -> None:
    if value:
        from . import __version__
        console.print(f"PortSlayer [bold cyan]{__version__}[/]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """[bold cyan]PortSlayer[/] — cross-platform port inspector and process killer."""
    if ctx.invoked_subcommand is None:
        from .tui import run_tui

        run_tui()


if __name__ == "__main__":
    app()
