# SCDMS-DMC
In this repository, `run_dmc_quickscan.py` and the `dmc_utils` package are tools for scanning SuperCDMS SuperSim DMC output for the number of events per detector and TES traces. This is to check the simulation output has what you want before performing analysis or scaling up the simulation.

## Intended Use

`DMCQuickScan` is designed for **fast validation of simulation jobs**, helping confirm that:

* events were produced
* detectors registered hits
* TES traces are present
* traces are physically reasonable

It is **not intended for full analysis or reconstruction**, but as a lightweight pre‑analysis diagnostic tool.

---

# Requirements
- Run in a SuperCDMS module Apptainer container
   - Python
   - Python packages:
      - numpy
      - uproot
      - matplotlib
- Output ROOT files from SuperCDMS SuperSim DMC run

---

# Running `run_dmc_quickscan.py`

`DMCQuickScan` can be executed as a command‑line tool to quickly validate and inspect SuperCDMS DMC ROOT simulation output by the driver `run_dmc_quickscan.py`. `DMCQuickScan` leverages tools from `dmc_utils` to access DMC ROOT output tree arrays and extract quantities such as the number of events-per-detector and TESSim traces for specified events.

The CLI provides three primary capabilities:

1. **ROOT File Ingestion**

   * Accept a single ROOT file or a glob pattern of many files.
   * Optionally combine multiple ROOT files into a single analysis file.

2. **Simulation Structure Validation**
   Prints a branch‑level report summarizing the contents of key DMC trees:

   * `G4SimDir/mcevent` – Geant4 event records and total energy depositions
   * `G4SimDir/g4dmcHits` – Detector hits after hit merging
   * `G4SimDir/g4dmcEvent` – Events passed to CrystalSim
   * `G4SimDir/g4dmcTES` – TES channel traces produced by TESSim

3. **TES Trace Sanity Visualization**

   * Builds a detector → event index
   * Selects a detector to inspect
   * Produces TES trace plots for all channels in each event
   * Saves plots to disk for quick sanity checks

This tool is intended for **rapid validation of simulation output** before running deeper physics analysis or scaling up the simulation.

---

## Basic Usage

```bash
python run_dmc_quickscan.py \
    --files "/path/to/run/*.root" \
    --output ./quickscan_plots \
    --combine
    --detector 2
```

This will:

* scan all ROOT files matching the pattern
* print a branch summary
* identify TES events per detector
* generate TES trace plots for the selected detector

---

## Combining ROOT Files

If your simulation produced many ROOT files, they can be combined automatically before scanning:

```bash
python run_dmc_quickscan.py \
    --files "/path/to/run/*.root" \
    --combine
```

Internally this performs the equivalent of:

```bash
hadd combined.root *.root
```

The combined file name can be changed using:

```bash
--combined-name run_combined.root
```

---

## Event Selection

By default the scanner plots **all TES events** for the selected detector.

You can restrict the number of events plotted.

### First N Events

```bash
--events 5
```

Plots the first 5 events.

### Event Index Range

```bash
--event-range 10 20
```

Plots events with indices `[10, 20)`.

Note: indexing starts at **0**.

### Detector

Finally, to select the detector you want to plot traces for, specify its number.

For a single simulated Tower detector stack configuration, there are 6 detectors, numbered 1-6.

