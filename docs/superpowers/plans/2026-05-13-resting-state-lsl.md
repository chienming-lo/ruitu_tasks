# Resting State LSL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-runnable PsychoPy resting-state paradigm that presents HBN-inspired eyes-closed and eyes-open blocks, plays pre-recorded voice instructions, and emits LSL event markers for LabRecorder to synchronize ARTISE 8ch EEG and Gazepoint GP3-HD eye tracking.

**Architecture:** The stimulus computer runs the PsychoPy task and publishes a dedicated LSL marker stream. EEG and eye-tracker vendor software publish their own LSL streams on the same private lab network. The acquisition laptop runs LabRecorder and records all streams into one `.xdf` source-of-truth file; `.bdf` export is a later analysis/conversion concern, not the acquisition format.

**Tech Stack:** Python 3.10/3.11, PsychoPy, pylsl, pyxdf, pytest, PyYAML, LabRecorder, Gazepoint Control/OpenGaze/LSL bridge, ARTISE LSL outlet.

---

## Confirmed External Constraints

- LabRecorder records LSL streams into `.xdf`, not `.bdf`. Keep `.xdf` as the raw synchronized acquisition file.
- Gazepoint GP3-HD software requirements are Windows 10/11 and USB3.0; Mac/Linux are not supported for the official Gazepoint software.
- GP3/GP3-HD communicates through the OpenGaze API over TCP/IP and exposes gaze data such as time, points of gaze, fixation point, pupil data, and screen/camera size.
- HBN-EEG Resting State used a fixation cross, pre-recorded voice instructions to open/close eyes, and event labels such as `instructed_toOpenEyes`.
- EEGDash's HBN-specific reannotation treats stable HBN clean windows as `eyes_closed` from 15-29 seconds after `instructed_toCloseEyes`, and `eyes_open` from 5-19 seconds after `instructed_toOpenEyes`. This plan stores those offsets as analysis metadata, but does not send them as LSL markers.

## Assumptions

- Final task presentation happens on the Windows desktop connected to the GP3-HD display, not on the MacBook.
- LabRecorder runs on the Windows laptop. This is acceptable as long as all machines are on the same private network and Windows firewall permits LSL discovery/stream ports.
- The ARTISE EEG app and GP3-HD LSL bridge are already able to publish LSL streams. This project does not implement vendor device drivers.
- OpenAI-generated audio will be saved as:
  - `assets/audio/close_eyes.wav`
  - `assets/audio/open_eyes.wav`
- Tomorrow's demo prioritizes reliable synchronized acquisition over exact HBN reproduction. The default protocol is one closed-eyes block followed by one open-eyes block, with only the EO/EC instruction onsets sent as condition markers.

## File Structure

- Create: `pyproject.toml`  
  Declares runtime and test dependencies.
- Create: `configs/resting_hbn_inspired.yaml`  
  Stores protocol timing, stream names, marker labels, and audio paths.
- Create: `src/resting_task/__init__.py`  
  Package marker.
- Create: `src/resting_task/config.py`  
  Loads and validates YAML config into typed dataclasses.
- Create: `src/resting_task/protocol.py`  
  Builds the time-ordered resting-state event schedule.
- Create: `src/resting_task/lsl_markers.py`  
  Creates the LSL marker outlet and pushes structured JSON markers.
- Create: `src/resting_task/run_resting.py`  
  Runs the PsychoPy visual/audio task and emits markers.
- Create: `tools/check_lsl_streams.py`  
  Lists visible LSL streams and verifies expected EEG/gaze/marker streams before recording.
- Create: `tools/verify_xdf.py`  
  Checks recorded `.xdf` files for required streams and marker labels.
- Create: `tests/test_config.py`  
  Unit tests for config loading.
- Create: `tests/test_protocol.py`  
  Unit tests for HBN-inspired timing.
- Create: `tests/test_lsl_markers.py`  
  Unit tests for marker payload generation without requiring a live LSL network.
- Create: `docs/windows_runbook.md`  
  Operator instructions for the two-Windows-machine setup.

## Success Criteria

