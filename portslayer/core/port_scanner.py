"""
Platform-aware port scanner.

Linux  – primary: ``ss -tulnp``  / fallback: ``lsof -i``
Windows – ``netstat -ano`` + ``tasklist``
macOS   – ``lsof -i -n -P``

All subprocess calls use explicit argument lists — never shell=True —
to prevent command-injection.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Optional

from .models import PortInfo
from ..utils.platform_utils import Platform, get_platform


# ────────────────────────────────────────────────────────────────────────────
# Public interface
# ────────────────────────────────────────────────────────────────────────────


class PortScanner:
    """Collect active port bindings for the current platform."""

    def __init__(self) -> None:
        self._platform = get_platform()

    # ------------------------------------------------------------------
    # Main entry-points
    # ------------------------------------------------------------------

    def list_ports(
        self,
        port: Optional[int] = None,
        port_prefix: Optional[str] = None,
        process: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> list[PortInfo]:
        """Return all active ports, optionally filtered."""
        raw = self._collect()
        return [
            e
            for e in raw
            if e.matches(port=port, port_prefix=port_prefix, process=process, protocol=protocol)
        ]

    def find_port(self, port: int) -> list[PortInfo]:
        """Return every binding on the exact port *port*."""
        return self.list_ports(port=port)

    def find_ports_by_prefix(self, prefix: str) -> list[PortInfo]:
        """Return every binding whose port number starts with *prefix*.

        E.g. prefix "808" matches 8080, 8081, 8083, ...
        """
        return self.list_ports(port_prefix=prefix)

    # ------------------------------------------------------------------
    # Platform dispatch
    # ------------------------------------------------------------------

    def _collect(self) -> list[PortInfo]:
        if self._platform == Platform.LINUX:
            return self._collect_linux()
        if self._platform == Platform.WINDOWS:
            return self._collect_windows()
        if self._platform == Platform.MACOS:
            return self._collect_macos()
        raise RuntimeError(f"Unsupported platform: {self._platform}")

    # ------------------------------------------------------------------
    # Linux
    # ------------------------------------------------------------------

    def _collect_linux(self) -> list[PortInfo]:
        try:
            return self._linux_via_ss()
        except Exception:
            pass
        try:
            return self._linux_via_lsof()
        except Exception:
            return []

    def _linux_via_ss(self) -> list[PortInfo]:
        result = _run(["ss", "-tulnp"])
        return _parse_ss(result.stdout)

    def _linux_via_lsof(self) -> list[PortInfo]:
        result = _run(["lsof", "-i", "-n", "-P"])
        return _parse_lsof(result.stdout)

    # ------------------------------------------------------------------
    # Windows
    # ------------------------------------------------------------------

    def _collect_windows(self) -> list[PortInfo]:
        result = _run(["netstat", "-ano"])
        pid_names = _windows_pid_names()
        return _parse_netstat(result.stdout, pid_names)

    # ------------------------------------------------------------------
    # macOS
    # ------------------------------------------------------------------

    def _collect_macos(self) -> list[PortInfo]:
        result = _run(["lsof", "-i", "-n", "-P"])
        return _parse_lsof(result.stdout)


# ────────────────────────────────────────────────────────────────────────────
# Parsers
# ────────────────────────────────────────────────────────────────────────────


def _parse_ss(output: str) -> list[PortInfo]:
    """
    Parse ``ss -tulnp`` output.

    Example line:
        tcp   LISTEN  0  128  0.0.0.0:22  0.0.0.0:*  users:(("sshd",pid=783,fd=3))
    """
    entries: list[PortInfo] = []
    for line in output.splitlines():
        line = line.strip()
        # Skip header or empty lines
        if not line or line.startswith("Netid"):
            continue

        parts = line.split()
        if len(parts) < 5:
            continue

        proto = parts[0].upper()   # tcp / udp
        state = parts[1].upper() if proto == "TCP" else "—"
        local = parts[4]

        # Extract port from "address:port"
        port = _extract_port(local)
        if port is None:
            continue

        # Extract PID and process name from users:(("name",pid=N,fd=N))
        pid, pname = _parse_ss_process(line)

        entries.append(
            PortInfo(
                port=port,
                pid=pid,
                process_name=pname,
                protocol=proto,
                state=state,
                local_address=local,
                remote_address=parts[5] if len(parts) > 5 else "—",
            )
        )
    return entries


_SS_PROCESS_RE = re.compile(r'users:\(\("([^"]+)",pid=(\d+)')


def _parse_ss_process(line: str) -> tuple[int, str]:
    m = _SS_PROCESS_RE.search(line)
    if m:
        return int(m.group(2)), m.group(1)
    return 0, "—"


def _parse_lsof(output: str) -> list[PortInfo]:
    """
    Parse ``lsof -i -n -P`` output.

    Example line:
        sshd  783  root  3u  IPv4  12345  0t0  TCP  *:22 (LISTEN)
    """
    entries: list[PortInfo] = []
    for line in output.splitlines():
        parts = line.split()
        # Expect at minimum: COMMAND PID USER FD TYPE DEVICE SIZE NODE NAME
        if len(parts) < 9:
            continue
        pname = parts[0]
        try:
            pid = int(parts[1])
        except ValueError:
            continue

        proto = parts[7].upper()  # TCP / UDP
        addr_field = parts[8]

        # State is inside parentheses at the end, e.g. "(LISTEN)"
        state = "—"
        if len(parts) >= 10:
            raw_state = parts[9].strip("()")
            state = raw_state.upper()

        port = _extract_port(addr_field)
        if port is None:
            continue

        entries.append(
            PortInfo(
                port=port,
                pid=pid,
                process_name=pname,
                protocol=proto,
                state=state,
                local_address=addr_field,
            )
        )
    return entries


def _parse_netstat(output: str, pid_names: dict[int, str]) -> list[PortInfo]:
    """
    Parse ``netstat -ano`` on Windows.

    Example line:
        TCP    0.0.0.0:80    0.0.0.0:0    LISTENING    1234
    """
    entries: list[PortInfo] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Active") or line.startswith("Proto"):
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        proto = parts[0].upper()
        local = parts[1]
        remote = parts[2]

        # TCP lines: Proto Local Foreign State PID
        # UDP lines: Proto Local Foreign PID
        if proto == "TCP":
            if len(parts) < 5:
                continue
            state = parts[3].upper()
            try:
                pid = int(parts[4])
            except ValueError:
                continue
        else:  # UDP
            state = "—"
            try:
                pid = int(parts[3])
            except ValueError:
                continue

        port = _extract_port(local)
        if port is None:
            continue

        pname = pid_names.get(pid, "—")

        entries.append(
            PortInfo(
                port=port,
                pid=pid,
                process_name=pname,
                protocol=proto,
                state=state,
                local_address=local,
                remote_address=remote,
            )
        )
    return entries


# ────────────────────────────────────────────────────────────────────────────
# Windows helpers
# ────────────────────────────────────────────────────────────────────────────


def _windows_pid_names() -> dict[int, str]:
    """Return {pid: process_name} mapping from ``tasklist``."""
    try:
        result = _run(["tasklist", "/FO", "CSV", "/NH"])
        names: dict[int, str] = {}
        for line in result.stdout.splitlines():
            line = line.strip().strip('"')
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2:
                try:
                    names[int(parts[1])] = parts[0]
                except ValueError:
                    pass
        return names
    except Exception:
        return {}


# ────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ────────────────────────────────────────────────────────────────────────────


def _extract_port(addr: str) -> Optional[int]:
    """
    Extract the port number from strings like:
        0.0.0.0:8080  [::]:443  *:22  :::8080
    Returns None if no port can be parsed.
    """
    # IPv6 bracket notation: [::1]:8080
    m = re.search(r"\]:(\d+)$", addr)
    if m:
        return int(m.group(1))
    # IPv4 / wildcard: 0.0.0.0:8080 or *:22
    m = re.search(r":(\d+)$", addr)
    if m:
        return int(m.group(1))
    return None


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run *cmd* safely (no shell) and return the completed process."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15,
    )
