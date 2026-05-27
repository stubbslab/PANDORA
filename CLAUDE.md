# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What PANDORA is

PANDORA (Photometrically Adjusted Neutral Density Optical Ray Attenuator) is a hardware-control system for a laboratory instrument. It coordinates several physical subsystems over the network and serial buses: a monochromator, a LabJack-driven shutter and flip mounts, two Keysight B298x electrometers, Zaber linear stages, a StellarNet spectrograph, and an iOptron HAZ-series Alt-Az telescope mount. There is no test harness, lint config, or build step — running this code talks to real hardware on the configured IP addresses and serial ports.

## Environment setup

The project is not installed as a package. Two things must be set up in every shell before running anything:

```bash
cd ${HOME}/Documents/dev/versions/v2.0/PANDORA
export PYTHONPATH="${PWD}:${PYTHONPATH}"
alias pb="python ${PWD}/pandora/commands/pb.py"
```

Dependencies in `requirements.txt` are minimal (numpy, pyyaml, sphinx). The hardware libraries (`labjack-ljm`, `pyserial`, `zaber-motion`, `stellarnet_driverLibs`, etc.) are *not* declared there — they are assumed to be installed in the operator's environment. If imports fail, install the missing hardware SDK rather than adding it to `requirements.txt` blindly.

## Common commands

The primary interface is the `pb` CLI defined in `pandora/commands/pb.py`. Run `pb -h` for the full subcommand list, or `pb <command> --help` for a specific command. The most-used subcommands:

- `pb measure-pandora-tput-final <exptime> <lambda0> <lambdaEnd> --step ... --nrepeats ...` — production throughput scan with overflow recovery
- `pb measure-pandora-charge <exptime> <lambda0> <lambdaEnd> [--charge-range ...] [--auto-range]` — CHAR-mode (coulomb meter) scan
- `pb set-wavelength <nm>` / `pb get-wavelength`
- `pb open-shutter` / `pb close-shutter`
- `pb get-keysight-readout <exptime> --name K1|K2 [--rang0 ...] [--autoRange] [--nplc ...]`
- `pb get-spectrometer-readout <exptime_ms> [--is_plot]`
- `pb flip <name> --on|--off|--state` / `pb flip --listNames`
- `pb zaber <controller> <slot>` / `pb zaber <controller> --move <mm>` / `pb zaber --listZaberNames`
- `pb mount status|goto|home|park|unpark|stop|set-park|set-alt-limit` (iOptron HAZ — note: mount loses zenith on power loss)
- `pb run-keysight start|stop` — long-running continuous Keysight acquisition (background-style)

Docs build (Sphinx, sources in `docs/source/`): `cd docs && make html`. Output lands in `docs/build/html`.

There is no automated test suite. Files in `examples/` are ad-hoc hardware-exercising scripts, not pytest tests — they will attempt to talk to the real instrument and are not safe to run blindly. Notebooks in `notebooks/` are exploratory analyses of recorded data.

## Architecture

### Layered structure

The codebase is organized as four layers, each importing only from layers below it:

1. **Device drivers** — `pandora/controller/`. One module per piece of hardware, each exposing a Controller class:
   - `keysight.py` (B298x electrometers, both CURR and CHAR modes)
   - `monochromator.py` (serial, with built-in 2nd-order filter logic at the wavelength threshold from config)
   - `zaberstages.py` (Ethernet-controlled Zaber stages with named "slot maps" defined in `default.yaml`)
   - `stellarnet.py` (USB spectrograph)
   - `ioptron.py` (iOptron HAZ mount, serial)
2. **State abstractions** — `pandora/states/`. The shutter and flip mounts are not real "controllers"; they are LabJack digital-output channels. `labjack_handler.py` wraps the LabJack T-series. `shutter_state.py` and `flipmount_state.py` model on/off devices on top of it. Per-channel "InvertLogic" flags in `default.yaml` swap the active level — respect these when adding new flip mounts.
3. **Orchestrator** — `pandora/pandora_controller.py`. The `PandoraBox` class is the single class that ties every subsystem together. It loads `default.yaml`, instantiates all subsystem controllers, owns the database handle, and exposes the high-level routines: `take_exposure`, `take_dark`, `wavelength_scan2`, `measure_pandora_tput_final`, `charge_wavelength_scan`, `take_charge_triplet`, `set_wavelength`, `set_photodiode_scale`, etc. New high-level workflows belong as methods here (or as helpers in `pandora/commands/measure_*.py` that take a `PandoraBox` as their first argument — see `measure_pandora_throughput.py` and `measure_pandora_charge.py` for the pattern).
4. **CLI** — `pandora/commands/`. `pb.py` is an argparse-based dispatcher. Each subcommand maps to a function in either `utils.py` (lightweight commands that instantiate only the subsystem they need) or one of the `measure_*.py` modules (full `PandoraBox` workflows). When you add a CLI command, add the subparser in `pb.py` *and* the implementation function in the appropriate sibling module, then wire them with `set_defaults(func=...)`.

