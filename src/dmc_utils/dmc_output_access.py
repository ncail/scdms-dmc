"""
DMC Output Access Module

Common functions for reading and processing SuperCDMS DMC ROOT file outputs from SuperSim of Tower configurations.
Uses uproot for pure-Python ROOT file reading to avoid C++ binding issues using CATs (SuperCDMS-developed package).

Branch semantics:
- G4SimDir/mcevent: Monte Carlo events. Each entry corresponds to a Geant4 event that led to energy depositions in detectors.
  The sum of HitsPerEvent is the total number of SourceSim-level hits.
- G4SimDir/g4dmcHits: Detector hits after hit merging. EventNum here is the merged hit event identifier.
- G4SimDir/g4dmcEvent: DMC event records that are passed on to CrystalSim. This count may exceed the raw Geant4 event count because individual Geant4 interactions can produce multiple DMC events (e.g. multi-detector or separate hits in the same crystal).
- G4SimDir/g4dmcTES: Output from TESSim per channel. The expected record count is roughly g4dmcEvent * number of channels.

Use `print_branch_report(file_path)` to display an informative summary of all DMC branches present in the file.
"""

# Array math and manipulation
import numpy as np

# Root file handling
import uproot

# For providing default keys
from collections import defaultdict

# Configure logging 
import logging 
logger = logging.getLogger(__name__)


# -----------------------------------------------------------
# Low-level tree accessors
# -----------------------------------------------------------
def get_tree(file_path: str, tree_name: str):
    """
    Return a ROOT tree object from the file.

    Parameters
    ----------
    file_path : str
        Path to ROOT file
    tree_name : str
        Full tree name (e.g. 'G4SimDir/g4dmcEvent')

    Returns
    -------
    uproot.TTree or None
    """
    try:
        f = uproot.open(file_path)

        if tree_name not in f:
            logger.warning(f"{tree_name} not found in {file_path}")
            return None

        return f[tree_name]

    except Exception as e:
        logger.error(f"Failed opening {tree_name} in {file_path}: {e}")
        return None


def get_tree_arrays(
        file_path: str, 
        tree_name: str, 
        branches: list[str] | None = None
    ):
    """
    Return arrays from a ROOT tree.

    Parameters
    ----------
    file_path : str
    tree_name : str
    branches : list[str] or None
        If None, load all branches.

    Returns
    -------
    dict[str, np.ndarray] or None
    """
    try:
        with uproot.open(file_path) as f:

            if tree_name not in f:
                logger.warning(f"{tree_name} not found in {file_path}")
                return None

            tree = f[tree_name]

            if branches is None:
                return tree.arrays(library="np")

            return tree.arrays(branches, library="np")

    except Exception as e:
        logger.error(f"Failed reading arrays from {tree_name}: {e}")
        return None


def get_mcevent_tree(file_path: str):
    """Return G4SimDir/mcevent tree."""
    return get_tree(file_path, "G4SimDir/mcevent")


def get_g4dmcHits_tree(file_path: str):
    """Return G4SimDir/g4dmcHits tree."""
    return get_tree(file_path, "G4SimDir/g4dmcHits")


def get_g4dmcEvent_tree(file_path: str):
    """Return G4SimDir/g4dmcEvent tree."""
    return get_tree(file_path, "G4SimDir/g4dmcEvent")


def get_g4dmcTES_tree(file_path: str):
    """Return G4SimDir/g4dmcTES tree."""
    return get_tree(file_path, "G4SimDir/g4dmcTES")


# -----------------------------------------------------------
# Core high-level utilities
# -----------------------------------------------------------

def compute_events_per_detector(
        det_nums: np.ndarray, 
        event_nums: np.ndarray,
        unique: bool = False
    ) -> dict[int, list[int]]:
    """
    Map each detector to the sorted list of unique events it recorded.
    
    Example 
    ------- 
    If, in the chosen branch, EventNum and DetNum are: 
    EventNum: [1, 1, 2, 3, 3, 4] 
    DetNum: [1, 2, 2, 2, 1, 2] 
    Then the output will be: { 1: [1, 3], 2: [1, 2, 3, 4] } 
    --> Indicating that detector 1 had events 1 and 3, while detector 2 had events 1, 2, 3 and 4. 
    
    Note: some events may occur in multiple detectors, and some "events" may occur multiple times in a detector, such as in the TES tree where one DMC event produces 12 TES traces. Each trace has the same "event" EventNum identifier.
    
    This function will return all EventNum identifiers for each DetNum, including duplicates. The caller can choose to apply np.unique if they want only unique event counts per detector.
    """
    if unique:
        # Use a set to automatically handle uniqueness
        events = defaultdict(set)

        for det, evt in zip(det_nums, event_nums):
            events[int(det)].add(int(evt))

        # Convert sets back to sorted lists
        return {det: sorted(list(evts)) for det, evts in events.items()}
    
    else:
        # Preserve all event occurrences, including duplicates
        events = defaultdict(list)

        for det, evt in zip(det_nums, event_nums):
            events[int(det)].append(int(evt))

        return dict(events)


