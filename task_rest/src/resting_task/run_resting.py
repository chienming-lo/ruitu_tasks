from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from resting_task.config import AppConfig, load_config
from resting_task.lsl_markers import MarkerPayload
from resting_task.protocol import ScheduledEvent, build_schedule


def main() -> int:
    args = _parse_args()
    cfg = load_config(args.config)
    schedule = _build_schedule(cfg)

    if args.dry_run:
        _print_schedule(schedule)
        return 0

    _require_audio_files(cfg)
    psychopy = _load_psychopy()
    outlet = _create_marker_outlet(cfg)
    run_task(cfg, schedule, outlet, psychopy)
    return 0


def run_task(
    cfg: AppConfig,
    schedule: list[ScheduledEvent],
    outlet: Any,
    psychopy: Any | None = None,
) -> None:
    """Run the visual/audio task and emit only the configured schedule markers."""
    if psychopy is None:
        psychopy = _load_psychopy()
    visual = psychopy["visual"]
    core = psychopy["core"]
    event = psychopy["event"]
    sound = psychopy["sound"]

    win = None

    try:
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
        start_message = visual.TextStim(
            win=win,
            text="準備好後按空白鍵或滑鼠開始",
            color=cfg.display.fixation_color,
            height=cfg.display.fixation_height,
        )
        end_message = visual.TextStim(
            win=win,
            text="實驗結束",
            color=cfg.display.fixation_color,
            height=cfg.display.fixation_height,
        )
        close_audio = sound.Sound(str(cfg.audio.close_eyes))
        open_audio = sound.Sound(str(cfg.audio.open_eyes))
        clock = core.Clock()

        if not _wait_for_start(start_message, win, event, core):
            return

        clock.reset()
        sent: set[int] = set()
        task_end = schedule[-1].onset
        escaped = False

        while clock.getTime() <= task_end + 0.1:
            if "escape" in event.getKeys(["escape"]):
                escaped = True
                break

            elapsed = clock.getTime()
            for event_index, scheduled_event in enumerate(schedule):
                label = scheduled_event.label
                if event_index in sent or elapsed < scheduled_event.onset:
                    continue
                _push_event(cfg, outlet, scheduled_event, elapsed)
                sent.add(event_index)
                if label == "instructed_toCloseEyes":
                    close_audio.stop()
                    close_audio.play()
                elif label == "instructed_toOpenEyes":
                    open_audio.stop()
                    open_audio.play()

            fixation.draw()
            win.flip()
            core.wait(0.005)

        if not escaped and len(sent) == len(schedule):
            end_message.draw()
            win.flip()
            core.wait(3.0)
    finally:
        if win is not None:
            win.close()


def _wait_for_start(start_message: Any, win: Any, event: Any, core: Any) -> bool:
    while True:
        keys = event.getKeys(["space", "escape"])
        if "escape" in keys:
            return False
        if "space" in keys or event.getMouseButtons()[0]:
            return True

        start_message.draw()
        win.flip()
        core.wait(0.01)


def _push_event(
    cfg: AppConfig,
    outlet: Any,
    scheduled_event: ScheduledEvent,
    elapsed: float,
) -> None:
    payload = MarkerPayload(
        task_name=cfg.protocol.task_name,
        label=scheduled_event.label,
        phase=scheduled_event.phase,
        scheduled_onset=scheduled_event.onset,
        elapsed=round(elapsed, 6),
        description=scheduled_event.description,
    )
    outlet.push(payload)


def _require_audio_files(cfg: Any) -> None:
    missing = [path for path in (cfg.audio.close_eyes, cfg.audio.open_eyes) if not path.exists()]
    if missing:
        missing_list = "\n".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing instruction audio files:\n{missing_list}")


def _load_psychopy() -> dict[str, Any]:
    try:
        from psychopy import core, event, sound, visual
    except ImportError as exc:
        raise RuntimeError(
            "PsychoPy is required for a real run. Use --dry-run to print the schedule "
            "without importing PsychoPy."
        ) from exc
    return {"visual": visual, "core": core, "event": event, "sound": sound}


def _build_schedule(cfg: AppConfig) -> list[ScheduledEvent]:
    return build_schedule(cfg.protocol)


def _create_marker_outlet(cfg: AppConfig) -> Any:
    from resting_task.lsl_markers import LSLMarkerOutlet

    return LSLMarkerOutlet(cfg.marker_stream)


def _print_schedule(schedule: list[ScheduledEvent]) -> None:
    for item in schedule:
        print(f"{item.onset:07.3f}s {item.label} {item.phase}")


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