### Configuration

`default.yaml` at the repo root is the single source of truth for IP addresses, serial ports, baud rates, Zaber slot maps (named filter/pinhole positions), Keysight default settings (mode, range, NPLC, sample count, interval), the LabJack channel assignments, and the power-line frequency used for NPLC timing. `PandoraBox._load_config` reads it; `get_config_section`/`get_config_value` are the access pattern. Hardcoded fallbacks in code are a smell — prefer adding a key to `default.yaml`.

### Measurement modes (Keysight)

The B2985B/B2987B electrometers operate in two modes, set via `keysight.set_mode('CURR')` or `set_mode('CHAR')`:

- **CURR** (default): instantaneous current. Used by `take_exposure`, `wavelength_scan2`, all throughput routines. Saves to `currentInput`/`currentOutput` columns.
- **CHAR**: integrated charge (coulomb meter). Used by `charge_wavelength_scan`/`take_charge_triplet`. The feedback capacitor must be discharged between acquisitions (controlled by `--no-discharge`). Saves to `chargeInput`/`chargeOutput` columns with a `sampleTime` per data point. `charge_wavelength_scan` always restores CURR mode in a `finally` block.

Charge mode auto-ranging (`estimate_charge_range`) uses a fixed 20 µA calibration range during a D-L-D current measurement — *not* AUTO range — because AUTO can't re-range fast enough between dark and light phases. If you change this, read the comment block in `estimate_charge_range` first.

### Database

`pandora/database/db.py` is a CSV-backed run logger, not a real database. Each "run" is identified by a `run_id` of the form `YYYYMMDDXXX` (auto-incremented in `.run_cache.csv` under the configured `database.root`). Per-row schema lives in `pandora/database/columns_map.py` (`COLUMN_DEFINITIONS` for types, `DEFAULT_VALUES` for defaults). To log a new field, you must add it to *both* dicts — `add()` raises `KeyError` for unknown columns. Two write paths exist:

- `write_exposure()` — buffer-and-flush in one call; back-compat for per-exposure writes.
- `buffer_exposure()` + `flush()` — batched writes. Use this in tight loops like `take_charge_triplet`, where every sample is a row; per-row CSV append is O(n²).

Calibration files (throughput curves, QE curves, etc.) live under `database.root/calib/` and are accessed via `PandoraCalibrationDatabase` (`pandora/database/calib_db.py`).

### Logging

Initialize once via `pandora.utils.logger.initialize_central_logger`. The orchestrator and all CLI entry points already do this. Log file path and level come from the `logging` section of `default.yaml`. Module loggers use the `pandora.<subsystem>` namespace (e.g. `pandora.controller`, `pandora.database`).

### Safety / hardware quirks worth knowing before editing

- The shutter is *closed* when `activate()`'d and *open* when `deactivate()`'d (it is a normally-open relay being driven shut). Don't "fix" this without understanding the wiring.
- Flip-mount channels each have an `InvertLogic` flag in `default.yaml` because the relay polarity differs per mount. Read the flag, don't hardcode.
- The iOptron mount does *not* persist its home/zenith across power cycles — after a power loss the operator must re-acquire zenith manually. Mount commands that assume a known reference frame should fail loudly if `mount status` reports an unknown state.
- The monochromator order-blocking filter is auto-engaged by `set_wavelength` whenever the requested wavelength exceeds `monochromator.wav_second_order_filter` (default 520 nm). Bypassing `set_wavelength` skips this — don't.
- Z2 (focus) Zaber can mechanically collide with photodiode 2; a `safety_threshold` is intentionally commented out in `default.yaml` and Z2 is currently disabled in `initialize_subsystems`. Re-enabling it requires re-establishing that interlock.
