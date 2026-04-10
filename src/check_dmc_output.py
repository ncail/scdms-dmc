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
    load_event_traces
)

def main():
    # --------------------------------------------------------
    # Path to DMC output files
    # --------------------------------------------------------
    path_to_files = "/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/combined.root"

    # ---------------------------------------------------------
    # Trace plot output path
    # ---------------------------------------------------------
    output_plot_path = "/home/nevenac/projects/scdms-dmc/output/tes_traces_det2_evt0.png"

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
    test_event = events[0]

    data = load_event_traces(files[0], test_event, det_num=test_det)

    print("n traces:", len(data["Trace"]))
    print("first trace type:", type(data["Trace"][0]))
    print("first trace shape:", np.shape(data["Trace"][0]))
    print("BinWidth unique:", np.unique(data["BinWidth"]))
    print("T0 unique:", np.unique(data["T0"]))

    fig, ax = plt.subplots(figsize=(10, 6))
    t = np.arange(len(data["Trace"][6])) * data["BinWidth"][6]
    plt.plot(t, data["Trace"][6])
    fig.savefig(f"{output_plot_path}_one_channel.png", dpi=300, bbox_inches="tight")

    # exit()

    print(f"\nPlotting EventNum = {test_event} (all channels)")
    plot_event_all_channels_overlay(
        files[0], 
        test_event, 
        save_path=output_plot_path, 
        det_num=test_det, 
        flip=True, 
        normalize=True, 
        show=False
    )


if __name__ == "__main__":
    main()
