import json
import sys

from resting_task.lsl_markers import LSLMarkerOutlet, MarkerPayload, encode_marker


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


def test_lsl_marker_module_does_not_import_pylsl_until_outlet_creation():
    sys.modules.pop("pylsl", None)

    encode_marker(
        MarkerPayload(
            task_name="RestingState",
            label="task_end",
            phase="task",
            scheduled_onset=52.0,
            elapsed=52.0,
            description="Resting-state task ended.",
        )
    )

    assert "pylsl" not in sys.modules


def test_outlet_can_push_encoded_markers_with_injected_stream_outlet():
    pushed_samples = []

    class FakeOutlet:
        def push_sample(self, sample):
            pushed_samples.append(sample)

    outlet = LSLMarkerOutlet.from_outlet(FakeOutlet())
    outlet.push(
        MarkerPayload(
            task_name="RestingState",
            label="task_end",
            phase="task",
            scheduled_onset=52.0,
            elapsed=52.0,
            description="Resting-state task ended.",
        )
    )

    assert len(pushed_samples) == 1
    assert json.loads(pushed_samples[0][0])["label"] == "task_end"
