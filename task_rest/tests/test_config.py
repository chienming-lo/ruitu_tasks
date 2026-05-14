from pathlib import Path

import pytest

from resting_task.config import ConfigError, load_config


def test_load_default_config_has_expected_protocol_values():
    cfg = load_config(Path("configs/resting_hbn_inspired.yaml"))

    assert cfg.marker_stream.name == "RestingStateMarkers"
    assert cfg.marker_stream.type == "Markers"
    assert cfg.protocol.task_name == "RestingState"
    assert cfg.protocol.pre_fixation_seconds == 2.0
    assert cfg.protocol.repetitions == 5
    assert cfg.protocol.starts_with == "eyes_open"
    assert cfg.protocol.eyes_closed.total_seconds == 40.0
    assert cfg.protocol.eyes_closed.clean_start_after_instruction == 15.0
    assert cfg.protocol.eyes_closed.clean_end_after_instruction == 29.0
    assert cfg.protocol.eyes_open.total_seconds == 20.0
    assert cfg.protocol.eyes_open.clean_start_after_instruction == 5.0
    assert cfg.protocol.eyes_open.clean_end_after_instruction == 19.0
    assert cfg.audio.close_eyes == Path.cwd() / "assets/audio/close_eyes.wav"
    assert cfg.audio.open_eyes == Path.cwd() / "assets/audio/open_eyes.wav"
    assert cfg.audio.end == Path.cwd() / "assets/audio/end.wav"


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
  repetitions: 5
  starts_with: eyes_open
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

    with pytest.raises(ConfigError, match="audio.close_eyes"):
        load_config(bad_config)


def test_load_config_rejects_invalid_clean_window(tmp_path):
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(
        """
marker_stream:
  name: RestingStateMarkers
  type: Markers
protocol:
  task_name: RestingState
  pre_fixation_seconds: 2.0
  repetitions: 5
  starts_with: eyes_open
  eyes_closed:
    total_seconds: 30.0
    clean_start_after_instruction: 29.0
    clean_end_after_instruction: 15.0
  eyes_open:
    total_seconds: 20.0
    clean_start_after_instruction: 5.0
    clean_end_after_instruction: 19.0
audio:
  close_eyes: assets/audio/close_eyes.wav
  open_eyes: assets/audio/open_eyes.wav
  end: assets/audio/end.wav
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

    with pytest.raises(ConfigError, match="clean analysis window"):
        load_config(bad_config)
