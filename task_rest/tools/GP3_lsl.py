from __future__ import annotations

import xml.etree.ElementTree as ET


SAMPLE_RATE_HZ = 150.0

CHANNELS = [
    ("TIME", "seconds", "gazepoint_time"),
    ("FPOGX", "percent", "gaze"),
    ("FPOGY", "percent", "gaze"),
    ("FPOGS", "seconds", "gaze"),
    ("FPOGD", "seconds", "gaze"),
    ("FPOGID", "integer", "gaze"),
    ("FPOGV", "boolean", "gaze"),
    ("BPOGX", "percent", "gaze"),
    ("BPOGY", "percent", "gaze"),
    ("BPOGV", "boolean", "gaze"),
    ("LPMM", "millimeters", "pupil"),
    ("LPMMV", "boolean", "pupil"),
    ("RPMM", "millimeters", "pupil"),
    ("RPMMV", "boolean", "pupil"),
]


def parse_record(message: str) -> list[float] | None:
    """Parse one Gazepoint <REC /> message into the LSL channel order."""

    message = message.strip()
    if not message:
        return None

    try:
        record = ET.fromstring(message)
    except ET.ParseError:
        return None

    if record.tag != "REC":
        return None

    return [_float_attr(record, label) for label, _, _ in CHANNELS]


def _float_attr(record: ET.Element, label: str) -> float:
    value = record.attrib.get(label)
    if value is None or value == "":
        return 0.0
    return float(value)


def _receive_line(sock: object) -> str:
    message = ""
    while True:
        chunk = sock.recv(1)
        if len(chunk) == 0:
            raise RuntimeError("socket connection broken")
        message += chunk.decode()
        if message.endswith("\r\n"):
            return message


def _send(sock: object, message: str) -> None:
    data = message.encode()
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        total_sent += sent


def _append_channels(info: object) -> None:
    channels = info.desc().append_child("channels")
    for label, unit, channel_type in CHANNELS:
        channels.append_child("channel").append_child_value("label", label).append_child_value(
            "unit", unit
        ).append_child_value("type", channel_type)


def _get_serial_number(sock: object) -> str:
    _send(sock, '<GET ID="SERIAL_ID" />\r\n')
    message = _receive_line(sock)
    try:
        ack = ET.fromstring(message.strip())
    except ET.ParseError:
        return "000000000"
    return ack.attrib.get("VALUE", "000000000")


def main() -> int:
    import socket

    import pylsl as lsl

    requests = [
        '<SET ID="ENABLE_SEND_TIME" STATE="1"/>\r\n',
        '<SET ID="ENABLE_SEND_POG_FIX" STATE="1"/>\r\n',
        '<SET ID="ENABLE_SEND_POG_BEST" STATE="1"/>\r\n',
        '<SET ID="ENABLE_SEND_PUPILMM" STATE="1"/>\r\n',
        '<SET ID="ENABLE_SEND_DATA" STATE="1"/>\r\n',
    ]

    with socket.socket() as sock:
        sock.connect(("127.0.0.1", 4242))
        print("Connected to Gazepoint Control on 127.0.0.1:4242")

        for request in requests:
            _send(sock, request)
            _receive_line(sock)

        serial_number = _get_serial_number(sock)
        source_id = "gazepoint" + serial_number
        print("Gazepoint device SN:", source_id)

        info = lsl.StreamInfo(
            "GazepointEyeTracker",
            "gaze",
            len(CHANNELS),
            SAMPLE_RATE_HZ,
            "float32",
            source_id,
        )
        info.desc().append_child_value("manufacturer", "Gazepoint")
        _append_channels(info)

        outlet = lsl.StreamOutlet(info)
        print("Streaming Gazepoint gaze + pupil data to LSL as GazepointEyeTracker")
        print("Channels:", ", ".join(label for label, _, _ in CHANNELS))

        while True:
            sample = parse_record(_receive_line(sock))
            if sample is None:
                continue
            outlet.push_sample(sample)


if __name__ == "__main__":
    raise SystemExit(main())
