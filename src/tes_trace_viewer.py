"""
TES Trace Viewer - Interactive visualization tool for TESSim traces from DMC output.

This tool loads and visualizes raw pulses (DMC Intermediates) from DMC root files.
Traces are located in: outputfile.root > G4SimDir > g4dmcTES > Trace

Uses uproot for pure-Python ROOT file reading (avoids C++ binding issues).

Usage (Python API):
    viewer = TESTraceViewer(dmc_files)
    events = viewer.get_events_for_detector(det_num=2)  # Get events for detector
    viewer.plot_trace(event_num=events[0], chan_num=0)
    viewer.print_detector_summary()  # See detector summary

Command Line:
    # See detector summary and which events are in which detectors
    python tes_trace_viewer.py --file-pattern /path/to/file.root --print-detectors
    
    # Plot first trace from detector 2
    python tes_trace_viewer.py /path/to/file.root --det-num 2 --save-dir /path/to/save/
"""

import logging
import argparse
from typing import List, Optional, Tuple
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

# CDataFrame is crashing for me when loading the g4dmcTES tree, so using uproot instead for this viewer.
import uproot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TESTrace:
    """Container for a single TES trace with metadata and time information."""

    def __init__(
        self,
        trace_data: np.ndarray,
        time_data: np.ndarray,
        event_num: int,
        chan_num: int,
        chan_name: str,
    ):
        """
        Initialize a TES trace.

        Parameters
        ----------
        trace_data : np.ndarray
            The trace amplitude values (microamperes)
        time_data : np.ndarray
            Time axis in microseconds
        event_num : int
            Event number identifier
        chan_num : int
            Channel number identifier
        chan_name : str
            Human-readable channel name
        """
        self.data = trace_data
        self.time = time_data
        self.event_num = event_num
        self.chan_num = chan_num
        self.chan_name = chan_name

    def flip(self) -> np.ndarray:
        """Return vertically flipped trace (max - data)."""
        return np.max(self.data) - self.data

    @property
    def duration_us(self) -> float:
        """Duration of trace in microseconds."""
        return self.time[-1] - self.time[0]

    @property
    def amplitude_range(self) -> Tuple[float, float]:
        """Min and max amplitude of trace."""
        return float(np.min(self.data)), float(np.max(self.data))


