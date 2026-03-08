"""
Scan output from DMC jobs for critical information such as the number of particle hits, and which detectors they occured in.
"""

# File management
import glob

# Vector math
import numpy as np

# SuperCDMS root file utilities
from cats.cdataframe import CDataFrame


def check_tree(tree_name, files, columns):
    """
    Try loading a tree with CDataFrame.
    Returns dictionary of numpy arrays if successful, otherwise None.
    """
    try:
        df = CDataFrame(tree_name, files)
        data = df.AsNumpy(columns)
        return data
    except Exception:
        return None


def inspect_file(root_file):

    print(f"\n===== {root_file} =====")

    # ---- Check g4dmcEvents ----
    events = check_tree(
        "G4SimDir/g4dmcEvent",
        [root_file],
        ["EventNum", "DetNum", "DetType"]
    )

    if events is None:
        print("No G4SimDir/g4dmcEvent tree")
    else:
        eventnum = events["EventNum"]
        detnums = np.unique(events["DetNum"])
        dettypes = np.unique(events["DetType"])

        print("G4SimDir/g4dmcEvent present")
        print("  Contents of EventNum:", eventnum)
        print("  EventNum length:", len(eventnum))
        print("  DetNum values:", detnums)
        print("  DetType values:", dettypes)

    # ---- Check mcevent ----
    mcevent = check_tree(
        "G4SimDir/mcevent",
        [root_file],
        ["HitsPerEvent"]
    )

    if mcevent is None:
        print("No G4SimDir/mcevent tree")
    else:
        hits = mcevent["HitsPerEvent"]

        print("G4SimDir/mcevent present")
        print(f"  Contains: {hits}")
        print(f"  Entries: {len(hits)}")
        print(f"  Mean HitsPerEvent: {np.mean(hits):.3f}")
        print(f"  Max HitsPerEvent: {np.max(hits)}")


def main():

    prefix = "/path/to/root/output/files/run_prefix_??????.root"

    files = sorted(glob.glob(prefix))

    print(f"Found {len(files)} files")

    for f in files:
        inspect_file(f)


if __name__ == "__main__":
    main()








