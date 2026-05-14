from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from resting_task.config import load_config


def main() -> int:
    args = _parse_args()
    cfg = load_config(args.config)
    streams = _resolve_streams(args.timeout)
    rows = [
        (stream.name(), stream.type(), stream.channel_count(), stream.nominal_srate())
        for stream in streams
    ]

    print("Visible LSL streams:")
    if not rows:
        print("- none")
    for name, stream_type, channel_count, srate in rows:
        print(f"- {name} | {stream_type} | {channel_count} ch | {srate} Hz")

    names = [row[0] for row in rows]
    required = _required_patterns(cfg)
    missing = {
        label: pattern
        for label, pattern in required.items()
        if not _contains_pattern(names, pattern)
    }

    if missing:
        print("Missing required streams:")
        for label, pattern in missing.items():
            print(f"- {label}: expected stream name containing '{pattern}'")
        return 1

    print("All required streams are visible.")
    return 0


def _resolve_streams(timeout: float) -> list[Any]:
    try:
        from pylsl import resolve_streams
    except ImportError as exc:
        raise RuntimeError("pylsl is required to check live LSL streams.") from exc
    return resolve_streams(wait_time=timeout)


def _contains_pattern(names: list[str], pattern: str) -> bool:
    pattern_lower = pattern.lower()
    return any(pattern_lower in name.lower() for name in names)


def _required_patterns(cfg: Any) -> dict[str, str]:
    return {
        "EEG": cfg.required_streams.eeg_name_contains,
        "Gaze": cfg.required_streams.gaze_name_contains,
        "Markers": cfg.marker_stream.name,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/resting_hbn_inspired.yaml"),
        help="Path to resting task YAML config.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Seconds to wait for LSL stream discovery.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