- `pytest -q` passes on the MacBook development machine.
- On Windows desktop, `python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml --dry-run` prints the exact event schedule without opening PsychoPy.
- On Windows desktop, the real task shows fixation, plays the two instruction files, and publishes `RestingStateMarkers`.
- On Windows laptop, LabRecorder sees EEG, GP3-HD gaze, and `RestingStateMarkers` streams before pressing Start.
- A test `.xdf` contains all required marker labels: `task_start`, `instructed_toCloseEyes`, `instructed_toOpenEyes`, `task_end`.

---

### Task 1: Project Scaffold And Config

**Files:**
- Create: `pyproject.toml`
- Create: `configs/resting_hbn_inspired.yaml`
- Create: `src/resting_task/__init__.py`
- Create: `src/resting_task/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

import pytest

from resting_task.config import load_config


def test_load_default_config_has_expected_protocol_values():
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))

    assert cfg.marker_stream.name == "RestingStateMarkers"
    assert cfg.protocol.task_name == "RestingState"
    assert cfg.protocol.pre_fixation_seconds == 2.0
    assert cfg.protocol.eyes_closed.total_seconds == 30.0
    assert cfg.protocol.eyes_closed.clean_start_after_instruction == 15.0
    assert cfg.protocol.eyes_closed.clean_end_after_instruction == 29.0
    assert cfg.protocol.eyes_open.total_seconds == 20.0
    assert cfg.protocol.eyes_open.clean_start_after_instruction == 5.0
    assert cfg.protocol.eyes_open.clean_end_after_instruction == 19.0


def test_load_config_rejects_missing_audio_key(tmp_path):
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(
        """
marker_stream:
  name: RestingStateMarkers
  type: Markers
protocol:
  task_name: RestingState
  pre_fixation_seconds: 2.0
  eyes_closed:
    total_seconds: 30.0
    clean_start_after_instruction: 15.0
    clean_end_after_instruction: 29.0
  eyes_open:
    total_seconds: 20.0
    clean_start_after_instruction: 5.0
    clean_end_after_instruction: 19.0
display:
  fullscreen: true
  background_color: [-0.1, -0.1, -0.1]
  fixation_color: [1, 1, 1]
  fixation_height: 0.08
required_streams:
  eeg_name_contains: ARTISE
  gaze_name_contains: Gaze
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="audio.close_eyes"):
        load_config(bad_config)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_config.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'resting_task'`.

