from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from resting_task.config import load_config


REQUIRED_LABELS = {
    "task_start",
    "instructed_toCloseEyes",
    "instructed_toOpenEyes",
    "task_end",
}


def main() -> int:
    args = _parse_args()
    cfg = load_config(args.config)
    streams = _load_xdf(args.xdf)
    stream_names = [_stream_info(stream, "name") for stream in streams]

    print("Streams in XDF:")
    if not streams:
        print("- none")
    for stream in streams:
        print(
            "- "
            f"{_stream_info(stream, 'name')} | "
            f"{_stream_info(stream, 'type')} | "
            f"{_stream_info(stream, 'channel_count')} ch | "
            f"{_stream_info(stream, 'nominal_srate')} Hz | "
            f"{len(stream.get('time_series', []))} samples"
        )

    expected_patterns = list(_required_patterns(cfg).values())
    missing_streams = [
        pattern
        for pattern in expected_patterns
        if not _contains_pattern(stream_names, pattern)
    ]

    marker_stream = next(
        (stream for stream in streams if _stream_info(stream, "name") == _marker_stream_name(cfg)),
        None,
    )
    if marker_stream is None:
        print(f"Missing marker stream: {_marker_stream_name(cfg)}")
        return 1

    labels, invalid_samples = _marker_labels(marker_stream)
    missing_labels = REQUIRED_LABELS - labels
    extra_labels = labels - REQUIRED_LABELS
    sample_count = len(marker_stream.get("time_series", []))
    expected_sample_count = cfg.protocol.repetitions * 2 + 2
    if missing_streams or missing_labels or extra_labels or invalid_samples or sample_count != expected_sample_count:
        if missing_streams:
            print("Missing stream name patterns:")
            for pattern in missing_streams:
                print(f"- {pattern}")
        if missing_labels:
            print("Missing marker labels:")
            for label in sorted(missing_labels):
                print(f"- {label}")
        if extra_labels:
            print("Unexpected marker labels:")
            for label in sorted(extra_labels):
                print(f"- {label}")
        if invalid_samples:
            print(f"Unparseable marker samples: {invalid_samples}")
        if sample_count != expected_sample_count:
            print(f"Unexpected marker sample count: expected {expected_sample_count}, got {sample_count}")
        return 1

    print("XDF verification passed.")
    return 0


def _load_xdf(path: Path) -> list[dict[str, Any]]:
    try:
        import pyxdf
    except ImportError as exc:
        raise RuntimeError("pyxdf is required to verify recorded .xdf files.") from exc
    streams, _ = pyxdf.load_xdf(str(path))
    return streams


def _marker_labels(marker_stream: dict[str, Any]) -> tuple[set[str], int]:
    labels: set[str] = set()
    invalid_samples = 0
    for sample in marker_stream.get("time_series", []):
        raw_value = _single_marker_value(sample)
        value = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else raw_value
        try:
            decoded = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            invalid_samples += 1
            continue
        label = decoded.get("label")
        if isinstance(label, str):
            labels.add(label)
        else:
            invalid_samples += 1
    return labels, invalid_samples


def _single_marker_value(sample: Any) -> Any:
    if isinstance(sample, (str, bytes)):
        return sample
    if isinstance(sample, (list, tuple)):
        return sample[0] if sample else ""
    if hasattr(sample, "shape") and getattr(sample, "shape", None) == ():
        return sample.item()
    if hasattr(sample, "__len__") and hasattr(sample, "__getitem__"):
        try:
            if len(sample) == 1:
                return sample[0]
        except TypeError:
            pass
    if hasattr(sample, "item"):
        try:
            return sample.item()
        except ValueError:
            pass
    return sample


def _stream_info(stream: dict[str, Any], key: str) -> str:
    value = stream.get("info", {}).get(key, [""])[0]
    return str(value)


def _contains_pattern(names: list[str], pattern: str) -> bool:
    pattern_lower = pattern.lower()
    return any(pattern_lower in name.lower() for name in names)


def _required_patterns(cfg: Any) -> dict[str, str]:
    return {
        "EEG": cfg.required_streams.eeg_name_contains,
        "Gaze": cfg.required_streams.gaze_name_contains,
        "Markers": _marker_stream_name(cfg),
    }


def _marker_stream_name(cfg: Any) -> str:
    return cfg.marker_stream.name


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("xdf", type=Path, help="Path to the LabRecorder .xdf file.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/resting_hbn_inspired.yaml"),
        help="Path to resting task YAML config.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
