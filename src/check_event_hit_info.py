"""
Scan output ROOT files from DMC jobs for critical information such as the number of particle hits and which detectors they occurred in.
Outputs a table where each root file is labeled by the last three characters in its name (using the macro in this repo, this will be numerical, ranging from 000-009).
"""

import glob
import numpy as np
import pandas as pd

# Import common DMC output access functions
from dmc_output_access import inspect_file, print_detector_summary


def main():
    files = sorted(glob.glob("/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/combined.root"))

    if len(files) == 0:
        raise FileNotFoundError("No input ROOT files found with pattern.")

    # Print detector summary using g4dmcHits mapping
    print_detector_summary(files)

    # Inspect each file and collect info from inspect_file()
    rows = []
    for f in files:
        info = inspect_file(f)
        info["filename"] = f
        rows.append(info)

    df = pd.DataFrame(rows)
    print("\nSummary table:\n")
    print(df)

    # Optional: save to CSV
    # df.to_csv("/home/nevenac/projects/scdms-dmc/dmc_hit_summary.csv", index=False)


if __name__ == "__main__":
    main()