- [ ] **Step 3: Create project metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "task-resting"
version = "0.1.0"
description = "PsychoPy resting-state task with LSL markers for EEG and eye tracking."
requires-python = ">=3.10,<3.12"
dependencies = [
  "psychopy>=2024.2.0",
  "pylsl>=1.16.2",
  "pyxdf>=1.16.7",
  "PyYAML>=6.0.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

- [ ] **Step 4: Create default config**

Create `configs/resting_hbn_inspired.yaml`:

```yaml
marker_stream:
  name: RestingStateMarkers
  type: Markers

protocol:
  task_name: RestingState
  pre_fixation_seconds: 2.0
  eyes_closed:
    total_seconds: 30.0
    clean_start_after_instruction: 15.0
    clean_end_after_instruction: 29.0
  eyes_open:
    total_seconds: 20.0
    clean_start_after_instruction: 5.0
    clean_end_after_instruction: 19.0

audio:
  close_eyes: assets/audio/close_eyes.wav
  open_eyes: assets/audio/open_eyes.wav

display:
  fullscreen: true
  background_color: [-0.1, -0.1, -0.1]
  fixation_color: [1, 1, 1]
  fixation_height: 0.08

required_streams:
  eeg_name_contains: ARTISE
  gaze_name_contains: Gaze
```

- [ ] **Step 5: Create package marker**

Create `src/resting_task/__init__.py`:

```python
"""Resting-state PsychoPy task with Lab Streaming Layer markers."""

__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 6: Implement config loader**

Create `src/resting_task/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class MarkerStreamConfig:
    name: str
    type: str


@dataclass(frozen=True)
class BlockTiming:
    total_seconds: float
    clean_start_after_instruction: float
    clean_end_after_instruction: float


@dataclass(frozen=True)
class ProtocolConfig:
    task_name: str
    pre_fixation_seconds: float
    eyes_closed: BlockTiming
    eyes_open: BlockTiming


@dataclass(frozen=True)
class AudioConfig:
    close_eyes: Path
    open_eyes: Path


@dataclass(frozen=True)
class DisplayConfig:
    fullscreen: bool
    background_color: tuple[float, float, float]
    fixation_color: tuple[float, float, float]
    fixation_height: float


@dataclass(frozen=True)
class RequiredStreamsConfig:
    eeg_name_contains: str
    gaze_name_contains: str


@dataclass(frozen=True)
class AppConfig:
    marker_stream: MarkerStreamConfig
    protocol: ProtocolConfig
    audio: AudioConfig
    display: DisplayConfig
    required_streams: RequiredStreamsConfig


def load_config(path: Path) -> AppConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping.")

    base_dir = path.parent.parent
    _require_path(raw, "marker_stream.name")
    _require_path(raw, "marker_stream.type")
    _require_path(raw, "protocol.task_name")
    _require_path(raw, "protocol.pre_fixation_seconds")
    _require_path(raw, "protocol.eyes_closed.total_seconds")
    _require_path(raw, "protocol.eyes_closed.clean_start_after_instruction")
    _require_path(raw, "protocol.eyes_closed.clean_end_after_instruction")
    _require_path(raw, "protocol.eyes_open.total_seconds")
    _require_path(raw, "protocol.eyes_open.clean_start_after_instruction")
    _require_path(raw, "protocol.eyes_open.clean_end_after_instruction")
    _require_path(raw, "audio.close_eyes")
    _require_path(raw, "audio.open_eyes")
    _require_path(raw, "display.fullscreen")
    _require_path(raw, "display.background_color")
    _require_path(raw, "display.fixation_color")
    _require_path(raw, "display.fixation_height")
    _require_path(raw, "required_streams.eeg_name_contains")
    _require_path(raw, "required_streams.gaze_name_contains")

    return AppConfig(
        marker_stream=MarkerStreamConfig(
            name=str(raw["marker_stream"]["name"]),
            type=str(raw["marker_stream"]["type"]),
        ),
        protocol=ProtocolConfig(
            task_name=str(raw["protocol"]["task_name"]),
            pre_fixation_seconds=float(raw["protocol"]["pre_fixation_seconds"]),
            eyes_closed=_block_timing(raw["protocol"]["eyes_closed"], "eyes_closed"),
            eyes_open=_block_timing(raw["protocol"]["eyes_open"], "eyes_open"),
        ),
        audio=AudioConfig(
            close_eyes=base_dir / str(raw["audio"]["close_eyes"]),
            open_eyes=base_dir / str(raw["audio"]["open_eyes"]),
        ),
        display=DisplayConfig(
            fullscreen=bool(raw["display"]["fullscreen"]),
            background_color=_color(raw["display"]["background_color"], "display.background_color"),
            fixation_color=_color(raw["display"]["fixation_color"], "display.fixation_color"),
            fixation_height=float(raw["display"]["fixation_height"]),
        ),
        required_streams=RequiredStreamsConfig(
            eeg_name_contains=str(raw["required_streams"]["eeg_name_contains"]),
            gaze_name_contains=str(raw["required_streams"]["gaze_name_contains"]),
        ),
    )


def _block_timing(raw: dict[str, Any], name: str) -> BlockTiming:
    timing = BlockTiming(
        total_seconds=float(raw["total_seconds"]),
        clean_start_after_instruction=float(raw["clean_start_after_instruction"]),
        clean_end_after_instruction=float(raw["clean_end_after_instruction"]),
    )
    if not 0 <= timing.clean_start_after_instruction < timing.clean_end_after_instruction <= timing.total_seconds:
        raise ValueError(f"Invalid clean window for protocol.{name}.")
    return timing


def _color(value: Any, key: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{key} must contain exactly three values.")
    return (float(value[0]), float(value[1]), float(value[2]))


def _require_path(raw: dict[str, Any], dotted_path: str) -> None:
    current: Any = raw
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Missing required config key: {dotted_path}")
        current = current[part]
```

- [ ] **Step 7: Run config tests**

Run:

```bash
pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml configs/resting_hbn_inspired.yaml src/resting_task/__init__.py src/resting_task/config.py tests/test_config.py
git commit -m "feat: add resting task config scaffold"
```

---

### Task 2: HBN-Inspired Event Schedule

**Files:**
- Create: `src/resting_task/protocol.py`
- Test: `tests/test_protocol.py`

- [ ] **Step 1: Write failing protocol tests**

Create `tests/test_protocol.py`:

```python
from pathlib import Path

from resting_task.config import load_config
from resting_task.protocol import build_schedule


def labels(schedule):
    return [event.label for event in schedule]


def test_schedule_contains_required_marker_labels():
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))

    schedule = build_schedule(cfg.protocol)

    assert labels(schedule) == [
        "task_start",
        "instructed_toCloseEyes",
        "instructed_toOpenEyes",
        "task_end",
    ]


