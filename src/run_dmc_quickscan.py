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
        file_pattern : Directory or file pattern to your simulation output ROOT files
        output_dir   : Directory where you want TES trace plots to be output
        file_mode    : 
        combined_name:
        detector     :
        flip         :
        normalize    :
        xlim         :
    """
    config = ScanConfig(
        file_pattern="/home/nevenac/scratch/CUTE-T3_Ba133_12inch_DMC_10kevents/*.root",
        output_dir="/home/nevenac/projects/scdms-dmc/output/",
        file_mode="combined",
        combined_name="run_combined.root",
        detector=3,
        flip=True,
        normalize=False,
        xlim=(25, 50),
    )

    scanner = DMCQuickScan(config)

    # Print to terminal summary of each DMC ROOT branch
    scanner.print_summary()
    scanner.build_index()
    scanner.run_sanity_plots()


if __name__ == "__main__":
    main()