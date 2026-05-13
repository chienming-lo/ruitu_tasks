from pathlib import Path

from resting_task.config import load_config
from resting_task.protocol import build_schedule
from resting_task import run_resting
from resting_task.run_resting import _print_schedule


def test_dry_run_schedule_output(capsys):
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))
    schedule = build_schedule(cfg.protocol)

    _print_schedule(schedule)

    assert capsys.readouterr().out == (
        "000.000s task_start task\n"
        "002.000s instructed_toOpenEyes eyes_open\n"
        "022.000s instructed_toCloseEyes eyes_closed\n"
        "062.000s instructed_toOpenEyes eyes_open\n"
        "082.000s instructed_toCloseEyes eyes_closed\n"
        "122.000s instructed_toOpenEyes eyes_open\n"
        "142.000s instructed_toCloseEyes eyes_closed\n"
        "182.000s instructed_toOpenEyes eyes_open\n"
        "202.000s instructed_toCloseEyes eyes_closed\n"
        "242.000s instructed_toOpenEyes eyes_open\n"
        "262.000s instructed_toCloseEyes eyes_closed\n"
        "302.000s task_end task\n"
    )


def test_main_dry_run_does_not_load_psychopy_or_create_lsl_outlet(monkeypatch, capsys):
    def fail_if_called():
        raise AssertionError("dry-run must not load PsychoPy")

    def fail_if_outlet_created(_cfg):
        raise AssertionError("dry-run must not create an LSL outlet")

    monkeypatch.setattr(
        "sys.argv",
        ["run_resting", "--config", "configs/resting_hbn_inspired.yaml", "--dry-run"],
    )
    monkeypatch.setattr(run_resting, "_load_psychopy", fail_if_called)
    monkeypatch.setattr(run_resting, "_create_marker_outlet", fail_if_outlet_created)

    assert run_resting.main() == 0
    assert "instructed_toCloseEyes" in capsys.readouterr().out
