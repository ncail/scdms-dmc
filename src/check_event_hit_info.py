"""
Scan output ROOT files from DMC jobs for critical information such as the number of particle hits and which detectors they occurred in.
Outputs a table where each root file is labeled by the last three characters in its name (using the macro in this repo, this will be numerical, ranging from 000-009).
"""

import glob
import numpy as np
import pandas as pd
import uproot

# Import common DMC output access functions
from dmc_output_access import (
    get_g4dmcTES_summary,
    print_branch_report,
    get_g4dmcEvent_summary,
    get_g4dmcTES_summary
)


def main():
    path_to_files = "/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/combined.root"
    files = sorted(glob.glob(path_to_files))

    if len(files) == 0:
        raise FileNotFoundError("No input ROOT files found with pattern.")

    # Get the summary for a file
    print(print_branch_report(files[0]))


if __name__ == "__main__":
    main()
