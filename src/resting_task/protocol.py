"""Protocol schedule construction for the resting-state task."""

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
    """Build the real LSL marker events for the configured task.

    Clean analysis windows are intentionally not emitted as markers. They are
    derived later from the EO/EC instruction onsets and the configured offsets.
    """

    events = [
        ScheduledEvent(0.0, "task_start", "task", "Resting-state task started."),
    ]
    onset = protocol.pre_fixation_seconds
    phase = protocol.starts_with

    for _ in range(protocol.repetitions * 2):
        events.append(_instruction_event(onset, phase))
        onset += _duration_for_phase(protocol, phase)
        phase = "eyes_open" if phase == "eyes_closed" else "eyes_closed"

    events.append(ScheduledEvent(onset, "task_end", "task", "Resting-state task ended."))
    return events


def _instruction_event(onset: float, phase: str) -> ScheduledEvent:
    if phase == "eyes_closed":
        return ScheduledEvent(
            onset,
            "instructed_toCloseEyes",
            "eyes_closed",
            "Voice instruction and eyes-closed block start.",
        )
    return ScheduledEvent(
        onset,
        "instructed_toOpenEyes",
        "eyes_open",
        "Voice instruction and eyes-open block start.",
    )


def _duration_for_phase(protocol: ProtocolConfig, phase: str) -> float:
    if phase == "eyes_closed":
        return protocol.eyes_closed.total_seconds
    return protocol.eyes_open.total_seconds
