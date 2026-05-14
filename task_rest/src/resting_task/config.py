"""Configuration loading for the resting-state task."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the task configuration is missing required settings."""


@dataclass(frozen=True)
class MarkerStreamConfig:
    name: str
    type: str
    source_id: str


@dataclass(frozen=True)
class BlockTiming:
    total_seconds: float
    clean_start_after_instruction: float
    clean_end_after_instruction: float


@dataclass(frozen=True)
class ProtocolConfig:
    task_name: str
    pre_fixation_seconds: float
    repetitions: int
    starts_with: str
    eyes_closed: BlockTiming
    eyes_open: BlockTiming


@dataclass(frozen=True)
class AudioConfig:
    close_eyes: Path
    open_eyes: Path
    end: Path


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


def load_config(config_path: str | Path, repo_root: str | Path | None = None) -> AppConfig:
    """Load a YAML config and resolve relative audio paths from the repo root."""

    path = Path(config_path)
    root = Path(repo_root) if repo_root is not None else path.resolve().parent.parent

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ConfigError("configuration must be a mapping")

    _require_path(raw, "marker_stream.name")
    _require_path(raw, "marker_stream.type")
    _require_path(raw, "protocol.task_name")
    _require_path(raw, "protocol.pre_fixation_seconds")
    _require_path(raw, "protocol.repetitions")
    _require_path(raw, "protocol.starts_with")
    _require_path(raw, "protocol.eyes_closed.total_seconds")
    _require_path(raw, "protocol.eyes_closed.clean_start_after_instruction")
    _require_path(raw, "protocol.eyes_closed.clean_end_after_instruction")
    _require_path(raw, "protocol.eyes_open.total_seconds")
    _require_path(raw, "protocol.eyes_open.clean_start_after_instruction")
    _require_path(raw, "protocol.eyes_open.clean_end_after_instruction")
    _require_path(raw, "audio.close_eyes")
    _require_path(raw, "audio.open_eyes")
    _require_path(raw, "audio.end")
    _require_path(raw, "display.fullscreen")
    _require_path(raw, "display.background_color")
    _require_path(raw, "display.fixation_color")
    _require_path(raw, "display.fixation_height")
    _require_path(raw, "required_streams.eeg_name_contains")
    _require_path(raw, "required_streams.gaze_name_contains")

    marker_stream = raw["marker_stream"]
    protocol = raw["protocol"]
    audio = raw["audio"]
    display = raw["display"]
    required_streams = raw["required_streams"]

    return AppConfig(
        marker_stream=MarkerStreamConfig(
            name=str(marker_stream["name"]),
            type=str(marker_stream["type"]),
            source_id=str(marker_stream.get("source_id", "task_resting_markers")),
        ),
        protocol=ProtocolConfig(
            task_name=str(protocol["task_name"]),
            pre_fixation_seconds=_number(protocol, "pre_fixation_seconds"),
            repetitions=_positive_int(protocol, "repetitions"),
            starts_with=_condition(protocol, "starts_with"),
            eyes_closed=_block_timing(protocol["eyes_closed"], "protocol.eyes_closed"),
            eyes_open=_block_timing(protocol["eyes_open"], "protocol.eyes_open"),
        ),
        audio=AudioConfig(
            close_eyes=_resolve_repo_path(root, str(audio["close_eyes"])),
            open_eyes=_resolve_repo_path(root, str(audio["open_eyes"])),
            end=_resolve_repo_path(root, str(audio["end"])),
        ),
        display=DisplayConfig(
            fullscreen=bool(display["fullscreen"]),
            background_color=_color(display["background_color"], "display.background_color"),
            fixation_color=_color(display["fixation_color"], "display.fixation_color"),
            fixation_height=_number(display, "fixation_height"),
        ),
        required_streams=RequiredStreamsConfig(
            eeg_name_contains=str(required_streams["eeg_name_contains"]),
            gaze_name_contains=str(required_streams["gaze_name_contains"]),
        ),
    )


def _block_timing(raw: Any, path: str) -> BlockTiming:
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must be a mapping")

    timing = BlockTiming(
        total_seconds=_number(raw, "total_seconds"),
        clean_start_after_instruction=_number(raw, "clean_start_after_instruction"),
        clean_end_after_instruction=_number(raw, "clean_end_after_instruction"),
    )
    if not 0 <= timing.clean_start_after_instruction < timing.clean_end_after_instruction <= timing.total_seconds:
        raise ConfigError(f"invalid clean analysis window for {path}")
    return timing


def _color(value: Any, path: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ConfigError(f"{path} must contain exactly three values")
    return (float(value[0]), float(value[1]), float(value[2]))


def _number(raw: dict[str, Any], key: str) -> float:
    value = raw[key]
    if not isinstance(value, (int, float)):
        raise ConfigError(f"{key} must be numeric")
    return float(value)


def _positive_int(raw: dict[str, Any], key: str) -> int:
    value = raw[key]
    if not isinstance(value, int) or value < 1:
        raise ConfigError(f"{key} must be a positive integer")
    return value


def _condition(raw: dict[str, Any], key: str) -> str:
    value = raw[key]
    if value not in {"eyes_closed", "eyes_open"}:
        raise ConfigError(f"{key} must be 'eyes_closed' or 'eyes_open'")
    return str(value)


def _require_path(raw: dict[str, Any], dotted_path: str) -> None:
    current: Any = raw
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ConfigError(f"missing required config key: {dotted_path}")
        current = current[part]


def _resolve_repo_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path
