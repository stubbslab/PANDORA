"""
Command line interface for measuring charge vs wavelength.

Uses the B2985B/B2987B electrometer in coulomb meter (CHAR) mode to measure
accumulated charge instead of instantaneous current.

Usage:
    pb measure-pandora-charge 0.5 300 700 --step 5 --nrepeats 10
    pb measure-pandora-charge 0.1 500 520 --step 5 --nrepeats 2 --verbose

"""

import numpy as np
import os
from utils import _initialize_logger

script_dir = os.path.dirname(os.path.realpath(__file__))
default_cfg = os.path.join(script_dir, "../../default.yaml")


def check_measure_pandora_charge(args):
    """Validate input arguments for charge measurement."""

    # Check step is reasonable
    if np.modf(args.step * 10)[0] != 0:
        warning_msg = "Step size in Angstrom units is not an integer, it will be rounded to the nearest integer in Angstroms"
        print(warning_msg)

    # Wavelength range validation
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

    Measures accumulated charge (Coulombs) vs wavelength using the
    B2985B/B2987B electrometer in CHAR mode.

    Parameters
    ----------
    args : argparse.Namespace
        Expected to contain: lambda0, lambdaEnd, step, exptime, darktime,
        nrepeats, discharge, verbose.
    """
    print("Measuring Pandora charge")
    check_measure_pandora_charge(args)

    # Initialize logging
    _initialize_logger(args.verbose)

    from pandora.pandora_controller import PandoraBox
    pb = PandoraBox(config_file=default_cfg, verbose=args.verbose, init_zaber=False)

    # Run charge wavelength scan
    print(f"Scanning wavelength from {args.lambda0} to {args.lambdaEnd} nm in steps of {args.step} nm")
    print(f"Integration time: {args.exptime} s, repeats per wavelength: {args.nrepeats}")
    print("This might take a while...")

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
    print("Done! Thanks for waiting")
