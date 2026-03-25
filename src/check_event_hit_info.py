"""
Scan output root files from DMC jobs for critical information such as the number of particle hits, and which detectors they occured in.
Outputs a table where each root file is labeled by the last three characters in its name (using the macro in this repo, this will be numerical, ranging from 000-009).
"""

import glob
import numpy as np
import pandas as pd

from cats.cdataframe import CDataFrame


def check_tree(tree_name, files, columns):
    try:
        df = CDataFrame(tree_name, files)
        data = df.AsNumpy(columns)
        return data
    except Exception:
        return None


def get_run_id(filepath):
    """Extract last 3 digits from filename."""
    name = filepath.split("/")[-1]
    return name.split("_")[-1].split(".")[0][-3:]


def inspect_file(root_file):

    result = {}

    # ---- g4dmcEvents ----
    events = check_tree(
        "G4SimDir/g4dmcEvent",
        [root_file],
        ["EventNum", "DetNum", "DetType"]
    )

    if events is None:
        result["g4dmcEvent_tree_exists"] = "no"
        result["EventNum_contents"] = ""
        result["DetNum_values"] = ""
        result["DetType_values"] = ""
    else:
        result["g4dmcEvent_tree_exists"] = "yes"
        result["EventNum_contents"] = events["EventNum"]
        result["DetNum_values"] = list(np.unique(events["DetNum"]))
        result["DetType_values"] = list(np.unique(events["DetType"]))

    # ---- mcevent ----
    mcevent = check_tree(
        "G4SimDir/mcevent",
        [root_file],
        ["HitsPerEvent"]
    )

    if mcevent is None:
        result["mcevent_tree_exists"] = "no"
        result["HitsPerEvent_contents"] = ""
    else:
        hits = mcevent["HitsPerEvent"]
        result["mcevent_tree_exists"] = "yes"
        result["HitsPerEvent_contents"] = hits

    return result


def main():

    files = sorted(glob.glob("/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/combined.root"))

    table = {}

    for f in files:
        run = get_run_id(f)
        table[run] = inspect_file(f)

    df = pd.DataFrame(table)

    print("\nSummary table:\n")
    print(df)

    # Optional: save to CSV
    # df.to_csv("/home/nevenac/projects/scdms-dmc/dmc_hit_summary.csv")


if __name__ == "__main__":
    main()
