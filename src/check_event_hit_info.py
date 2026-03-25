"""
Scan output root files from DMC jobs for critical information such as the number of particle hits, and which detectors they occured in.
Outputs a table where each root file is labeled by the last three characters in its name (using the macro in this repo, this will be numerical, ranging from 000-009).
"""

import glob
import numpy as np
import pandas as pd
import uproot
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_tree(tree_name, files, columns):
    """Check a single tree using uproot."""
    try:
        with uproot.open(files[0]) as f:  # Assuming single file for now
            tree = f[tree_name]
            data = tree.arrays(columns, library='np')
        return data
    except Exception as e:
        logger.warning(f"Failed to load {tree_name}: {e}")
        return None


def get_events_for_detector(dmc_files, det_num):
    """
    Get all EventNums that occurred in a specific detector from g4dmcEvent tree.

    Parameters
    ----------
    dmc_files : list of str
        List of DMC ROOT file paths
    det_num : int
        Detector number

    Returns
    -------
    np.ndarray
        Sorted unique EventNums for this detector
    """
    logger.info(f"Finding events for DetNum=={det_num}...")
    all_event_nums = []
    
    for file_path in dmc_files:
        try:
            with uproot.open(file_path) as f:
                event_tree = f['G4SimDir/g4dmcEvent']
                det_nums = event_tree['DetNum'].array(library='np')
                event_nums = event_tree['EventNum'].array(library='np')
                mask = det_nums == det_num
                all_event_nums.extend(event_nums[mask])
        except Exception as e:
            logger.error(f"Failed to get detector events from {file_path}: {e}")
            return np.array([])
    
    return np.unique(all_event_nums)


def print_detector_summary(dmc_files):
    """Print which events are in which detectors from g4dmcEvent tree."""
    logger.info("Building detector summary...")
    
    detector_events = {}
    
    # Load g4dmcEvent for all files
    for file_path in dmc_files:
        try:
            with uproot.open(file_path) as f:
                event_tree = f['G4SimDir/g4dmcEvent']
                det_nums = event_tree['DetNum'].array(library='np')
                event_nums = event_tree['EventNum'].array(library='np')
                
                # Group events by detector
                for det_num, event_num in zip(det_nums, event_nums):
                    det_num = int(det_num)
                    event_num = int(event_num)
                    if det_num not in detector_events:
                        detector_events[det_num] = set()
                    detector_events[det_num].add(event_num)
        except Exception as e:
            logger.error(f"Failed to load detector info from {file_path}: {e}")
            return
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Detector Summary (from g4dmcEvent)")
    print(f"{'='*60}")
    
    for det_num in sorted(detector_events.keys()):
        events = sorted(detector_events[det_num])
        print(f"DetNum {det_num}: {len(events)} events")
        print(f"  Events: {events}")
    
    print(f"{'='*60}\n")


def inspect_file(root_file):

    result = {}

    # ---- g4dmcEvent ----
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

    # ---- g4dmcHits ----
    hits = check_tree(
        "G4SimDir/g4dmcHits",
        [root_file],
        ["EventNum", "DetNum", "DetType"]
    )

    if hits is None:
        result["g4dmcHits_tree_exists"] = "no"
        result["Hits_EventNum_contents"] = ""
        result["Hits_DetNum_values"] = ""
        result["Hits_DetType_values"] = ""
    else:
        result["g4dmcHits_tree_exists"] = "yes"
        result["Hits_EventNum_contents"] = hits["EventNum"]
        result["Hits_DetNum_values"] = list(np.unique(hits["DetNum"]))
        result["Hits_DetType_values"] = list(np.unique(hits["DetType"]))

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

    # Print detector summary
    print_detector_summary(files)

    # Optional: save to CSV
    # df.to_csv("/home/nevenac/projects/scdms-dmc/dmc_hit_summary.csv")


if __name__ == "__main__":
    main()