class TESTraceViewer:
    """Main viewer class for TES traces from DMC output files."""

    def __init__(self, dmc_files: List[str] | str):
        """
        Initialize the trace viewer.

        Parameters
        ----------
        dmc_files : List[str] or str
            Path(s) to DMC root files
        """
        self.dmc_files = dmc_files if isinstance(dmc_files, list) else [dmc_files]
        logger.info(f"Loading DMC files: {self.dmc_files}")

        # Load trees from root files using uproot
        try:
            logger.info("Loading G4SimDir/g4dmcTES tree from ROOT files...")
            self.trees = []
            for file_path in self.dmc_files:
                with uproot.open(file_path) as f:
                    tree = f['G4SimDir/g4dmcTES']
                    self.trees.append(tree)
            logger.info(f"Successfully loaded {len(self.trees)} tree(s)")
                
        except Exception as e:
            logger.error(f"Failed to load DMC files: {e}")
            raise

    def get_events_for_detector(self, det_num: int) -> np.ndarray:
        """
        Get all EventNums that occurred in a specific detector.

        Parameters
        ----------
        det_num : int
            Detector number

        Returns
        -------
        np.ndarray
            Sorted unique EventNums for this detector
        """
        logger.info(f"Finding events for DetNum=={det_num}...")
        all_event_nums = []
        
        for file_path in self.dmc_files:
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

    def get_trace(
        self, 
        event_num: int = 0, 
        chan_num: int = 0
    ) -> TESTrace:
        """
        Retrieve a specific trace.

        Parameters
        ----------
        event_num : int, optional
            Event number (default: 0)
        chan_num : int, optional
            Channel number (default: 0)

        Returns
        -------
        TESTrace
            The requested trace with metadata
        """
        logger.info(f"Retrieving trace: event={event_num}, channel={chan_num}")

        # Search through all trees for the matching event and channel
        for tree in self.trees:
            # Read arrays from tree
            event_nums = tree['EventNum'].array(library='np')
            chan_nums = tree['ChanNum'].array(library='np')
            
            # Find matching index
            mask = (event_nums == event_num) & (chan_nums == chan_num)
            indices = np.where(mask)[0]
            
            if len(indices) > 0:
                idx = indices[0]
                
                # Extract data for this entry
                trace_data = tree['Trace'].array(library='np')[idx]
                chan_names = tree['ChanName'].array(library='np')[idx]
                start = tree['T0'].array(library='np')[idx]
                width = tree['BinWidth'].array(library='np')[idx]
                
                # Create time array (in microseconds)
                num_bins = len(trace_data)
                time_array = np.arange(
                    start, 
                    width * num_bins + start, 
                    width
                ) * 1e-6
                
                # Handle channel name encoding
                if isinstance(chan_names, bytes):
                    chan_names = chan_names.decode()
                
                return TESTrace(
                    trace_data=trace_data,
                    time_data=time_array,
                    event_num=event_num,
                    chan_num=chan_num,
                    chan_name=str(chan_names),
                )
        
        # Not found in any tree
        raise ValueError(
            f"No trace found for event {event_num}, channel {chan_num}"
        )

    def plot_trace(
        self,
        event_num: int = 0,
        chan_num: int = 0,
        xlim: Tuple[float, float] = (-1, 10),
        figsize: Tuple[float, float] = (10, 6),
        show: bool = True,
        save_path: Optional[str] = None,
    ) -> Figure:
        """
        Plot a trace.

        Parameters
        ----------
        event_num : int, optional
            Event number (default: 0)
        chan_num : int, optional
            Channel number (default: 0)
        xlim : tuple, optional
            X-axis limits in microseconds (default: (-1, 10))
        figsize : tuple, optional
            Figure size (width, height) in inches
        show : bool, optional
            Whether to display the plot (default: True)
        save_path : str, optional
            Path to save plot as PNG (default: None, do not save)

        Returns
        -------
        Figure
            Matplotlib figure object
        """
        trace = self.get_trace(event_num, chan_num)

        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(trace.time, trace.data, linewidth=1.5, color='steelblue')
        ax.set_xlabel(r"Time ($\mu$s)", fontsize=11)
        ax.set_ylabel("Current (µA)", fontsize=11)
        ax.set_xlim(xlim)
        ax.set_title(
            f'TES Trace: {trace.chan_name} (Event {trace.event_num}, Channel {trace.chan_num})',
            fontsize=12,
            fontweight='bold'
        )
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')

        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        
        if show:
            plt.show()

        return fig

    def plot_flipped_trace(
        self,
        event_num: int = 0,
        chan_num: int = 0,
        xlim: Tuple[float, float] = (-1, 10),
        figsize: Tuple[float, float] = (10, 6),
        show: bool = True,
        save_path: Optional[str] = None,
    ) -> Figure:
        """
        Plot a vertically flipped trace (inverted amplitude).

        Parameters
        ----------
        event_num : int, optional
            Event number (default: 0)
        chan_num : int, optional
            Channel number (default: 0)
        xlim : tuple, optional
            X-axis limits in microseconds (default: (-1, 10))
        figsize : tuple, optional
            Figure size (width, height) in inches
        show : bool, optional
            Whether to display the plot (default: True)
        save_path : str, optional
            Path to save plot as PNG (default: None, do not save)

        Returns
        -------
        Figure
            Matplotlib figure object
        """
        trace = self.get_trace(event_num, chan_num)
        flipped = trace.flip()

        fig, ax = plt.subplots(figsize=figsize)
        ax.plot(trace.time, flipped, linewidth=1.5, color='coral')
        ax.set_xlabel(r"Time ($\mu$s)", fontsize=11)
        ax.set_ylabel("Current (µA)", fontsize=11)
        ax.set_xlim(xlim)
        ax.set_title(
            f'Flipped TES Trace: {trace.chan_name} (Event {trace.event_num}, Channel {trace.chan_num})',
            fontsize=12,
            fontweight='bold'
        )
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#f8f9fa')

        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved plot to {save_path}")
        
        if show:
            plt.tight_layout()
            plt.show()

        return fig

    def list_available_traces(self) -> None:
        """Print summary of available traces in the loaded DMC files."""
        logger.info("Fetching trace summary...")
        
        all_event_nums = []
        all_chan_nums = []
        
        # Collect event and channel numbers from all trees
        for tree in self.trees:
            all_event_nums.extend(tree['EventNum'].array(library='np'))
            all_chan_nums.extend(tree['ChanNum'].array(library='np'))
        
        all_event_nums = np.array(all_event_nums)
        all_chan_nums = np.array(all_chan_nums)

        # Count unique (EventNum, ChanNum) pairs to get actual number of traces
        unique_traces = len(np.unique(np.column_stack((all_event_nums, all_chan_nums)), axis=0))
        unique_events = len(np.unique(all_event_nums))
        unique_channels = len(np.unique(all_chan_nums))

        print(f"\n{'='*60}")
        print(f"TES Trace Summary")
        print(f"{'='*60}")
        print(f"Total unique traces: {unique_traces}")
        print(f"Unique events: {unique_events}")
        print(f"Unique channels: {unique_channels}")
        print(f"{'='*60}\n")

    def print_detector_summary(self) -> None:
        """Print which events are in which detectors."""
        logger.info("Building detector summary...")
        
        detector_events = {}
        
        # Load g4dmcEvent for all files
        for file_path in self.dmc_files:
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
        print(f"Detector Summary")
        print(f"{'='*60}")
        
        for det_num in sorted(detector_events.keys()):
            events = sorted(detector_events[det_num])
            print(f"DetNum {det_num}: {len(events)} events")
            print(f"  Events: {events}")
        
        print(f"{'='*60}\n")


