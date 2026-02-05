# Plan: Charge Measurement Command Integration

**Date:** 2026-02-05
**Goal:** Add `measure-pandora-charge` command following the pattern of `measure-pandora-throughput-beta`

---

## Overview

Integrate charge measurement capability into the PANDORA CLI, enabling wavelength scans that measure accumulated charge (Coulombs) instead of instantaneous current (Amperes). This uses the B2985B/B2987B electrometer's coulomb meter mode.

---

## Phase 1: KeysightController Enhancements

**File:** `pandora/controller/keysight.py`

### 1.1 Add Discharge Methods

```python
def discharge(self):
    """Zero the feedback capacitor before a new charge measurement."""
    self.write('SENS:CHAR:DISCharge')

def set_auto_discharge(self, enabled=True, level=None):
    """
    Configure automatic discharge to prevent range overflow.

    Args:
        enabled: Enable/disable auto-discharge
        level: Threshold in Coulombs (2e-9, 2e-8, 2e-7, 2e-6)
    """
    state = 'ON' if enabled else 'OFF'
    self.write(f'SENS:CHAR:DISCharge:AUTO {state}')
    if level is not None:
        self.write(f'SENS:CHAR:DISCharge:LEVel {level}')
```

### 1.2 Add Charge-Aware Acquire Wrapper

```python
def acquire_charge(self, discharge_first=True, **kwargs):
    """Acquire charge data, optionally discharging the capacitor first."""
    if discharge_first:
        self.discharge()
        time.sleep(0.05)  # brief settling time after discharge
    self.acquire(**kwargs)
```

### 1.3 Add Charge Range Table for Auto-Scale

```python
CHARGE_RANGES = [
    2e-9,   # 2 nC  (resolution: 1 fC)
    2e-8,   # 20 nC (resolution: 10 fC)
    2e-7,   # 200 nC (resolution: 100 fC)
    2e-6,   # 2 µC  (resolution: 1 pC)
]

def auto_scale_charge(self, rang0=2e-8):
    """
    Auto-scale for charge mode. Similar to auto_scale() but uses charge ranges.
    """
    # Implementation similar to auto_scale() but with CHARGE_RANGES
    # and reading CHAR data instead of CURR
```

### 1.4 Update wait_for_settle (Optional)

