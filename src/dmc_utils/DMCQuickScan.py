"""
DMC Quick Scan + TES Trace Sanity Tool

- Validates ROOT outputs
- Prints detector/event structure
- Generates TES trace sanity plots
"""

# File handling
import glob
from pathlib import Path

# Class definitions
from dataclasses import dataclass

# Type hints
from typing import Optional, Union, Tuple, List, Literal

# Shell process
import subprocess

# Utils from DMC package
from dmc_utils import (
    print_branch_report,
    list_detector_events,
    plot_event_all_channels_overlay,
)


# ------------------------------------------------------------
# Configuration object
# ------------------------------------------------------------

@dataclass
class ScanConfig:
    file_pattern: str
    output_dir: str
    detector: int = 1
    flip: bool = True
    xlim: tuple = (25, 50)      # In microseconds, adjust as needed
    save_all_events: bool = True
    file_mode: Literal["single", "combined"] = "single"
    combined_name: str = "combined.root"


# ------------------------------------------------------------
# ROOT file utilities
# ------------------------------------------------------------

def combine_root_files(
    input_files: List[str],
    output_file: str,
    overwrite: bool = True,
) -> str:
    """
    Combine multiple ROOT files into one using `hadd`.

    This is a thin wrapper around the ROOT CLI tool.

    Parameters
    ----------
    input_files : List[str]
        List of ROOT files to combine.
    output_file : str
        Path to output combined ROOT file.
    overwrite : bool
        If True, overwrite existing output file.

    Returns
    -------
    str
        Path to combined ROOT file.
    """

    if not input_files:
        raise ValueError("No input ROOT files provided.")

    out = Path(output_file)

    if out.exists() and not overwrite:
        print(f"[combine_root_files] Using existing file: {output_file}")
        return str(out)

    cmd = ["hadd", "-f" if overwrite else "", output_file, *input_files]
    cmd = [c for c in cmd if c]  # remove empty flags

    print("[combine_root_files] Running:", " ".join(cmd))

    subprocess.run(cmd, check=True)

    return str(out)


EventRange = Optional[Union[int, Tuple[int, int]]]
def resolve_event_range(events: List[int], event_range: EventRange):
    """
    Convert user-provided event range into a concrete list of events.

    Parameters
    ----------
    events : list[int]
        Full list of events.
    event_range :
        - None -> all events
        - int -> first N events
        - (start, stop) -> slice of events

    Returns
    -------
    list[int]
        Selected subset of events.
    """

    if not events:
        return []

    if event_range is None:
        return events

    # first N events
    if isinstance(event_range, int):
        return events[:event_range] # Zero-based indexing

    # slice (start, stop)
    if isinstance(event_range, tuple):
        start, stop = event_range
        return events[start:stop]   # Zero-based indexing

    raise ValueError(f"Invalid event_range: {event_range}. Number of events is {len(events)}.")


# ------------------------------------------------------------
# Core runner
# ------------------------------------------------------------

class DMCQuickScan:

    def __init__(self, config: ScanConfig):
        self.cfg = config
        self.files = sorted(glob.glob(config.file_pattern))

        if not self.files:
            raise FileNotFoundError(
                f"No ROOT files found for pattern: {config.file_pattern}"
            )

        Path(self.cfg.output_dir).mkdir(parents=True, exist_ok=True)

        # ----------------------------------------------------
        # File selection logic
        # ----------------------------------------------------
        if self.cfg.file_mode == "single":
            self.file = self.files[0]

        elif self.cfg.file_mode == "combined":
            self.file = combine_root_files(
                self.files,
                str(Path(self.cfg.output_dir) / self.cfg.combined_name),
            )

        else:
            raise ValueError(f"Unknown file_mode: {self.cfg.file_mode}")

    # --------------------------------------------------------

    def print_summary(self):
        print_branch_report(self.file)

    # --------------------------------------------------------

    def get_tessim_events(self):
        list_detector_events(self.file, branch_name="G4SimDir/g4dmcTES", unique=True)

    # --------------------------------------------------------

    def run_sanity_plots(self, event_range: EventRange = None):
        det = self.cfg.detector

        if det not in self.index:
            print(f"\nDetector {det} not found.")
            return

        events = self.index[det]
        events = resolve_event_range(events, event_range)

        if not events:
            print(f"\nNo events for detector {det}.")
            return

        print(f"\nRunning sanity plots for Det {det}")
        print(f"Events: {events}")

        for evt in events:

            base = f"det{det}_evt{evt}"

            # --------------------------------------------------
            # Raw
            # --------------------------------------------------
            print(f"Plotting event {evt} (raw)")
            plot_event_all_channels_overlay(
                self.file,
                evt,
                det_num=det,
                flip=self.cfg.flip,
                normalize=False,
                xlim=self.cfg.xlim,
                show=False,
                save_path=str(Path(self.cfg.output_dir) / f"raw_{base}.png"),
            )

            # --------------------------------------------------
            # Normalized
            # --------------------------------------------------
            print(f"Plotting event {evt} (normalized)")
            plot_event_all_channels_overlay(
                self.file,
                evt,
                det_num=det,
                flip=self.cfg.flip,
                normalize=True,
                xlim=self.cfg.xlim,
                show=False,
                save_path=str(Path(self.cfg.output_dir) / f"norm_{base}.png"),
            )
