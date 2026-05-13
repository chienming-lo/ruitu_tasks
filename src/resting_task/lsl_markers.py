"""LSL marker payload encoding and outlet helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from resting_task.config import MarkerStreamConfig


@dataclass(frozen=True)
class MarkerPayload:
    task_name: str
    label: str
    phase: str
    scheduled_onset: float
    elapsed: float
    description: str


def encode_marker(payload: MarkerPayload) -> str:
    """Encode a marker payload as one compact JSON LSL sample."""

    data = asdict(payload)
    data["task"] = data.pop("task_name")
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


class LSLMarkerOutlet:
    """Push encoded marker payloads to an LSL marker outlet."""

    def __init__(self, config: MarkerStreamConfig):
        from pylsl import StreamInfo, StreamOutlet

        info = StreamInfo(
            name=config.name,
            type=config.type,
            channel_count=1,
            nominal_srate=0,
            channel_format="string",
            source_id=config.source_id,
        )
        self._outlet = StreamOutlet(info)

    @classmethod
    def from_outlet(cls, outlet: object) -> "LSLMarkerOutlet":
        marker_outlet = cls.__new__(cls)
        marker_outlet._outlet = outlet
        return marker_outlet

    def push(self, payload: MarkerPayload) -> None:
        self._outlet.push_sample([encode_marker(payload)])
