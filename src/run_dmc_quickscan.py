"""
DMC QuickScan Driver Script

This script provides a high-level entry point for validating and inspecting SuperCDMS SuperSim DMC ROOT output files produced by simulation jobs.

It performs three main tasks:

    1. ROOT file ingestion
    - Accepts either a file pattern or directory of ROOT files
    - Optionally combines multiple ROOT files into a single analysis file

    2. Structural validation
    - Prints a branch-level summary of key DMC trees:
        - mcevent (Geant4 events and energy deposits)
        - g4dmcHits (post-hit merging detector hits)
        - g4dmcEvent (CrystalSim input events)
        - g4dmcTES (TES channel traces)

    3. TES sanity visualization
    - Builds a detector -> event index
    - Selects a detector to display events from
    - Generates TES trace plots for all events in that detector
    - Produces both raw and optionally normalized views

This tool is intended for quick sanity checks before deeper analysis, not full-scale physics reconstruction.

Example usage:

    python run_dmc_quickscan.py \
        --files "/scratch/run/*.root" \
        --output ./plots \
        --detector 2 \
        --combine \
        --events 10
"""

# CLI argument parsing
import argparse

# DMC output accessors
from dmc_utils import (
    DMCQuickScan,
    ScanConfig
)

# Logging
import logging
logger = logging.getLogger()


def parse_args():
    """
    Parse command line arguments for DMCQuickScan.
    """

    parser = argparse.ArgumentParser(
        description="Quick sanity scanner for SuperCDMS DMC ROOT output."
    )

    parser.add_argument(
        "--files",
        required=True,
        help="ROOT file pattern or directory (e.g. '/path/*.root')"
    )

    parser.add_argument(
        "--output",
        default="./quickscan_output",
        help="Directory where plots will be saved"
    )

    parser.add_argument(
        "--detector",
        type=int,
        default=1,
        help="Detector number to inspect"
    )

    parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine all ROOT files into a single analysis file"
    )

    parser.add_argument(
        "--combined-name",
        default="combined.root",
        help="Filename for combined ROOT file"
    )

    parser.add_argument(
        "--flip",
        action="store_true",
        help="Flip TES traces vertically"
    )

    parser.add_argument(
        "--xlim",
        nargs=2,
        type=float,
        metavar=("XMIN", "XMAX"),
        default=(25, 50),
        help="Time window in microseconds for plotting traces"
    )

    parser.add_argument(
        "--events",
        type=int,
        help="Plot first N events"
    )

    parser.add_argument(
        "--event-range",
        nargs=2,
        type=int,
        metavar=("START", "STOP"),
        help="Plot event index range"
    )

    return parser.parse_args()


def main(args):
    """
    Entry point for DMCQuickScan CLI.

    Configuration: 
        file_pattern (str) : Directory or file pattern to your simulation output ROOT files 
        output_dir (str)   : Directory where you want TES trace plots to be output 
        file_mode (str)    : Mode for handling input files ("single" or "combined") 
            - "single"     : Process a single ROOT file 
            - "combined"   : Combine multiple ROOT files into one for a simulation-wide scan 
        combined_name (str): Name for the combined ROOT file if file_mode is "combined" 
        detector (int)     : Detector ID to scan (1-6 for a SuperCDMS Tower) 
        flip (bool)        : Whether to flip the TES trace plots 
        xlim (tuple)       : X-axis limits for the TES trace plots in microseconds (e.g., (25, 50) to focus on the main pulse region)
    """

    file_mode = "combined" if args.combine else "single"

    config = ScanConfig(
        file_pattern=args.files,
        output_dir=args.output,
        file_mode=file_mode,
        combined_name=args.combined_name,
        detector=args.detector,
        flip=args.flip,
        xlim=tuple(args.xlim)
    )

    # Load configurations in scanner
    scanner = DMCQuickScan(config)

    # Print DMC branch report
    scanner.print_summary()

    # Get detailed report of TESSim events per detector
    scanner.get_tessim_events()

    # Determine event selection
    event_selection = None

    if args.events is not None:
        event_selection = args.events

    elif args.event_range is not None:
        event_selection = tuple(args.event_range)

    # Plot TES traces for selected events
    scanner.run_sanity_plots(event_selection)


if __name__ == "__main__":
    args = parse_args()
    main(args)