def _summarize_tree(
        file_path: str, 
        tree_name: str, 
        branches: list[str]
    ) -> dict:
    """
    Generic ROOT tree summarizer.

    Reads specified branches and returns summary statistics.
    """
    result = {}

    try:
        with uproot.open(file_path) as f:

            if tree_name not in f:
                result["exists"] = False
                return result

            tree = f[tree_name]
            arrays = tree.arrays(branches, library="np")

            result["exists"] = True
            result["total_records"] = int(len(next(iter(arrays.values()))))

            # Unique counts
            for name, arr in arrays.items():
                result[f"unique_{name}"] = int(len(np.unique(arr)))

            # Detectors
            if "DetNum" in arrays:
                result['detectors_with_events'] = [int(x) for x in np.unique(arrays["DetNum"])]

            # Event per detector if possible
            if "DetNum" in arrays and "EventNum" in arrays:
                # Get total event counts per detector, including duplicates (e.g. for TES tree where one DMC event produces 12 traces with the same EventNum)
                events_per_det = compute_events_per_detector(arrays["DetNum"], arrays["EventNum"])
                result["events_per_detector"] = events_per_det
                result['total_detector_events'] = sum((len(evts)) for evts in result['events_per_detector'].values())

                # Get unqiue event counts per detector
                unique_events_per_det = compute_events_per_detector(arrays["DetNum"], arrays["EventNum"], unique=True)
                result["unique_events_per_detector"] = unique_events_per_det
                result['total_unique_detector_events'] = sum((len(evts)) for evts in result['unique_events_per_detector'].values())

    except Exception as e:
        logger.error(f"Failed reading {tree_name} from {file_path}: {e}")
        result["exists"] = False

    return result


# -----------------------------------------------------------
# Branch specific summaries
# -----------------------------------------------------------

def get_mcevent_summary(file_path: str) -> dict:
    """Summary for G4SimDir/mcevent."""
    try:
        with uproot.open(file_path) as f:

            if "G4SimDir/mcevent" not in f:
                return {"exists": False}

            hits = f["G4SimDir/mcevent"]["HitsPerEvent"].array(library="np")

            return {
                "exists": True,
                "event_count": int(len(hits)),
                "total_hits": int(np.sum(hits)),
            }

    except Exception as e:
        logger.error(f"Failed reading mcevent from {file_path}: {e}")
        return {"exists": False}


def get_g4dmcHits_summary(file_path: str) -> dict:
    return _summarize_tree(file_path, "G4SimDir/g4dmcHits", ["EventNum", "DetNum"])


def get_g4dmcEvent_summary(file_path: str) -> dict:
    return _summarize_tree(file_path, "G4SimDir/g4dmcEvent", ["EventNum", "DetNum"])


def get_g4dmcTES_summary(file_path: str) -> dict:
    return _summarize_tree(file_path, "G4SimDir/g4dmcTES", ["EventNum", "ChanNum", "DetNum"])


# -----------------------------------------------------------
# File level summary
# -----------------------------------------------------------

def summarize_branch_counts(file_path: str) -> dict:
    """Return summaries for all major DMC branches."""
    return {
        "mcevent": get_mcevent_summary(file_path),
        "g4dmcHits": get_g4dmcHits_summary(file_path),
        "g4dmcEvent": get_g4dmcEvent_summary(file_path),
        "g4dmcTES": get_g4dmcTES_summary(file_path),
    }


# -----------------------------------------------------------
# Reporting
# -----------------------------------------------------------

BRANCH_DESCRIPTIONS = {
    "G4SimDir/mcevent":
        "Monte Carlo Geant4 events. Sum(HitsPerEvent) gives total SourceSim hits.",

    "G4SimDir/g4dmcHits":
        "Detector hits after hit merging.",

    "G4SimDir/g4dmcEvent":
        "Events passed to CrystalSim; one Geant4 event may produce multiple.",

    "G4SimDir/g4dmcTES":
        "TESSim trace output per channel."
}


def print_branch_report(file_path: str) -> None:
    """Print a readable report of DMC ROOT branch contents."""

    summary = summarize_branch_counts(file_path)

    print("\n" + "=" * 80)
    print(f"DMC Branch Report")
    print(file_path)
    print("=" * 80 + "\n")

    for branch, desc in BRANCH_DESCRIPTIONS.items():

        key = branch.split("/")[-1]
        data = summary.get(key, {})

        print(branch)
        print("  Description:", desc)

        if not data.get("exists"):
            print("  Present: no\n")
            continue

        print("  Present: yes")
        for k, v in data.items():
            if k == "events_per_detector" or k == "unique_events_per_detector":
                print(f"  {k}:")
                for det, evts in sorted(v.items()):
                    print(f"    DetNum {det}: {len(evts)} events")
            # Skip "exists" key, was handled earlier.
            elif k != "exists":
                print(f"  {k}: {v}")

        print()

    print("=" * 80 + "\n")