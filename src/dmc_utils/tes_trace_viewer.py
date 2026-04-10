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

# File system
import os

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
    det_num: int = None,
    xlim: Tuple[float, float] = None,
    normalize: bool = False,
    flip: bool = False,
    figsize: Tuple[int, int] = (10, 6),
    save_path: str = None,
    show: bool = True,
):
    """
    Plot ALL TES channels for a single event on the same axes.
    """

    data = load_event_traces(file_path, event_num, det_num=det_num)

    traces = data["Trace"]
    chans = data["ChanNum"]
    dt_all = data["BinWidth"]

    fig, ax = plt.subplots(figsize=figsize)

    for i, (trace, chan, dt) in enumerate(zip(traces, chans, dt_all)):

        trace = np.asarray(trace)

        # Skip empty traces
        if np.isnan(trace).all():
            print(f"Skipping Chan {chan} (all NaN)")
            continue

        t = np.arange(trace.size) * dt * 1e-6
        y = trace.copy()

        if flip:
            y = -y

        if normalize:
            ymin, ymax = y.min(), y.max()
            y = (y - ymin) / (ymax - ymin + 1e-12)

        ax.plot(t, y, linewidth=1, label=f"Channel {chan}")

    ax.set_title(f"TES Event {event_num} (all channels)")
    ax.set_xlabel("Time (µs)")
    ax.set_ylabel("Amplitude")
    if xlim is not None:
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

    plt.close(fig)  # Important for HPC memory hygiene

    return fig


def plot_traces_individually(
    file_path,
    event_num,
    det_num=None,
    normalize=False,
    flip=False,
    out_dir="trace_debug"
):

    os.makedirs(out_dir, exist_ok=True)

    data = load_event_traces(file_path, event_num, det_num=det_num)

    traces = data["Trace"]
    chans = data["ChanNum"]
    dt_all = data["BinWidth"]

    for i, (trace, chan, dt) in enumerate(zip(traces, chans, dt_all)):

        trace = np.asarray(trace)

        # Skip empty traces
        if np.isnan(trace).all():
            print(f"Skipping Chan {chan} (all NaN)")
            continue

        t = np.arange(trace.size) * dt * 1e-6
        y = trace.copy()

        if flip:
            y = -y

        if normalize:
            ymin, ymax = y.min(), y.max()
            y = (y - ymin) / (ymax - ymin + 1e-12)

        fig, ax = plt.subplots(figsize=(8,4))

        ax.plot(t, y, linewidth=1)

        ax.set_title(f"Event {event_num}  |  Channel {chan}")
        ax.set_xlabel("Time (µs)")
        ax.set_ylabel("Amplitude")
        ax.grid(alpha=0.3)

        save_file = f"{out_dir}/event{event_num}_chan{chan}.png"
        plt.savefig(save_file, dpi=150)
        plt.close()

        print("Saved:", save_file)


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
