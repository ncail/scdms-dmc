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
from cats.cdataframe import CDataFrame

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
# UTILITIES
# ============================================================

def normalizer(trace: np.ndarray) -> np.ndarray:
    """
    Normalize a TES trace to the range [0, 1] using min-max normalization.
    """
    min_val = np.min(trace)
    max_val = np.max(trace)
    
    if max_val - min_val == 0:
        return trace  # Avoid division by zero if all values are the same
    
    normalized = (trace - min_val) / (max_val - min_val + 1e-12)
    
    return normalized


def build_cut_string(
        events: int | List[int], 
        det_num: int = None
) -> str:
    """
    Build an uproot cut expression for filtering a tree by DetNum-EventNum indices.

    Example usage:
        cut_str = build_cut_string(events=[1, 5, 10], det_num=2)
        # Result: "(DetNum == 2) & ((EventNum == 1) | (EventNum == 5) | (EventNum == 10))"
        data = myTree.arrays(
            ["Trace", "ChanNum", "T0", "BinWidth"], 
            cut=cut_str, 
            library="np"
        )
    """
    if isinstance(events, int):
        cut_str = f"EventNum == {events}"
    else:
        events = list(events)
        cut_str = " | ".join(f"(EventNum == {e})" for e in events)

    if det_num is not None:
        cut_str = f"(DetNum == {det_num}) & ({cut_str})"

    return cut_str


# ============================================================
# DATA ACCESS LAYER
# ============================================================

def get_event_traces(
        file_path: str, 
        event_num: int,
        det_num: int = None        
) -> Dict[str, np.ndarray]:
    """
    Load all TES traces for a single g4dmcTES EventNum.

    Returns grouped channel data for plotting.

    **Note: does not leverage CDataFrame. Prefer to use get_traces_for_event() which is more robust.**

    Example:
        data = get_event_traces("my_sim_output.root", event_num=101, det_num=1)
        first_chan_trace = data["Trace"][0]
        
        t = np.arange(len(first_chan_trace) * data["BinWidth"][0]
        plt.plot(t, first_chan_trace)
        plt.show()
    """
    
    with uproot.open(file_path) as f:
        tree = f["G4SimDir/g4dmcTES"]

        # Get meta info first, small and fast, to find indices of relevant entries
        meta = tree.arrays(["EventNum", "DetNum"], library="np")

        mask = (meta["EventNum"] == event_num) & (meta["DetNum"] == det_num)
        entries = np.where(mask)[0]

        # Load only this slice of the trace data
        data = tree.arrays(
            ["EventNum", "DetNum", "Trace", "ChanNum", "ChanName", "T0", "BinWidth"],
            entry_start=entries.min(),
            entry_stop=entries.max() + 1,
            library="np"
        )

    return {
        "EventNum": data["EventNum"].astype(int),
        "DetNum": data["DetNum"].astype(int),
        "ChanNum": data["ChanNum"].astype(int),
        "ChanName": data["ChanName"].astype(str),
        "Trace": data["Trace"],
        "T0": data["T0"],
        "BinWidth": data["BinWidth"]
    }


def get_traces_for_events(
    file_path: str,
    events: int | List[int],
    det_num: int = None
) -> Dict[int, Dict[str, np.ndarray]]:
    """
    Load TES traces for multiple events, grouped by EventNum.

    Example:
        event_nums = [101, 102, 103]
        data = get_traces_for_events("my_sim_output.root", event_nums, det_num=1)
        # data is a dict of NumPy arrays, aligned by row: {"Trace": [...], "ChanNum": [...], ...}
        traces = data["Trace"]
        plt.plot(traces[0])  # Plot first trace
        plt.title(f"Trace for Channel {data["ChanName"][0]}, Event {data["EventNum"][0]}")
    """
    if isinstance(events, int):
        events = [events]

    cut = build_cut_string(events, det_num)
    
    # Use CDataFrame to filter the tree by event and detector
    data = CDataFrame('G4SimDir/g4dmcTES', file_path).Filter(cut)

    # Organize into a dictionary
    event_num   = data.AsNumpy(['EventNum'])['EventNum']
    det         = data.AsNumpy(['DetNum'])['DetNum']
    chan_num    = data.AsNumpy(['ChanNum'])['ChanNum']
    chan_name   = data.AsNumpy(['ChanName'])['ChanName']
    trace       = data.AsNumpy(['Trace'])['Trace']
    t0          = data.AsNumpy(['T0'])['T0']
    bin_width   = data.AsNumpy(['BinWidth'])['BinWidth']

    data_dict = {
        "EventNum": event_num,
        "DetNum": det,
        "ChanNum": chan_num,
        "ChanName": chan_name,
        "Trace": trace,
        "T0": t0,
        "BinWidth": bin_width
    }

    return data_dict


def normalize_traces(
    traces: np.ndarray
) -> np.ndarray:
    """
    Normalize TES traces 

    Example:
        data = get_event_traces("my_sim_output.root", event_num=101, det_num=1)
        traces = data["Trace"]
        normalized_traces = normalize_traces(traces)

        # Plot normalized traces for this detector event
        t = np.arange(len(first_chan_trace) * data["BinWidth"][0]
        plt.plot(t, normalized_traces[0])  # Plot first channel as example
        plt.show()
    """

    for i, trace in enumerate(traces):
        trace = np.asarray(trace)
        
        if np.isnan(trace).all():
            continue  # Skip empty traces
        
        trace = normalizer(trace)
        traces[i] = trace
    
    return traces


def flip_traces(
    traces: np.ndarray      
) -> np.ndarray:
    for i, trace in enumerate(traces):
        trace = np.asarray(trace)
        
        if np.isnan(trace).all():
            continue  # Skip empty traces
        
        trace = -trace
        traces[i] = trace
    
    return traces


def baseline_correct(trace, n=500):
    trace = np.asarray(trace)
    baseline = np.mean(trace[:n])
    return trace - baseline


# ============================================================
# PLOTTING LAYER
# ============================================================

def get_trace_t_y(
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
        y = normalizer(y)

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

    data = get_event_traces(file_path, event_num, det_num=det_num)

    traces = data["Trace"]
    chans = data["ChanName"]
    dt_all = data["BinWidth"]

    fig, ax = plt.subplots(figsize=figsize)

    for i, (trace, chan, dt) in enumerate(zip(traces, chans, dt_all)):
        
        trace = np.asarray(trace)

        # Skip empty traces
        if np.isnan(trace).all():
            print(f"Skipping Chan {chan} (all NaN)")
            continue

        t, y = get_trace_t_y(trace, dt, flip=flip, normalize=normalize)

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

    data = get_event_traces(file_path, event_num, det_num=det_num)

    traces = data["Trace"]
    chans = data["ChanName"]
    dt_all = data["BinWidth"]

    for i, (trace, chan, dt) in enumerate(zip(traces, chans, dt_all)):

        trace = np.asarray(trace)

        # Skip empty traces
        if np.isnan(trace).all():
            print(f"Skipping Chan {chan} (all NaN)")
            continue

        t, y = get_trace_t_y(trace, dt, flip=flip, normalize=normalize)

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


