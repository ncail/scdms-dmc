"""
TES Trace Viewer - Interactive visualization tool for TESSim traces from DMC output.

This tool loads and visualizes raw pulses (DMC Intermediates) from DMC root files.
Traces are located in: outputfile.root > G4SimDir > g4dmcTES > Trace

Usage (Python API):
    viewer = TESTraceViewer(dmc_files)
    viewer.plot_trace(event_num=0, chan_num=0)
    viewer.plot_flipped_trace(event_num=0, chan_num=0)
    viewer.plot_comparison(event_num=0, chan_num=0, save_path='comparison.png')

Command Line:
    python tes_trace_viewer.py /path/to/dmc/files/*.root [--save-dir /path/to/save/]
"""

import logging
import argparse
from typing import List, Optional, Tuple
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

try:
    from cats.cdataframe import CDataFrame
except ImportError:
    raise ImportError("SCDMS CATS package is required. Load scdms module.")

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

        # Load pulses from root files
        try:
            self.pulses = CDataFrame(
                'G4SimDir/g4dmcTES', 
                self.dmc_files
            )
        except Exception as e:
            logger.error(f"Failed to load DMC files: {e}")
            raise

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

        # Filter for specific event and channel
        filtered = self.pulses.Filter(f'EventNum=={event_num} & ChanNum=={chan_num}')

        if len(filtered) == 0:
            raise ValueError(
                f"No trace found for event {event_num}, channel {chan_num}"
            )

        # Extract data
        trace_data = filtered.AsNumpy(['Trace'])['Trace'][0]
        event_nums = filtered.AsNumpy(['EventNum'])['EventNum'][0]
        chan_nums = filtered.AsNumpy(['ChanNum'])['ChanNum'][0]
        chan_names = filtered.AsNumpy(['ChanName'])['ChanName'][0]
        start = filtered.AsNumpy(['T0'])['T0'][0]
        width = filtered.AsNumpy(['BinWidth'])['BinWidth'][0]

        # Create time array (in microseconds)
        num_bins = len(trace_data)
        time_array = np.arange(
            start, 
            width * num_bins + start, 
            width
        ) * 1e-6

        return TESTrace(
            trace_data=trace_data,
            time_data=time_array,
            event_num=int(event_nums),
            chan_num=int(chan_nums),
            chan_name=chan_names.decode() if isinstance(chan_names, bytes) else chan_names,
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
        
        event_nums = self.pulses.AsNumpy(['EventNum'])['EventNum']
        chan_nums = self.pulses.AsNumpy(['ChanNum'])['ChanNum']

        # Count unique (EventNum, ChanNum) pairs to get actual number of traces
        unique_traces = len(np.unique(np.column_stack((event_nums, chan_nums)), axis=0))
        unique_events = len(np.unique(event_nums))
        unique_channels = len(np.unique(chan_nums))

        print(f"\n{'='*60}")
        print(f"TES Trace Summary")
        print(f"{'='*60}")
        print(f"Total unique traces: {unique_traces}")
        print(f"Unique events: {unique_events}")
        print(f"Unique channels: {unique_channels}")
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
    
    parser.add_argument(
        'file_pattern',
        help='Glob pattern for DMC root files (e.g., /path/to/files/*.root)'
    )
    parser.add_argument(
        '--save-dir',
        help='Directory to save plots as PNG files',
        default=None,
        type=str
    )
    parser.add_argument(
        '--no-display',
        action='store_true',
        help='Do not display plots (only save if --save-dir specified)'
    )
    
    args = parser.parse_args()
    
    # Load DMC files matching pattern
    # Works for a single root file location as well.
    import glob
    dmc_files = np.sort(glob.glob(args.file_pattern))
    
    if not dmc_files:
        print(f"Error: No DMC files found matching pattern: {args.file_pattern}")
        return 1
    
    print(f"Found {len(dmc_files)} DMC files")
    
    # Create viewer
    viewer = TESTraceViewer(dmc_files)
    
    # View available traces
    viewer.list_available_traces()
    
    # Create save directory if needed
    save_dir = None
    if args.save_dir:
        save_dir = Path(args.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Plots will be saved to {save_dir}")
    
    # Plot examples
    show_plots = not args.no_display
    
    # Plot first trace
    save_path = None
    if save_dir:
        save_path = save_dir / 'trace_event0_chan0.png'
    viewer.plot_trace(event_num=0, chan_num=0, show=show_plots, save_path=str(save_path))
    
    return 0


if __name__ == "__main__":
    exit(main())
