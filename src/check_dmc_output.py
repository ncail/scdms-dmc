"""
Scan output ROOT files from DMC jobs for critical information such as the number of particle hits and which detectors they occurred in.
Output a summary report to the terminal. This is a quick check to confirm that the DMC job produced expected results before diving into more detailed analysis.
Output TES traces for a sample detector and event to visually confirm that the traces look reasonable (e.g. not all zeros, not all noise, etc).
"""

# File handling
import glob

# Dataframes
import pandas as pd

# Array math
import numpy as np

# Plotting
import matplotlib.pyplot as plt

# Import common DMC output access functions
from dmc_utils import (
    print_branch_report,
    get_detector_event_index,
    plot_event_all_channels_overlay,
    plot_traces_individually,
    load_event_traces
)

def main():
    # --------------------------------------------------------
    # Path to DMC output files
    # --------------------------------------------------------
    path_to_files = "/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/combined.root"

    files = sorted(glob.glob(path_to_files))

    if len(files) == 0:
        raise FileNotFoundError("No input ROOT files found with pattern.")

    # Get the summary for a file
    print(print_branch_report(files[0]))

    print("\nLoading TES event index...")
    index = get_detector_event_index(files[0])

    print("\nDetector → number of events:")
    for det, events in sorted(index.items()):
        print(f"  Det {det}: {len(events)} events")

    # --------------------------------------------------------
    # Plot traces from Detector 2
    # --------------------------------------------------------
    test_det = 2

    if test_det not in index:
        print(f"\nDetector {test_det} not found in file.")
        return

    events = index[test_det]

    if not events:
        print(f"\nNo events found for detector {test_det}.")
        return

    print(f"\nTesting detector {test_det}")
    print(f"Available events: {events}")

    # Pick first event
    # test_event = events[0]

    # ---------------------------------------------------------
    # Trace plot output path
    # ---------------------------------------------------------
    output_plot_path = f"/home/nevenac/projects/scdms-dmc/output/"

    for evt in events:
        print(f"\nPlotting EventNum = {evt} (all channels)")
        plot_event_all_channels_overlay(
            files[0], 
            evt, 
            save_path=f"{output_plot_path}/tes_traces_det{test_det}_evt{evt}.png", 
            det_num=test_det, 
            flip=True, 
            normalize=False, 
            xlim=(25, 50),      # In microseconds
            show=False
        )

        print(f"\nPlotting EventNum = {evt} (all channels - normalized)")
        plot_event_all_channels_overlay(
            files[0], 
            evt, 
            save_path=f"{output_plot_path}/tes_traces_normalized_det{test_det}_evt{evt}.png", 
            det_num=test_det, 
            flip=True, 
            normalize=True, 
            xlim=(25, 50),      # In microseconds
            show=False
        )

if __name__ == "__main__":
    main()
