"""
DMC Output Access Module

Common functions for reading and processing SuperCDMS DMC ROOT file outputs.
Uses uproot for pure-Python ROOT file reading to avoid C++ binding issues.

Trees accessed:
- G4SimDir/g4dmcTES: TES traces
- G4SimDir/g4dmcHits: Detector hits with unique EventNum
- G4SimDir/g4dmcEvent: Detector events (legacy)
- G4SimDir/mcevent: Monte Carlo events
"""

import numpy as np
import uproot
import logging

# Configure logging
logger = logging.getLogger(__name__)


def load_trace_data(file_path: str) -> dict:
    """
    Load TES trace data from g4dmcTES tree.

    Parameters
    ----------
    file_path : str
        Path to DMC ROOT file

    Returns
    -------
    dict
        Dictionary with keys: 'EventNum', 'ChanNum', 'Trace', 'Time'
    """
    try:
        with uproot.open(file_path) as f:
            tes_tree = f['G4SimDir/g4dmcTES']
            data = tes_tree.arrays(['EventNum', 'ChanNum', 'Trace', 'Time'], library='np')
        return data
    except Exception as e:
        logger.error(f"Failed to load trace data from {file_path}: {e}")
        return {}


def get_events_for_detector(file_paths: list[str], det_num: int) -> np.ndarray:
    """
    Get all EventNums that occurred in a specific detector from g4dmcHits tree.

    Parameters
    ----------
    file_paths : list[str]
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

    for file_path in file_paths:
        try:
            with uproot.open(file_path) as f:
                hits_tree = f['G4SimDir/g4dmcHits']
                det_nums = hits_tree['DetNum'].array(library='np')
                event_nums = hits_tree['EventNum'].array(library='np')
                mask = det_nums == det_num
                all_event_nums.extend(event_nums[mask])
        except Exception as e:
            logger.error(f"Failed to get detector events from {file_path}: {e}")
            return np.array([])

    return np.unique(all_event_nums)


def print_detector_summary(file_paths: list[str]) -> None:
    """Print which events are in which detectors from g4dmcHits tree."""
    logger.info("Building detector summary...")

    detector_events = {}

    # Load g4dmcHits for all files
    for file_path in file_paths:
        try:
            with uproot.open(file_path) as f:
                hits_tree = f['G4SimDir/g4dmcHits']
                det_nums = hits_tree['DetNum'].array(library='np')
                event_nums = hits_tree['EventNum'].array(library='np')

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
    print(f"Detector Summary (from g4dmcHits)")
    print(f"{'='*60}")

    for det_num in sorted(detector_events.keys()):
        events = sorted(detector_events[det_num])
        print(f"DetNum {det_num}: {len(events)} events")
        print(f"  Events: {events}")

    print(f"{'='*60}\n")


def inspect_file(file_path: str) -> dict:
    """
    Inspect a DMC ROOT file for key information.

    Parameters
    ----------
    file_path : str
        Path to DMC ROOT file

    Returns
    -------
    dict
        Dictionary with inspection results
    """
    result = {}

    # ---- g4dmcEvent ----
    try:
        with uproot.open(file_path) as f:
            event_tree = f['G4SimDir/g4dmcEvent']
            events = event_tree.arrays(['EventNum', 'DetNum', 'DetType'], library='np')
        result["g4dmcEvent_tree_exists"] = "yes"
        result["EventNum_contents"] = events["EventNum"]
        result["DetNum_values"] = list(np.unique(events["DetNum"]))
        result["DetType_values"] = list(np.unique(events["DetType"]))
    except Exception as e:
        logger.warning(f"Failed to load g4dmcEvent: {e}")
        result["g4dmcEvent_tree_exists"] = "no"
        result["EventNum_contents"] = ""
        result["DetNum_values"] = ""
        result["DetType_values"] = ""

    # ---- g4dmcHits ----
    try:
        with uproot.open(file_path) as f:
            hits_tree = f['G4SimDir/g4dmcHits']
            hits = hits_tree.arrays(['EventNum', 'DetNum', 'DetType'], library='np')
        result["g4dmcHits_tree_exists"] = "yes"
        result["Hits_EventNum_contents"] = hits["EventNum"]
        result["Hits_DetNum_values"] = list(np.unique(hits["DetNum"]))
        result["Hits_DetType_values"] = list(np.unique(hits["DetType"]))
    except Exception as e:
        logger.warning(f"Failed to load g4dmcHits: {e}")
        result["g4dmcHits_tree_exists"] = "no"
        result["Hits_EventNum_contents"] = ""
        result["Hits_DetNum_values"] = ""
        result["Hits_DetType_values"] = ""

    # ---- mcevent ----
    try:
        with uproot.open(file_path) as f:
            mcevent_tree = f['G4SimDir/mcevent']
            mcevent = mcevent_tree.arrays(['HitsPerEvent'], library='np')
        result["mcevent_tree_exists"] = "yes"
        result["HitsPerEvent_contents"] = mcevent["HitsPerEvent"]
    except Exception as e:
        logger.warning(f"Failed to load mcevent: {e}")
        result["mcevent_tree_exists"] = "no"
        result["HitsPerEvent_contents"] = ""

    return result


def get_trace_summary(file_paths: list[str]) -> dict:
    """
    Get summary statistics for traces across files.

    Parameters
    ----------
    file_paths : list[str]
        List of DMC ROOT file paths

    Returns
    -------
    dict
        Summary with total traces, unique events, unique channels
    """
    all_event_nums = []
    all_chan_nums = []

    for file_path in file_paths:
        data = load_trace_data(file_path)
        if data:
            all_event_nums.extend(data['EventNum'])
            all_chan_nums.extend(data['ChanNum'])

    # Count unique (EventNum, ChanNum) pairs to get actual number of traces
    unique_traces = len(np.unique(np.column_stack((all_event_nums, all_chan_nums)), axis=0))
    unique_events = len(np.unique(all_event_nums))
    unique_channels = len(np.unique(all_chan_nums))

    return {
        'total_unique_traces': unique_traces,
        'unique_events': unique_events,
        'unique_channels': unique_channels
    }