def test_schedule_uses_condition_onsets_only():
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))

    by_label = {event.label: event for event in build_schedule(cfg.protocol)}

    assert by_label["instructed_toCloseEyes"].onset == 2.0
    assert by_label["instructed_toOpenEyes"].onset == 32.0
    assert by_label["task_end"].onset == 52.0
    assert not any("clean" in label for label in by_label)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_protocol.py -q
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `resting_task.protocol`.

- [ ] **Step 3: Implement schedule builder**

Create `src/resting_task/protocol.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from resting_task.config import ProtocolConfig


@dataclass(frozen=True)
class ScheduledEvent:
    onset: float
    label: str
    phase: str
    description: str


def build_schedule(protocol: ProtocolConfig) -> list[ScheduledEvent]:
    events: list[ScheduledEvent] = [
        ScheduledEvent(0.0, "task_start", "task", "Resting-state task started."),
    ]

    close_instruction_onset = protocol.pre_fixation_seconds
    events.append(
        ScheduledEvent(
            close_instruction_onset,
            "instructed_toCloseEyes",
            "eyes_closed",
            "Voice instruction and eyes-closed block start.",
        )
    )

    open_instruction_onset = close_instruction_onset + protocol.eyes_closed.total_seconds
    events.append(
        ScheduledEvent(
            open_instruction_onset,
            "instructed_toOpenEyes",
            "eyes_open",
            "Voice instruction and eyes-open block start.",
        )
    )

    task_end = open_instruction_onset + protocol.eyes_open.total_seconds
    events.append(ScheduledEvent(task_end, "task_end", "task", "Resting-state task ended."))
    return sorted(events, key=lambda event: event.onset)
```

- [ ] **Step 4: Run protocol tests**

Run:

```bash
pytest tests/test_protocol.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/resting_task/protocol.py tests/test_protocol.py
git commit -m "feat: add HBN-inspired resting schedule"
```

---

### Task 3: LSL Marker Payloads

**Files:**
- Create: `src/resting_task/lsl_markers.py`
- Test: `tests/test_lsl_markers.py`

- [ ] **Step 1: Write failing marker tests**

Create `tests/test_lsl_markers.py`:

```python
import json

from resting_task.lsl_markers import MarkerPayload, encode_marker


def test_encode_marker_contains_label_phase_and_elapsed_time():
    payload = MarkerPayload(
        task_name="RestingState",
        label="instructed_toOpenEyes",
        phase="eyes_open",
        scheduled_onset=32.0,
        elapsed=32.012,
        description="Voice instruction and eyes-open block start.",
    )

    encoded = encode_marker(payload)
    decoded = json.loads(encoded)

    assert decoded["task"] == "RestingState"
    assert decoded["label"] == "instructed_toOpenEyes"
    assert decoded["phase"] == "eyes_open"
    assert decoded["scheduled_onset"] == 32.0
    assert decoded["elapsed"] == 32.012
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_lsl_markers.py -q
```

