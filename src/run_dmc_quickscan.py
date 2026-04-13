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

Typical usage:
    python run_dmc_quickscan.py
"""

from dmc_utils import (
    DMCQuickScan, 
    ScanConfig
)

# ------------------------------------------------------------
# Main entry point for DMCQuickScan
# ------------------------------------------------------------

def main():
    """
    Entry point for DMC QuickScan execution.

    Configuration:
        file_pattern (str) : Directory or file pattern to your simulation output ROOT files
        output_dir   (str) : Directory where you want TES trace plots to be output
        file_mode    (str) : Mode for handling input files ("single" or "combined")
            - "single"     : Process a single ROOT file
            - "combined"   : Combine multiple ROOT files into one for a simulation-wide scan
        combined_name (str): Name for the combined ROOT file if file_mode is "combined"
        detector     (int) : Detector ID to scan (1-6 for a SuperCDMS Tower)
        flip         (bool): Whether to flip the TES trace plots
        xlim        (tuple): X-axis limits for the TES trace plots in microseconds (e.g., (25, 50) to focus on the main pulse region)
    """
    config = ScanConfig(
        file_pattern="/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/CUTE*.root",
        output_dir="/home/nevenac/projects/scdms-dmc/output/testing_scanner",
        file_mode="combined",
        combined_name="run_combined.root",
        detector=2,
        flip=True,
        xlim=(25, 50),
    )

    # Load ROOT files, optionally combine into one, and initialize the DMCQuickScan object
    scanner = DMCQuickScan(config)

    # Print to terminal summary of each DMC ROOT branch
    scanner.print_summary()

    # Prints the TESSim EventNum indices that registered per detector
    scanner.get_tessim_events()

    # Generate TES trace sanity plots for all events in the selected detector (configured above)
    # Each plot is all 12 channel traces for an event. 
    # Arguments --
    #   None: All events that occurred in the detector are looped through and plotted.
    #   int: The first N events that occurred in the detector are plotted (e.g., 10 to plot the first 10 events).
    #   Tuple[int, int]: A range of events to plot (e.g., (0, 10) to plot the first 10 events)
    # scanner.run_sanity_plots(3)


if __name__ == "__main__":
    main()