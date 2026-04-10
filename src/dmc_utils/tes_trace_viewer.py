"""
TES Event Viewer
-----------------------------
Minimal, clean interface for working with g4dmcTES ROOT output.

Core design:
    Detector → Events → TES traces → Plot all channels

Performs:
    1. Event indexing per detector
    2. Event trace loading
    3. Event-level plotting (all 12 channels)

Dependencies:
    - uproot
    - numpy
    - matplotlib
"""


# Array math and manipulation
import numpy as np

# Root file handling
import uproot

# For providing default keys
from collections import defaultdict

# Type hints
from typing import Dict, List, Tuple

# Plotting
import matplotlib
matplotlib.use("Agg")  # non-GUI backend for HPC
import matplotlib.pyplot as plt

# Configure logging 
import logging 
logger = logging.getLogger(__name__)


# ============================================================
# INDEXING LAYER
# ============================================================

def get_detector_event_index(file_path: str) -> Dict[int, List[int]]:
    """
    Map each detector (DetNum) → sorted unique EventNum list.

    This is the ONLY grouping logic needed for navigation.
    """
    with uproot.open(file_path) as f:
        tree = f["G4SimDir/g4dmcTES"]
        det = tree["DetNum"].array(library="np")
        evt = tree["EventNum"].array(library="np")

    index = defaultdict(set)

    for d, e in zip(det, evt):
        index[int(d)].add(int(e))

    return {d: sorted(list(e)) for d, e in index.items()}


# ============================================================
# DATA ACCESS LAYER
# ============================================================

def load_event_traces(
        file_path: str, 
        event_num: int,
        det_num: int = None        
) -> Dict[str, np.ndarray]:
    """
    Load all TES traces for a single g4dmcTES EventNum.

    Returns grouped channel data for plotting.
    """
    with uproot.open(file_path) as f:
        tree = f["G4SimDir/g4dmcTES"]
        data = tree.arrays(
            ["EventNum", "DetNum", "ChanNum", "Trace", "T0", "BinWidth", "ChanName"],
            library="np"
        )

    mask = data["EventNum"] == event_num

    if det_num is not None:
        mask &= (data["DetNum"] == det_num)

    return {
        "DetNum": data["DetNum"][mask].astype(int),
        "ChanNum": data["ChanNum"][mask].astype(int),
        "ChanName": data["ChanName"][mask].astype(str),
        "Trace": data["Trace"][mask],
        "T0": data["T0"][mask],
        "BinWidth": data["BinWidth"][mask]
    }


# ============================================================
# PLOTTING LAYER
# ============================================================

def plot_event_all_channels_overlay(
    file_path: str,
    event_num: int,
    xlim: Tuple[float, float] = (-1, 10),
    normalize: bool = False,
    flip: bool = False,
    figsize: Tuple[int, int] = (10, 6),
    save_path: str = None,
    show: bool = True,
):
    """
    Plot ALL TES channels for a single event on the same axes.
    """

    data = load_event_traces(file_path, event_num)

    traces = data["Trace"]
    chans = data["ChanNum"]

    fig, ax = plt.subplots(figsize=figsize)

    for i, (trace, chan) in enumerate(zip(traces, chans)):

        # t0 = data["T0"][i]
        dt = data["BinWidth"][i]

        t = np.arange(len(trace)) * dt * 1e-6

        y = trace.copy()

        # Optional transforms
        if flip:
            y = -y

        if normalize:
            y = (y - np.min(y)) / (np.max(y) - np.min(y) + 1e-12)

        ax.plot(t, y, linewidth=1, alpha=0.8, label=f"Ch {chan}")

    ax.set_title(f"TES Event {event_num} (all channels)")
    ax.set_xlabel("Time (µs)")
    ax.set_ylabel("Amplitude")
    ax.set_xlim(xlim)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=12, ncol=2)

    # -----------------------------------
    # HPC save logic
    # -----------------------------------
    if save_path is not None:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"[saved] {save_path}")

    if show:
        plt.show()

    plt.close(fig)  # important for HPC memory hygiene

    return fig


# ============================================================
# HIGH-LEVEL USER API
# ============================================================

def plot_detector_event(
    file_path: str,
    det_num: int,
    event_index: int = 0,
):
    """
    Convenience function:

    Detector → pick event → plot all channels.
    """
    index = get_detector_event_index(file_path)

    if det_num not in index:
        raise ValueError(f"No detector {det_num} found")

    events = index[det_num]

    if not events:
        raise ValueError(f"No events for detector {det_num}")

    event_num = events[event_index]

    print(f"Detector {det_num} → Event {event_num}")

    return plot_event_all_channels_overlay(file_path, event_num)


# ============================================================
# OPTIONAL UTILITY
# ============================================================

def list_detector_events(file_path: str) -> None:
    """
    Print detectors and available events.
    """
    index = get_detector_event_index(file_path)

    print("\nDetector → Event Summary")
    print("=" * 40)

    for det, events in sorted(index.items()):
        print(f"Det {det}: {len(events)} events")
        print(f"   {events[:10]}{' ...' if len(events) > 10 else ''}")

    print("=" * 40)