Expected: FAIL with `ImportError` for `resting_task.lsl_markers`.

- [ ] **Step 3: Implement LSL marker module**

Create `src/resting_task/lsl_markers.py`:

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from pylsl import StreamInfo, StreamOutlet


@dataclass(frozen=True)
class MarkerPayload:
    task_name: str
    label: str
    phase: str
    scheduled_onset: float
    elapsed: float
    description: str


def encode_marker(payload: MarkerPayload) -> str:
    data = asdict(payload)
    data["task"] = data.pop("task_name")
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


class LSLMarkerOutlet:
    def __init__(self, name: str, stream_type: str, source_id: str = "task_resting_markers") -> None:
        info = StreamInfo(
            name=name,
            type=stream_type,
            channel_count=1,
            nominal_srate=0,
            channel_format="string",
            source_id=source_id,
        )
        self._outlet = StreamOutlet(info)

    def push(self, payload: MarkerPayload) -> None:
        self._outlet.push_sample([encode_marker(payload)])
```

- [ ] **Step 4: Run marker tests**

Run:

```bash
pytest tests/test_lsl_markers.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/resting_task/lsl_markers.py tests/test_lsl_markers.py
git commit -m "feat: add LSL marker payloads"
```

---

### Task 4: PsychoPy Resting Task Runner

**Files:**
- Create: `src/resting_task/run_resting.py`

- [ ] **Step 1: Add the runner**

Create `src/resting_task/run_resting.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from psychopy import core, event, sound, visual

from resting_task.config import AppConfig, load_config
from resting_task.lsl_markers import LSLMarkerOutlet, MarkerPayload
from resting_task.protocol import ScheduledEvent, build_schedule


def main() -> int:
    args = _parse_args()
    cfg = load_config(args.config)
    schedule = build_schedule(cfg.protocol)

    if args.dry_run:
        for item in schedule:
            print(f"{item.onset:07.3f}s {item.label} {item.phase}")
        return 0

    _require_audio_files(cfg)
    outlet = LSLMarkerOutlet(cfg.marker_stream.name, cfg.marker_stream.type)
    run_task(cfg, schedule, outlet)
    return 0


def run_task(cfg: AppConfig, schedule: list[ScheduledEvent], outlet: LSLMarkerOutlet) -> None:
    win = visual.Window(
        fullscr=cfg.display.fullscreen,
        color=cfg.display.background_color,
        units="height",
    )
    fixation = visual.TextStim(
        win=win,
        text="+",
        color=cfg.display.fixation_color,
        height=cfg.display.fixation_height,
    )
    close_audio = sound.Sound(str(cfg.audio.close_eyes))
    open_audio = sound.Sound(str(cfg.audio.open_eyes))

    clock = core.Clock()
    try:
        clock.reset()
        sent: set[str] = set()
        task_end = schedule[-1].onset

        while clock.getTime() <= task_end + 0.1:
            if "escape" in event.getKeys(["escape"]):
                _push_event(cfg, outlet, ScheduledEvent(clock.getTime(), "task_abort", "task", "Escape pressed."), clock)
                break

            elapsed = clock.getTime()
            for scheduled_event in schedule:
                if scheduled_event.label in sent:
                    continue
                if elapsed >= scheduled_event.onset:
                    _push_event(cfg, outlet, scheduled_event, clock)
                    sent.add(scheduled_event.label)
                    if scheduled_event.label == "instructed_toCloseEyes":
                        close_audio.play()
                    elif scheduled_event.label == "instructed_toOpenEyes":
                        open_audio.play()

            fixation.draw()
            win.flip()
            core.wait(0.005)
    finally:
        win.close()
        core.quit()


def _push_event(
    cfg: AppConfig,
    outlet: LSLMarkerOutlet,
    scheduled_event: ScheduledEvent,
    clock: core.Clock,
) -> None:
    outlet.push(
        MarkerPayload(
            task_name=cfg.protocol.task_name,
            label=scheduled_event.label,
            phase=scheduled_event.phase,
            scheduled_onset=scheduled_event.onset,
            elapsed=round(clock.getTime(), 6),
            description=scheduled_event.description,
        )
    )