Either:
- Add charge-specific settling times, or
- Skip settling for charge mode (feedback capacitor doesn't have same RC settling)

---

## Phase 2: New Command Module

**File:** `pandora/commands/measure_pandora_charge.py`

### 2.1 Structure

```python
"""
Command line interface for measuring charge vs wavelength.

Usage:
    pb measure-pandora-charge 0.5 300 700 --step 5 --nrepeats 10
"""

import numpy as np
import os
from utils import _initialize_logger

script_dir = os.path.dirname(os.path.realpath(__file__))
default_cfg = os.path.join(script_dir, "../../default.yaml")


def check_measure_pandora_charge(args):
    """Validate input arguments."""
    if args.lambda0 < 200 or args.lambdaEnd > 1100:
        raise ValueError("Wavelength range must be between 200 and 1100 nm")
    if args.lambda0 > args.lambdaEnd:
        raise ValueError("lambda0 must be less than lambdaEnd")
    if args.step <= 0:
        raise ValueError("Step size must be greater than 0")
    if args.nrepeats <= 0:
        raise ValueError("Number of repeats must be greater than 0")
    if args.exptime <= 0:
        raise ValueError("Exposure time must be greater than 0")


def measurePandoraCharge(args):
    """
    Main entry point for charge measurement wavelength scan.
    """
    print("Measuring Pandora charge")
    check_measure_pandora_charge(args)

    _initialize_logger(args.verbose)

    from pandora.pandora_controller import PandoraBox
    pb = PandoraBox(config_file=default_cfg, verbose=args.verbose, init_zaber=False)

    # Run charge wavelength scan
    pb.charge_wavelength_scan(
        args.lambda0,
        args.lambdaEnd,
        args.step,
        args.exptime,
        dark_time=args.darktime,
        nrepeats=args.nrepeats,
        discharge_before_acquire=args.discharge,
    )

    print(f"Charge scan saved to {pb.pdb.run_data_file}")
    print("Done!")
```

---

## Phase 3: PandoraBox Controller Additions

**File:** `pandora/pandora_controller.py`

### 3.1 Add Charge Wavelength Scan Method

```python
def charge_wavelength_scan(self, start, end, step, exptime, dark_time=None,
                            nrepeats=100, discharge_before_acquire=True):
    """
    Wavelength scan measuring charge instead of current.

    Similar to wavelength_scan2() but:
    - Sets Keysight to CHAR mode
    - Discharges capacitor before each acquisition
    - Saves charge values instead of current
    """
    self.logger.info(f"Starting charge wavelength scan {start}-{end} nm...")

    wavelengths = np.arange(start, end + step, np.round(step, 1))

    # Switch to charge mode
    self.keysight.k1.set_mode('CHAR')
    self.keysight.k2.set_mode('CHAR')

    # Auto-scale for charge ranges
    self.set_wavelength(start - 10)
    self.keysight.k1.auto_scale_charge()
    self.keysight.k2.auto_scale_charge()

    if dark_time is None:
        dark_time = exptime

    for wav in wavelengths:
        self.logger.info(f"Charge scan: lambda = {wav:.1f} nm")
        self.set_wavelength(wav)

        # Baseline dark
        self.take_charge_exposure(dark_time, is_dark=True,
                                   discharge=discharge_before_acquire)

        for _ in range(nrepeats):
            # Light exposure
            self.take_charge_exposure(exptime, is_dark=False,
                                       discharge=discharge_before_acquire)
            # Closing dark
            self.take_charge_exposure(dark_time, is_dark=True,
                                       discharge=discharge_before_acquire)

    # Restore current mode
    self.keysight.k1.set_mode('CURR')
    self.keysight.k2.set_mode('CURR')

    self.logger.info("Charge wavelength scan completed.")
```

### 3.2 Add Charge Exposure Method

```python
def take_charge_exposure(self, exptime, is_dark=False, discharge=True):
    """
    Take a single charge measurement.

    Similar to take_exposure_per_sample() but:
    - Calls discharge() before acquire
    - Reads CHAR data
    - Saves charge fields
    """
    self.keysight.k1.on()
    self.keysight.k2.on()

    self.keysight.k1.set_acquisition_time(exptime)
    self.keysight.k2.set_acquisition_time(exptime)

    timestamp = datetime.now()

    if is_dark:
        self.close_shutter()
    else:
        self.open_shutter()

    self.timer.mark("ChargeExposure")

    # Discharge and acquire
    if discharge:
        self.keysight.k1.discharge()
        self.keysight.k2.discharge()
        time.sleep(0.05)

    self.keysight.k1.acquire()
    self.keysight.k2.acquire()

    self.timer.sleep(exptime)
    self.close_shutter()
    eff_exptime = self.timer.elapsed_since("ChargeExposure")

    # Read charge data
    d1 = self.keysight.k1.read_data(wait=True)
    d2 = self.keysight.k2.read_data(wait=True)

    # Save with charge fields
    self._save_charge_exposure(d1, d2, timestamp, exptime, eff_exptime,
                                "charge", not is_dark)
```

### 3.3 Add Charge Save Method

```python
def _save_charge_exposure(self, d1, d2, timestamp, exptime, eff_exptime,
                           description, shutter_flag=True):
    """Save charge measurement to database."""
    self.pdb.add("exptime", float(exptime))
    self.pdb.add("timestamp", timestamp)
    self.pdb.add("effective_exptime", eff_exptime)
    self.pdb.add("wavelength", float(self.wavelength))
    self.pdb.add("chargeInput", np.abs(np.mean(d1['CHAR'])))
    self.pdb.add("chargeOutput", np.abs(np.mean(d2['CHAR'])))
    self.pdb.add("chargeInputErr", np.std(d1['CHAR']))
    self.pdb.add("chargeOutputErr", np.std(d2['CHAR']))
    self.pdb.add('shutter', shutter_flag)
    self.pdb.add("measurementMode", "CHAR")
    self.pdb.add("Description", description)

    # Save flip mount states (same as _save_exposure)
    for name in self.flipMountNames[1:]:
        fm = getattr(self, name, None)
        if fm is None:
            self.pdb.add(name, False)
            continue
        st = getattr(fm, "state", None)
        raw = getattr(st, "value", st)
        flag = str(raw).lower() == "on"
        self.pdb.add(name, flag)
```

---

## Phase 4: CLI Integration

**File:** `pandora/commands/pb.py`

### 4.1 Add Import

```python
from measure_pandora_charge import measurePandoraCharge
```

### 4.2 Add Subparser

```python
# command: measure-pandora-charge
charge_parser = subparsers.add_parser(
    "measure-pandora-charge",
    help="Measure accumulated charge vs wavelength using the B2985B/B2987B electrometer."
)
charge_parser.add_argument("exptime", type=float,
    help="Integration time per measurement (s).")
charge_parser.add_argument("lambda0", type=float,
    help="Start wavelength (nm).")
charge_parser.add_argument("lambdaEnd", type=float,
    help="End wavelength (nm).")
charge_parser.add_argument("--step", type=float, default=1,
    help="Wavelength step (nm).")
charge_parser.add_argument("--nrepeats", type=int, default=100,
    help="Number of repeats per wavelength.")
charge_parser.add_argument("--darktime", type=float, default=None,
    help="Dark exposure time (s). Defaults to exptime.")
charge_parser.add_argument("--discharge", action="store_true", default=True,
    help="Discharge capacitor before each acquisition (default: True).")
charge_parser.add_argument("--no-discharge", dest="discharge", action="store_false",
    help="Skip discharge (for continuous accumulation).")
charge_parser.add_argument("--verbose", action="store_true",
    help="Enable verbose output.")
charge_parser.set_defaults(func=measurePandoraCharge)
```

---

## Phase 5: Testing

### 5.1 Unit Tests

- Test `discharge()` sends correct SCPI command
- Test `set_auto_discharge()` with various levels
- Test `auto_scale_charge()` finds appropriate range
- Test mode switching between CURR and CHAR

### 5.2 Integration Tests

```bash
# Short test scan
pb measure-pandora-charge 0.1 500 510 --step 5 --nrepeats 2 --verbose

# Full scan
pb measure-pandora-charge 0.5 300 700 --step 5 --nrepeats 10 --verbose
```

### 5.3 Verify Output

- Check database contains `chargeInput`, `chargeOutput` fields
- Verify charge values are in expected range (fC to µC)
- Compare with current measurement at same conditions

---

## Phase 6: Documentation Updates

**Location:** `docs/source/` (ReadTheDocs: https://pandora-box.readthedocs.io)

### 6.1 Update Command Line Reference (`docs/source/command_line.rst`)

Add new section for charge measurement command:

```rst
Charge Measurement
------------------

Measure accumulated charge versus wavelength using the B2985B/B2987B electrometer in coulomb meter mode. This is useful for integrating low-level signals over time.

.. code-block:: bash

   pb measure-pandora-charge <exptime> <lambda0> <lambdaEnd> [options]

**Positional Arguments**:

- ``exptime``: Integration time per measurement (seconds).
- ``lambda0``: Start wavelength (nm).
- ``lambdaEnd``: End wavelength (nm).

**Options**:

- ``--step <nm>``: Wavelength step size (default: 1 nm).
- ``--nrepeats <n>``: Number of repeats per wavelength (default: 100).
- ``--darktime <s>``: Dark exposure time. Defaults to exptime if not specified.
- ``--discharge``: Discharge capacitor before each acquisition (default: enabled).
- ``--no-discharge``: Skip discharge for continuous charge accumulation.
- ``--verbose``: Enable detailed console output.

**Examples**:

.. code-block:: bash

   # Basic charge scan from 300-700 nm
   pb measure-pandora-charge 0.5 300 700 --step 5 --nrepeats 10

   # Quick test scan with verbose output
   pb measure-pandora-charge 0.1 500 520 --step 5 --nrepeats 2 --verbose

   # Continuous accumulation (no discharge between measurements)
   pb measure-pandora-charge 1.0 400 600 --step 10 --no-discharge

.. note::

   Charge measurement mode is only available on B2985B and B2987B electrometers
   (not B2981B/B2983B picoammeters).
```

### 6.2 Update Overview Section

Update the command list in the Overview section to include `measure-pandora-charge`:

```rst
   {measure-pandora-throughput,measure-pandora-charge,set-wavelength,...}
     measure-pandora-throughput    Measure throughput (current mode).
     measure-pandora-charge        Measure charge vs wavelength (coulomb mode).
```

### 6.3 Update Keysight Electrometers Section

Add note about measurement modes:

```rst
Keysight Electrometers
----------------------

The Keysight B2980B series electrometers support two measurement modes:

- **Current mode (CURR)**: Measures instantaneous current (Amperes). Used by
  ``measure-pandora-throughput`` and ``get-keysight-readout``.
- **Charge mode (CHAR)**: Measures accumulated charge (Coulombs) via an
  integrating feedback capacitor. Used by ``measure-pandora-charge``.
  Only available on B2985B/B2987B models.

Charge measurement ranges: 2 nC, 20 nC, 200 nC, 2 µC (resolution down to 1 fC).
```

### 6.4 Add Reference to Controlling Subsystems (`docs/source/controlling_subsystems.rst`)

If applicable, add a subsection describing programmatic charge measurement:

```rst
Charge Measurement Mode
~~~~~~~~~~~~~~~~~~~~~~~

To measure charge programmatically:

.. code-block:: python

   from pandora.controller.keysight import KeysightController

   keysight = KeysightController(name="K01", keysight_ip="169.254.5.2")
   keysight.set_mode('CHAR')           # Switch to charge mode
   keysight.set_rang(2e-8)             # 20 nC range
   keysight.set_nplc(0.1)
   keysight.discharge()                # Zero the capacitor
   keysight.acquire()
   data = keysight.read_data(wait=True)
   print(data['CHAR'])                 # Charge values in Coulombs
```

### 6.5 Build and Verify Documentation

```bash
cd docs/
make html
# Open build/html/index.html to verify
```

Verify on ReadTheDocs after merge:
- https://pandora-box.readthedocs.io/en/latest/command_line.html

---

## Implementation Order

1. **KeysightController** - Add `discharge()`, `set_auto_discharge()`, `CHARGE_RANGES`, `auto_scale_charge()`
2. **PandoraBox** - Add `take_charge_exposure()`, `_save_charge_exposure()`, `charge_wavelength_scan()`
3. **Command module** - Create `measure_pandora_charge.py`
4. **CLI** - Wire up in `pb.py`
5. **Test** - Run short wavelength scan to verify
6. **Documentation** - Update `command_line.rst`, `controlling_subsystems.rst`, rebuild docs

---

## Notes

- Only B2985B and B2987B support charge mode (not B2981B/B2983B)
- Charge ranges: 2 nC, 20 nC, 200 nC, 2 µC
- Discharge zeroes the integrating capacitor - essential before each measurement
- NPLC controls A/D digitization window, not integration time
- The feedback capacitor accumulates charge continuously until discharged
