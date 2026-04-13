"""
TES Trace Viewer Package (DMC / g4dmcTES)

This module provides tools for loading, inspecting, and visualizing
Transition Edge Sensor (TES) traces produced by SuperCDMS SuperSim DMC Tower simulations.

It is designed to work with ROOT files produced by SuperSim/TESSim workflows,
and uses uproot for pure-Python access to avoid C++ ROOT dependencies.

-----------------------------------------------------------------------
DATA STRUCTURE OVERVIEW (g4dmcTES)
-----------------------------------------------------------------------

Each row in the g4dmcTES tree corresponds to a single TES trace:

    EventNum   -> g4dmcEvent identifier
    DetNum     -> detector identifier
    ChanNum    -> TES channel index
    ChanName   -> human-readable channel name
    Trace      -> waveform (array of current samples)
    T0         -> time offset (µs scale depends on simulation config)
    BinWidth   -> sampling interval per bin

A full "event" typically consists of 12 TES channels per detector.

-----------------------------------------------------------------------
KEY FEATURES
-----------------------------------------------------------------------

* Load TES traces from SuperSim DMC ROOT files (multi-file support)
* Filter by EventNum and DetNum
* Group traces by event
* Plot individual TES channels
* Overlay all channels for a single event
* Normalize and flip traces
* Save plots to file (HPC-friendly, no GUI required)

-----------------------------------------------------------------------
NOTES ON DEBUGGING
-----------------------------------------------------------------------

- Always verify filtering by BOTH EventNum and DetNum
- BinWidth must be aligned per trace row (do not reuse index after filtering)
- Use individual trace plots to validate data before overlay visualization
- x-axis cropping (xlim) can hide valid TES signals if misconfigured
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

    Example:
        data = load_event_traces("my_sim_output.root", event_num=101, det_num=1)
        first_chan_trace = data["Trace"][0]
        
        t = np.arange(len(first_chan_trace) * data["BinWidth"][0]
        plt.plot(t, first_chan_trace)
        plt.show()
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

def _get_trace_t_y(
    trace: np.ndarray,
    dt: float,
    flip: bool = False,
    normalize: bool = False
):
    """
    Convert a TES trace to time (t) and amplitude (y) arrays for plotting.
    """
    t = np.arange(trace.size) * dt * 1e-6
    y = trace.copy()

    if flip:
        y = -y

    if normalize:
        ymin, ymax = y.min(), y.max()
        y = (y - ymin) / (ymax - ymin + 1e-12)

    return t, y


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
    Note: Every channel trace from a unique CrystalSim event will have the same EventNum (index). This method filters all traces by EventNum and optionally DetNum, then plots them together in the same figure, labelled by channel.

    Parameters:
        file_path: Path to simulation ROOT file
        event_num: EventNum index of the event you want to plot traces for
        det_num  : Optional DetNum to filter by (if None, plots all detectors' channels for that event)
        xlim     : Optional tuple (xmin, xmax) to crop x-axis (time) range in microseconds
        normalize: If True, normalize each trace to [0, 1] for better visual comparison (useful if channels have different offsets or amplitudes)
        flip     : If True, flip traces vertically (multiply by -1) to match typical TES pulse shapes where signal is negative-going
        figsize  : Tuple (width, height) in inches for the figure size
        save_path: Optional path to save the figure (e.g. "myOutput/event101_traces.png"). If None, the figure will not be saved.
        show     : If True, display the figure using plt.show(). Set to False for HPC environments where GUI is not available.

    Example:
        # Get indices (EventNum) for Detector 1
        detector_1_events = get_detector_event_index("my_sim_output.root")[1]
        event_1 = detector_1_events[0]  # Get the first event for Det 1
        plot_event_all_channels_overlay(
            "my_sim_output.root",
            event_num=event_1,
            det_num=1,
            xlim=(25, 50),
            normalize=True,
            flip=True,
            save_path="myOutput/det1_event1_traces.png",
            show=False
        )
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

        t, y = _get_trace_t_y(trace, dt, flip=flip, normalize=normalize)

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
    file_path: str,
    event_num: int,
    det_num: int = None,
    normalize: bool = False,
    flip: bool = False,
    save_path: str = None
):
    """
    Plot each TES channel for a single event in its own figure.
    Note: Every trace from a unique CrystalSim event will have the same EventNum (index). This method filters all traces by EventNum and optionally DetNum, then plots each trace individually, labelled by channel.
    
    Parameters:
        file_path: Path to simulation ROOT file
        event_num: EventNum index of the event you want to plot traces for
        det_num  : Optional DetNum to filter by (if None, plots all detectors' channels for that event)
        normalize: If True, normalize each trace to [0, 1] for better visual comparison (useful if channels have different offsets or amplitudes)
        flip     : If True, flip traces vertically (multiply by -1) to match typical TES pulse shapes where signal is negative-going
        save_path: Optional path to save the figure (e.g. "myOutput/event1"). If None, the figure will not be saved. Figures are named "event{event_num}_chan{chan}.png" within the save_path directory.

    Example:
        # Get indices (EventNum) for Detector 2
        detector_2_events = get_detector_event_index("my_sim_output.root")[2]
        event_1 = detector_2_events[0]  # Get the first event for Det 2
        plot_traces_individually(
            "my_sim_output.root",
            event_num=event_1,
            det_num=1,
            normalize=True,
            flip=True,
            save_path="myOutput/det1_event1_traces"
        )
    """

    os.makedirs(save_path, exist_ok=True)

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

        t, y = _get_trace_t_y(trace, dt, flip=flip, normalize=normalize)

        fig, ax = plt.subplots(figsize=(8,4))

        ax.plot(t, y, linewidth=1)

        ax.set_title(f"Event {event_num}  |  Channel {chan}")
        ax.set_xlabel("Time (µs)")
        ax.set_ylabel("Amplitude")
        ax.grid(alpha=0.3)

        save_file = f"{save_path}/event{event_num}_chan{chan}.png"
        plt.savefig(save_file, dpi=150)
        plt.close()

        print("Saved:", save_file)


