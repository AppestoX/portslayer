"""
Tests for the port scanner parsers.

We test the internal parsing functions in isolation so the tests can run
on any platform without real network sockets.
"""

import pytest
from portslayer.core.port_scanner import (
    _extract_port,
    _parse_lsof,
    _parse_netstat,
    _parse_ss,
)


# ────────────────────────────────────────────────────────────────────────────
# _extract_port
# ────────────────────────────────────────────────────────────────────────────


class TestExtractPort:
    def test_ipv4_address(self):
        assert _extract_port("0.0.0.0:8080") == 8080

    def test_ipv4_wildcard(self):
        assert _extract_port("*:22") == 22

    def test_ipv6_bracket(self):
        assert _extract_port("[::]:443") == 443

    def test_ipv6_mapped(self):
        assert _extract_port("[::1]:5432") == 5432

    def test_triple_colon_linux(self):
        # ss sometimes outputs :::8080 for IPv6
        assert _extract_port(":::8080") == 8080

    def test_no_port_returns_none(self):
        assert _extract_port("no_port_here") is None

    def test_empty_string(self):
        assert _extract_port("") is None


# ────────────────────────────────────────────────────────────────────────────
# _parse_ss
# ────────────────────────────────────────────────────────────────────────────

SS_OUTPUT = """\
Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port Process
tcp    LISTEN  0       128     0.0.0.0:22          0.0.0.0:*         users:(("sshd",pid=783,fd=3))
tcp    LISTEN  0       511     [::]:80             [::]:*            users:(("nginx",pid=1042,fd=6))
udp    UNCONN  0       0       0.0.0.0:68          0.0.0.0:*         users:(("dhclient",pid=455,fd=5))
"""


class TestParseSs:
    def setup_method(self):
        self.entries = _parse_ss(SS_OUTPUT)

    def test_correct_count(self):
        assert len(self.entries) == 3

    def test_ssh_entry(self):
        ssh = next(e for e in self.entries if e.port == 22)
        assert ssh.protocol == "TCP"
        assert ssh.state == "LISTEN"
        assert ssh.pid == 783
        assert ssh.process_name == "sshd"

    def test_nginx_entry(self):
        nginx = next(e for e in self.entries if e.port == 80)
        assert nginx.pid == 1042
        assert nginx.process_name == "nginx"

    def test_udp_entry(self):
        dhcp = next(e for e in self.entries if e.port == 68)
        assert dhcp.protocol == "UDP"
        assert dhcp.process_name == "dhclient"

    def test_empty_output(self):
        assert _parse_ss("") == []

    def test_header_only(self):
        assert _parse_ss("Netid State Recv-Q Send-Q Local Address:Port\n") == []


# ────────────────────────────────────────────────────────────────────────────
# _parse_netstat (Windows)
# ────────────────────────────────────────────────────────────────────────────

NETSTAT_OUTPUT = """\

Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:80             0.0.0.0:0              LISTENING       4
  TCP    127.0.0.1:5432         127.0.0.1:50012        ESTABLISHED     1234
  TCP    0.0.0.0:445            0.0.0.0:0              LISTENING       4
  UDP    0.0.0.0:500            *:*                                    888
"""

PID_NAMES = {4: "System", 1234: "postgres.exe", 888: "lsass.exe"}


class TestParseNetstat:
    def setup_method(self):
        self.entries = _parse_netstat(NETSTAT_OUTPUT, PID_NAMES)

    def test_correct_count(self):
        assert len(self.entries) == 4

    def test_http_entry(self):
        http = next(e for e in self.entries if e.port == 80)
        assert http.protocol == "TCP"
        assert http.state == "LISTENING"
        assert http.pid == 4
        assert http.process_name == "System"

    def test_postgres_established(self):
        pg = next(e for e in self.entries if e.port == 5432)
        assert pg.state == "ESTABLISHED"
        assert pg.pid == 1234
        assert pg.process_name == "postgres.exe"

    def test_udp_no_state(self):
        udp = next(e for e in self.entries if e.protocol == "UDP")
        assert udp.state == "—"
        assert udp.pid == 888

    def test_unknown_pid_falls_back(self):
        entry = _parse_netstat(
            "  TCP    0.0.0.0:9999  0.0.0.0:0  LISTENING  9999\n", {}
        )
        assert entry[0].process_name == "—"


# ────────────────────────────────────────────────────────────────────────────
# _parse_lsof
# ────────────────────────────────────────────────────────────────────────────

LSOF_OUTPUT = """\
COMMAND  PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
sshd     783   root   3u   IPv4  12345  0t0      TCP  *:22 (LISTEN)
nginx    1042  www    6u   IPv6  23456  0t0      TCP  *:80 (LISTEN)
python   5678  user   4u   IPv4  34567  0t0      TCP  127.0.0.1:8000 (LISTEN)
"""


class TestParseLsof:
    def setup_method(self):
        self.entries = _parse_lsof(LSOF_OUTPUT)

    def test_correct_count(self):
        assert len(self.entries) == 3

    def test_ssh_entry(self):
        ssh = next(e for e in self.entries if e.port == 22)
        assert ssh.process_name == "sshd"
        assert ssh.pid == 783
        assert ssh.state == "LISTEN"

    def test_python_entry(self):
        py = next(e for e in self.entries if e.port == 8000)
        assert py.process_name == "python"
        assert py.pid == 5678