In the example simulation macro `simulation_jobs/CUTE-T3_Ba133_12inch_DMC_tuned.mac`, the detectors are arranged by the embedded macro `CDMSgeometry/macros/CUTE_T3_stack.mac` found here: [SuperSim macros - CUTE T3 stack](https://gitlab.com/supercdms/Simulations/supersim/-/blob/137a59df24a3fc5957f385bfb63d12491ddd582a/CDMSgeometry/macros/CUTE_T3_stack.mac) which does:

```bash
# Stack configuration
/CDMS/Layout/CrystalName G157 1
/CDMS/Layout/CrystalName S122 2
/CDMS/Layout/CrystalName G169 3
/CDMS/Layout/CrystalName G171 4
/CDMS/Layout/CrystalName S125 5
/CDMS/Layout/CrystalName G159 6
```

**Example:** To check traces from events in Silicon detectors with this configuration, run `run_dmc_quickscan` with
```bash
--detector 2
```

and again with

```bash
--detector 5
```

---

## Trace Plot Options

### Flip TES pulses

```bash
--flip
```

Flips the TES traces to be positive-going.

### Adjust time window

```bash
--xlim 25 50
```

Sets the TES trace plot x‑axis window in microseconds. The default (25, 50) is typically goood for centering on the pulse shape.

---

## Typical Workflow

A typical quick sanity check might look like:

```bash
python run_dmc_quickscan.py \
    --files "$SCRATCH/run/*.root" \
    --combine \
    --detector 3 \
    --events 10
```

This will:

1. Combine simulation output ROOT files
2. Print a branch structure report
3. Identify which detectors recorded TES events
4. Plot TES traces for the first 10 events in detector 3

---

# DMC Branch Report Documentation

This document explains the meaning of the printed DMC Branch Report generated by the SuperCDMS DMC Output Access Module, also driven by `run_dmc_quickscan.py`, and clarifies the physical meaning of each branch, along with common interpretations and relationships between quantities.

---

## 1. Overview of the Processing Chain

A single simulation proceeds through several stages:

1. **Geant4 simulation (mcevent)**

   * A “beamOn” corresponds to one physical event (e.g. one Ba-133 decay).
   * Particles produced in the decay propagate and deposit energy.

2. **SourceSim-level hits**

   * Each energy deposition in a detector is counted as a hit.
   * Multiple hits may occur per event, including across detectors.

3. **Hit merging (g4dmcHits)**

   * Nearby hits within a detector are merged if closer than a configurable threshold.
   * This reduces computational load for downstream simulation.

4. **CrystalSim event formation (g4dmcEvent)**

   * Defines the set of events that must be processed by CrystalSim.
   * May differ from Geant4 event count due to splitting across detectors or unmerged spatially separated hits.

5. **TES simulation output (g4dmcTES)**

   * Produces detector channel traces.
   * One trace per (event, channel) pair.

---

## 2. Physical Meaning of an “Event” vs a “Hit”

* **Event (Geant4 event)**: One `beamOn` interaction (e.g., one radioactive decay).
* **Hit**: A single energy deposition in a detector.
* **Merged hit**: A cluster of nearby hits treated as one effective interaction.
* **Trace**: TES output for a given event and channel.

Important nuance:

* One event can produce **multiple hits**.
* One hit may be **merged** with nearby hits.
* One event may produce **multiple detector interactions**, leading to multiple downstream DMC events.

---

## 3. Branch-by-Branch Interpretation

### 3.1 G4SimDir/mcevent

Represents Geant4 events that produced energy depositions in detectors.

* `event_count`: Number of Geant4 events with at least one detector interaction.
* `total_hits`: Total number of SourceSim-level hits (sum over events).

Example interpretation:

* 19 events produced detector interactions
* 36 total energy depositions occurred

---

### 3.2 G4SimDir/g4dmcHits

Represents detector hits after merging.

* `total_records`: Number of merged hits
* `unique_EventNum`: Number of contributing Geant4 events
* `events_per_detector`: Number of (merged) hits per detector

Key idea:

* This stage reduces raw hits via spatial merging.

Example interpretation:

* 36 raw hits → 25 merged hits

---

### 3.3 G4SimDir/g4dmcEvent

Represents events passed to CrystalSim.

Important nuance:

* This is NOT identical to Geant4 event count.
* A single Geant4 event can produce multiple g4dmcEvents if:

  * multiple detectors are hit
  * spatially separated hits are not merged

Example interpretation:

* 19 Geant4 events → 24 CrystalSim events

---

### 3.4 G4SimDir/g4dmcTES

TES simulation output per channel.

* `total_records`: Total TES traces
* `unique_EventNum`: Number of g4dmcEvents
* `unique_ChanNum`: Number of readout channels

Each g4dmcEvent produces a trace in every channel:

* Expected scaling:

  * `g4dmcTES traces = g4dmcEvent × number_of_channels`

Example:

* 24 events × 12 channels = 288 traces

---

## 4. Key Relationships Between Branches

### Event progression

```
mcevent (Geant4 events)
    ↓ produces
SourceSim hits
    ↓ merging
 g4dmcHits
    ↓ splitting across detectors / spatial logic
 g4dmcEvent
    ↓ channel expansion
 g4dmcTES
```

---

## 5. Subtle but Important Nuance

A key point:

> g4dmcEvent count is not equal to Geant4 event count

Because:

* A single Geant4 event may split into multiple DMC events
* Detector geometry + hit merging thresholds affect this mapping

---

## 6. Practical Guidance

When analyzing results:

* Use **mcevent** for physics event statistics
* Use **g4dmcHits** for detector-level interaction density
* Use **g4dmcEvent** for simulation workload (CrystalSim input size)
* Use **g4dmcTES** for final readout output size and channel occupancy

---

## 7. Summary

| Branch     | Meaning                              | Scaling behavior         |
| ---------- | ------------------------------------ | ------------------------ |
| mcevent    | Geant4 events with detector activity | physics-level            |
| g4dmcHits  | merged detector hits                 | reduced from raw hits    |
| g4dmcEvent | CrystalSim events                    | may exceed Geant4 events |
| g4dmcTES   | channel traces                       | event × channels         |

---

This document should be read alongside the printed branch report to correctly interpret simulation output consistency and scaling behavior.