def main():
    """Load DMC files from command line and visualize traces."""
    parser = argparse.ArgumentParser(
        description="TES Trace Viewer - Visualize DMC TESSim traces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tes_trace_viewer.py '/path/to/dmc/files/*.root'
  python tes_trace_viewer.py '/path/to/dmc/files/*.root' --save-dir ./plots/
        """
    )
    
    parser.add_argument('file_pattern',
        help='Glob pattern for DMC root files (e.g., /path/to/files/*.root)',
        default=None,
        type=str
    )
    parser.add_argument('--det-num',
        help='Filter to traces from a specific detector number',
        default=None,
        type=int
    )
    parser.add_argument('--save-dir',
        help='Directory to save plots as PNG files',
        default=None,
        type=str
    )
    parser.add_argument('--no-display',
        action='store_true',
        help='Do not display plots (only save if --save-dir specified)'
    )
    parser.add_argument('--print-detectors',
        action='store_true',
        help='Print summary of which events are in which detectors and exit'
    )
    
    args = parser.parse_args()
    
    # Load DMC files matching pattern
    # Works for a single root file location as well.
    import glob
    dmc_files = sorted(glob.glob(args.file_pattern))
    
    if not dmc_files:
        print(f"Error: No DMC files found matching pattern: {args.file_pattern}")
        return 1
    
    print(f"Found {len(dmc_files)} DMC file(s)")
    
    # Create viewer
    viewer = TESTraceViewer(dmc_files)
    
    # Print detector summary
    if args.print_detectors:
        viewer.print_detector_summary()
        return 0
    
    # View available traces
    viewer.list_available_traces()
    
    # Get events to plot
    events_to_plot = []
    if args.det_num is not None:
        # Get all events for this detector
        events_to_plot = viewer.get_events_for_detector(args.det_num)
        print(f"Found {len(events_to_plot)} events for DetNum=={args.det_num}: {events_to_plot}")
    else:
        # Just plot first event
        events_to_plot = [0]
    
    # Create save directory if needed
    save_dir = None
    if args.save_dir:
        save_dir = Path(args.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Plots will be saved to {save_dir}")
    
    # Plot examples
    show_plots = not args.no_display
    
    # Plot first trace from first event
    event_num = events_to_plot[0]
    save_path = None
    if save_dir:
        save_path = str(save_dir / f'trace_event{event_num}_chan0.png')
    viewer.plot_trace(
        event_num=event_num, 
        chan_num=0, 
        show=show_plots, 
        save_path=save_path
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