def _require_audio_files(cfg: AppConfig) -> None:
    missing = [path for path in [cfg.audio.close_eyes, cfg.audio.open_eyes] if not path.exists()]
    if missing:
        missing_list = "\n".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing instruction audio files:\n{missing_list}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/resting_hbn_inspired.yaml"),
        help="Path to resting task YAML config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the schedule without opening a PsychoPy window or LSL outlet.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry-run the schedule**

Run:

```bash
python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml --dry-run
```

Expected output:

```text
000.000s task_start task
002.000s instructed_toCloseEyes eyes_closed
032.000s instructed_toOpenEyes eyes_open
052.000s task_end task
```

- [ ] **Step 3: Commit**

```bash
git add src/resting_task/run_resting.py
git commit -m "feat: add PsychoPy resting task runner"
```

---

### Task 5: Stream And XDF Verification Tools

**Files:**
- Create: `tools/check_lsl_streams.py`
- Create: `tools/verify_xdf.py`

- [ ] **Step 1: Create LSL stream checker**

Create `tools/check_lsl_streams.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from pylsl import resolve_streams

from resting_task.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/resting_hbn_inspired.yaml"))
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    cfg = load_config(args.config)
    streams = resolve_streams(wait_time=args.timeout)
    rows = [(stream.name(), stream.type(), stream.channel_count(), stream.nominal_srate()) for stream in streams]

    print("Visible LSL streams:")
    for name, stream_type, channel_count, srate in rows:
        print(f"- {name} | {stream_type} | {channel_count} ch | {srate} Hz")

    names = [row[0] for row in rows]
    required = {
        "EEG": cfg.required_streams.eeg_name_contains,
        "Gaze": cfg.required_streams.gaze_name_contains,
        "Markers": cfg.marker_stream.name,
    }
    missing = {
        label: pattern
        for label, pattern in required.items()
        if not any(pattern.lower() in name.lower() for name in names)
    }
    if missing:
        print("Missing required streams:")
        for label, pattern in missing.items():
            print(f"- {label}: expected stream name containing '{pattern}'")
        return 1

    print("All required streams are visible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Create XDF verifier**

Create `tools/verify_xdf.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyxdf

from resting_task.config import load_config


