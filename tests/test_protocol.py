from pathlib import Path

from resting_task.config import load_config
from resting_task.protocol import build_schedule


def test_schedule_contains_only_real_marker_labels():
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))

    schedule = build_schedule(cfg.protocol)

    assert [event.label for event in schedule] == [
        "task_start",
        "instructed_toOpenEyes",
        "instructed_toCloseEyes",
        "instructed_toOpenEyes",
        "instructed_toCloseEyes",
        "instructed_toOpenEyes",
        "instructed_toCloseEyes",
        "instructed_toOpenEyes",
        "instructed_toCloseEyes",
        "instructed_toOpenEyes",
        "instructed_toCloseEyes",
        "task_end",
    ]


def test_schedule_uses_condition_onsets_only():
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))

    schedule = build_schedule(cfg.protocol)

    assert [event.onset for event in schedule] == [
        0.0,
        2.0,
        22.0,
        62.0,
        82.0,
        122.0,
        142.0,
        182.0,
        202.0,
        242.0,
        262.0,
        302.0,
    ]
    assert schedule[-1].label == "task_end"
    assert schedule[-1].onset == 302.0
    assert not any("clean" in event.label for event in schedule)
