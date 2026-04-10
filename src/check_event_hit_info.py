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
    print_branch_report,
    get_g4dmcEvent_summary
)


def main():
    path_to_files = "/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/combined.root"
    files = sorted(glob.glob(path_to_files))

    # Detector number of interest
    detnum = 2

    # Get events per detector
    g4dmcEvent = get_g4dmcEvent_summary(files[0])

    event_idices_in_det_2 = g4dmcEvent['events_per_detector'][detnum]
    print("Event indices in detector 2:", event_idices_in_det_2)

    # Get the summary for a file
    summary = get_g4dmcEvent_summary(files[0])
    events_per_det = summary['events_per_detector']

    # Reload the raw arrays for verification
    with uproot.open(files[0]) as f:
        tree = f['G4SimDir/g4dmcEvent']
        det_nums = tree['DetNum'].array(library='np')
        event_nums = tree['EventNum'].array(library='np')
    print("detnum: ", det_nums)
    print("eventnum: ", event_nums)
    print("events per det: ", events_per_det)


    if len(files) == 0:
        raise FileNotFoundError("No input ROOT files found with pattern.")

    # Get the summary for a file
    print(print_branch_report(files[0]))


if __name__ == "__main__":
    main()