REQUIRED_LABELS = {
    "task_start",
    "instructed_toCloseEyes",
    "instructed_toOpenEyes",
    "task_end",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("xdf", type=Path)
    parser.add_argument("--config", type=Path, default=Path("configs/resting_hbn_inspired.yaml"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    streams, _ = pyxdf.load_xdf(str(args.xdf))
    stream_names = [stream["info"]["name"][0] for stream in streams]
    print("Streams in XDF:")
    for stream in streams:
        name = stream["info"]["name"][0]
        stream_type = stream["info"]["type"][0]
        channels = stream["info"]["channel_count"][0]
        srate = stream["info"]["nominal_srate"][0]
        samples = len(stream["time_series"])
        print(f"- {name} | {stream_type} | {channels} ch | {srate} Hz | {samples} samples")

    expected_patterns = [
        cfg.required_streams.eeg_name_contains,
        cfg.required_streams.gaze_name_contains,
        cfg.marker_stream.name,
    ]
    missing_streams = [
        pattern
        for pattern in expected_patterns
        if not any(pattern.lower() in name.lower() for name in stream_names)
    ]

    marker_stream = next(
        (stream for stream in streams if stream["info"]["name"][0] == cfg.marker_stream.name),
        None,
    )
    if marker_stream is None:
        print(f"Missing marker stream: {cfg.marker_stream.name}")
        return 1

    labels = set()
    for sample in marker_stream["time_series"]:
        raw_value = sample[0]
        value = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else raw_value
        labels.add(json.loads(value)["label"])

    missing_labels = REQUIRED_LABELS - labels
    if missing_streams or missing_labels:
        if missing_streams:
            print("Missing stream name patterns:")
            for pattern in missing_streams:
                print(f"- {pattern}")
        if missing_labels:
            print("Missing marker labels:")
            for label in sorted(missing_labels):
                print(f"- {label}")
        return 1

    print("XDF verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run stream checker while task is dry-run unavailable**

Run:

```bash
python tools/check_lsl_streams.py --config configs/resting_hbn_inspired.yaml --timeout 2
```

Expected before hardware/task is running: FAIL and print missing stream patterns.

- [ ] **Step 4: Commit**

```bash
git add tools/check_lsl_streams.py tools/verify_xdf.py
git commit -m "feat: add LSL and XDF verification tools"
```

---

### Task 6: Windows Experiment Runbook

**Files:**
- Create: `docs/windows_runbook.md`

- [ ] **Step 1: Create operator runbook**

Create `docs/windows_runbook.md`:

```markdown
# Windows Runbook: ARTISE EEG + Gazepoint GP3-HD + PsychoPy + LabRecorder

## Machine Roles

- Windows desktop: stimulus presentation, PsychoPy task, GP3-HD connected by USB3.0, GP3-HD control/LSL bridge.
- Windows laptop: LabRecorder acquisition machine.
- MacBook Pro M3: development machine only. Do not use it for the final GP3-HD acquisition path because Gazepoint's official software does not support Mac/Linux.

## Network

- Put both Windows machines on the same private wired network when possible.
- If using Wi-Fi, make sure both machines are on the same SSID and client isolation is disabled.
- Windows firewall must allow LSL discovery and streaming on the private network.
- LSL default discovery uses UDP broadcast/multicast port 16571 and TCP/UDP ports 16572-16604.

## Before Participant Arrives

1. On Windows desktop, connect GP3-HD by USB3.0.
2. Launch Gazepoint Control/OpenGaze software.
3. Calibrate GP3-HD on the same display used by PsychoPy.
4. Start the GP3-HD LSL bridge and confirm a gaze stream is visible.
5. Start the ARTISE EEG app and confirm its LSL outlet is active.
6. On Windows desktop, activate the Python environment.
7. Run:

   ```powershell
   python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml --dry-run
   ```

8. Confirm the printed schedule is 52 seconds and contains only task start, EC instruction, EO instruction, and task end markers.

## LabRecorder Setup

1. On Windows laptop, open LabRecorder.
2. Click Update.
3. Confirm these streams are visible:
   - ARTISE EEG stream
   - Gazepoint/GP3-HD gaze stream
   - RestingStateMarkers
4. Set Study Root to the project data folder.
5. Use a filename template such as:

   ```text
   sub-%p_task-RestingState_run-%n.xdf
   ```

6. Press Start before starting the PsychoPy task.
7. Confirm file size increases during recording.
8. Press Stop only after PsychoPy exits.

## Demo Recording

1. Start LabRecorder on the laptop.
2. On Windows desktop, run:

   ```powershell
   python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml
   ```

3. The task will:
   - Show a central fixation cross.
   - At 2 seconds, play `close_eyes.wav` and emit `instructed_toCloseEyes`.
   - At 32 seconds, play `open_eyes.wav` and emit `instructed_toOpenEyes`.
   - End at 52 seconds.

## After Recording

Run:

```powershell
python tools\verify_xdf.py C:\path\to\recording.xdf --config configs\resting_hbn_inspired.yaml
```

Expected:

```text
XDF verification passed.
```

## Data Format Decision

Keep the LabRecorder `.xdf` as the raw synchronized source. If later analysis requires `.bdf`/`.edf`, convert from `.xdf` after verifying streams and marker timing. Do not use `.bdf` as the primary synchronized recording container for this multimodal LSL setup.
```

- [ ] **Step 2: Commit**

```bash
git add docs/windows_runbook.md
git commit -m "docs: add Windows acquisition runbook"
```

---

### Task 7: End-To-End Dry Run

**Files:**
- No new files.

- [ ] **Step 1: Install dependencies on MacBook for development tests**

Run:

```bash
python -m pip install -e ".[dev]"
```

Expected: dependencies install successfully. If PsychoPy installation fails on Mac M3, create a Windows venv and run the same command there; do not rewrite the task to avoid PsychoPy.

- [ ] **Step 2: Run unit tests**

Run:

```bash
pytest -q
```

Expected:

```text
5 passed
```

- [ ] **Step 3: Run dry-run schedule**

Run:

```bash
python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml --dry-run
```

Expected: the 52-second schedule printed in Task 4.

- [ ] **Step 4: On Windows desktop, verify audio assets**

Run:

```powershell
Test-Path assets\audio\close_eyes.wav
Test-Path assets\audio\open_eyes.wav
```

Expected:

```text
True
True
```

- [ ] **Step 5: On Windows desktop, start task and marker outlet**

Run:

```powershell
python -m resting_task.run_resting --config configs/resting_hbn_inspired.yaml
```

Expected: PsychoPy opens fullscreen, fixation cross appears, both voice instructions play, task closes after 52 seconds.

- [ ] **Step 6: On Windows laptop, verify streams before recording**

Run:

```powershell
python tools\check_lsl_streams.py --config configs\resting_hbn_inspired.yaml --timeout 5
```

Expected:

```text
All required streams are visible.
```

- [ ] **Step 7: Record one XDF**

Use LabRecorder to record one 52-second run.

Expected: LabRecorder file size increases while recording and produces one `.xdf`.

- [ ] **Step 8: Verify XDF**

Run:

```powershell
python tools\verify_xdf.py C:\path\to\recording.xdf --config configs\resting_hbn_inspired.yaml
```

Expected:

```text
XDF verification passed.
```

- [ ] **Step 9: Commit final verified state**

```bash
git status --short
git add .
git commit -m "test: verify resting task dry run"
```

---

## Self-Review

### Spec Coverage

- Synchronous EEG + eye tracking with LSL: covered by LabRecorder `.xdf`, marker stream, stream checker, and runbook.
- PsychoPy resting paradigm: covered by `run_resting.py`.
- HBN-inspired eyes-open/eyes-closed design: covered by EO/EC onset markers and clean-window offsets stored for downstream analysis.
- Audio instruction playback: covered by `close_eyes.wav` and `open_eyes.wav` config paths and PsychoPy sound playback.
- LSL event markers: covered by `lsl_markers.py`, protocol labels, and `.xdf` verification.
- Windows GP3-HD constraint: covered by runbook and architecture.
- MacBook development: covered by local tests and Windows runtime instructions.
- BDF/XDF question: resolved as `.xdf` source-of-truth, optional post-hoc conversion only.

### Placeholder Scan

No banned placeholder tokens or unspecified test steps are present. The only environment-specific value is the final `.xdf` path in the operator command, which is necessarily chosen after LabRecorder records a file.

### Type Consistency

- `ProtocolConfig`, `BlockTiming`, `AppConfig`, and `ScheduledEvent` names are consistent across tests and implementation.
- Marker labels in `protocol.py`, `verify_xdf.py`, and success criteria match.
- Config keys in YAML match `config.py` and tests.

## Sources Checked

- HBN-EEG Release 4 README: https://github.com/OpenNeuroDatasets/ds005508
- HBN-EEG paper/preprint excerpt describing Resting State voice instructions and HED label `instructed_toOpenEyes`: https://doi.org/10.1101/2024.10.03.615261
- EEGDash HBN reannotation windows: https://eegdash.org/api/dataset/eegdash.hbn.preprocessing.html
- LabRecorder records LSL streams into XDF: https://github.com/labstreaminglayer/App-LabRecorder
- LSL introduction and XDF format: https://labstreaminglayer.readthedocs.io/info/intro.html
- LSL network troubleshooting ports/firewall: https://labstreaminglayer.readthedocs.io/info/network-connectivity.html
- Gazepoint GP3-HD Windows requirements: https://www.gazept.com/product/gp3-hd-ux-bundle-eye-tracking-ux-testing/
- Gazepoint developer/OpenGaze API notes: https://www.gazept.com/developer/
