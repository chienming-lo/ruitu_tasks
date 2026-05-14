from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_gp3_lsl():
    module_path = Path(__file__).resolve().parents[1] / "tools" / "GP3_lsl.py"
    spec = importlib.util.spec_from_file_location("gp3_lsl", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_record_returns_formal_gaze_and_pupil_channels_in_order():
    gp3_lsl = _load_gp3_lsl()
    message = (
        '<REC TIME="12.50000" FPOGX="0.40000" FPOGY="0.60000" '
        'FPOGS="12.00000" FPOGD="0.50000" FPOGID="42" FPOGV="1" '
        'BPOGX="0.41000" BPOGY="0.61000" BPOGV="1" '
        'LPMM="3.10000" LPMMV="1" RPMM="3.20000" RPMMV="1" />\r\n'
    )

    assert gp3_lsl.parse_record(message) == [
        12.5,
        0.4,
        0.6,
        12.0,
        0.5,
        42.0,
        1.0,
        0.41,
        0.61,
        1.0,
        3.1,
        1.0,
        3.2,
        1.0,
    ]


def test_parse_record_defaults_missing_optional_values_to_zero():
    gp3_lsl = _load_gp3_lsl()

    assert gp3_lsl.parse_record('<REC TIME="1.0" FPOGX="0.5" />\r\n') == [
        1.0,
        0.5,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]


def test_parse_record_ignores_non_record_messages():
    gp3_lsl = _load_gp3_lsl()

    assert gp3_lsl.parse_record('<ACK ID="ENABLE_SEND_DATA" STATE="1" />\r\n') is None
    assert gp3_lsl.parse_record("not xml\r\n") is None
