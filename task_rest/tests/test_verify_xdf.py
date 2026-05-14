import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.verify_xdf import REQUIRED_LABELS, _marker_labels


def _sample(label):
    return json.dumps(
        {
            "task": "RestingState",
            "label": label,
            "phase": "task",
            "scheduled_onset": 0.0,
            "elapsed": 0.0,
            "description": "",
        }
    )


class ArrayLike:
    def __init__(self, value):
        self._value = value

    def __len__(self):
        return 1

    def __getitem__(self, index):
        if index != 0:
            raise IndexError(index)
        return self._value


class ScalarLike:
    shape = ()

    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


def test_marker_labels_accept_list_tuple_bytes_and_array_like_rows():
    marker_stream = {
        "time_series": [
            [_sample("task_start")],
            (_sample("instructed_toCloseEyes").encode("utf-8"),),
            ArrayLike(_sample("instructed_toOpenEyes")),
            ScalarLike(_sample("task_end")),
        ]
    }

    labels, invalid_samples = _marker_labels(marker_stream)

    assert labels == REQUIRED_LABELS
    assert invalid_samples == 0


def test_marker_labels_counts_unparseable_samples():
    labels, invalid_samples = _marker_labels({"time_series": [["not-json"]]})

    assert labels == set()
    assert invalid_samples == 1
