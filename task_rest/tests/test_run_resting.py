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


def test_run_task_emits_repeated_instruction_markers():
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))
    schedule = build_schedule(cfg.protocol)
    outlet = _FakeOutlet()
    sound_module = _FakeSoundModule()
    visual_module = _FakeVisualModule()
    core_module = _FakeCoreModule()

    run_resting.run_task(
        cfg,
        schedule,
        outlet,
        {
            "visual": visual_module,
            "core": core_module,
            "event": _FakeEventModule(),
            "sound": sound_module,
        },
    )

    labels = [payload.label for payload in outlet.payloads]
    assert labels.count("instructed_toOpenEyes") == 5
    assert labels.count("instructed_toCloseEyes") == 5
    assert labels == [event.label for event in schedule]
    assert sound_module.play_counts[str(cfg.audio.open_eyes)] == 5
    assert sound_module.play_counts[str(cfg.audio.close_eyes)] == 5
    assert "實驗結束" in visual_module.drawn_texts
    assert 3.0 in core_module.waits


class _FakeOutlet:
    def __init__(self):
        self.payloads = []

    def push(self, payload):
        self.payloads.append(payload)


class _FakeClock:
    def __init__(self):
        self.elapsed = 0.0

    def reset(self):
        self.elapsed = 0.0

    def getTime(self):
        self.elapsed += 1.0
        return self.elapsed


class _FakeCoreModule:
    def __init__(self):
        self.waits = []

    Clock = _FakeClock

    def wait(self, seconds):
        self.waits.append(seconds)


class _FakeEventModule:
    @staticmethod
    def getKeys(_keys):
        return []


class _FakeWindow:
    def __init__(self, drawn_texts, **_kwargs):
        self.drawn_texts = drawn_texts
        self.closed = False

    def flip(self):
        return None

    def close(self):
        self.closed = True


class _FakeTextStim:
    def __init__(self, **kwargs):
        self.text = kwargs["text"]
        self.win = kwargs["win"]

    def draw(self):
        self.win.drawn_texts.append(self.text)


class _FakeVisualModule:
    def __init__(self):
        self.drawn_texts = []

    def Window(self, **kwargs):
        return _FakeWindow(self.drawn_texts, **kwargs)

    TextStim = _FakeTextStim


class _FakeSound:
    def __init__(self, path, play_counts):
        self.path = path
        self.play_counts = play_counts

    def stop(self):
        return None

    def play(self):
        self.play_counts[self.path] = self.play_counts.get(self.path, 0) + 1


class _FakeSoundModule:
    def __init__(self):
        self.play_counts = {}

    def Sound(self, path):
        self.play_counts.setdefault(path, 0)
        return _FakeSound(path, self.play_counts)
