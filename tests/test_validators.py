import pytest
from portslayer.utils.validators import validate_port


class TestValidatePort:
    def test_valid_port_int(self):
        ok, msg = validate_port(80)
        assert ok is True
        assert msg == ""

    def test_valid_port_string(self):
        ok, msg = validate_port("8080")
        assert ok is True

    def test_valid_boundary_min(self):
        ok, _ = validate_port(1)
        assert ok is True

    def test_valid_boundary_max(self):
        ok, _ = validate_port(65535)
        assert ok is True

    def test_zero_is_invalid(self):
        ok, msg = validate_port(0)
        assert ok is False
        assert "out of the valid range" in msg

    def test_negative_is_invalid(self):
        ok, _ = validate_port(-1)
        assert ok is False

    def test_above_max_is_invalid(self):
        ok, msg = validate_port(65536)
        assert ok is False
        assert "out of the valid range" in msg

    def test_float_is_invalid(self):
        ok, msg = validate_port(80.5)  # type: ignore[arg-type]
        assert ok is False

    def test_non_numeric_string_is_invalid(self):
        ok, msg = validate_port("http")
        assert ok is False
        assert "not a valid port number" in msg

    def test_empty_string_is_invalid(self):
        ok, _ = validate_port("")
        assert ok is False

    def test_string_with_spaces(self):
        ok, _ = validate_port("  443  ")
        assert ok is True

    @pytest.mark.parametrize("port", [22, 443, 3000, 5432, 8080, 27017])
    def test_common_ports_valid(self, port):
        ok, _ = validate_port(port)
        assert ok is True
