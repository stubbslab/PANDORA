"""

Command line interface for measuring pandora throughput.

Usage:
    pb measure-pandora-throughput --lambda0 300 --lambdaEnd 700 --step 1 --maskPorts A

"""

# from pandora.calibration.transmission import measureTransmission
import numpy as np
import os
from utils import _initialize_logger

script_dir = os.path.dirname(os.path.realpath(__file__))
default_cfg = os.path.join(script_dir, "../../default.yaml")

def check_measure_pandora_throughput(args):
    # if step is not integer raise warning
    # if not isinstance(args.step, int):
    if np.modf(args.step*10)[0] != 0:
        warning_msg = "Step size in Angstrom units is not an integer, it will be rounded to the nearest integer in Angstroms"
        print(warning_msg)

    # if args.step 
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
    
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Final overflow‑safe throughput routine wrapper (CLI level)
# Call with: pb measure-pandora-tput-final ... (added in pb.py dispatcher)
# ─────────────────────────────────────────────────────────────────────────────

def measurePandoraTputFinal(args):
    """CLI wrapper that builds a PandoraBox and calls its
    ``measure_pandora_tput_final`` method (which must exist on PandoraBox).

    Parameters
    ----------
    args : argparse.Namespace
        Expected to contain: lambda0, lambdaEnd, step, exptime, darktime,
        nrepeats, verbose.
    """
    print("Measuring Pandora throughput (final overflow-safe routine)")
    check_measure_pandora_throughput(args)

    # initialise logging first so we capture everything
    _initialize_logger(args.verbose)

    from pandora.pandora_controller import PandoraBox
    pb = PandoraBox(config_file=default_cfg, verbose=args.verbose, init_zaber=False)

    # Run the new robust routine that lives on the controller object
    pb.measure_pandora_tput_final(
        args.lambda0,
        args.lambdaEnd,
        args.step,
        args.exptime,
        dark_time=getattr(args, "darktime", None),
        nrepeats=args.nrepeats,
        observation_type="throughput",
    )

    print(f"wavelength-scan saved on {pb.pdb.run_data_file}")
    print("Done! Thanks for waiting")
    return


def measurePandoraThroughputBeta(args):
    print("Measuring Pandora throughput")
    check_measure_pandora_throughput(args)

    _initialize_logger(args.verbose)

    from pandora.pandora_controller import PandoraBox   
    pandora_box = PandoraBox(config_file=default_cfg, verbose=args.verbose, init_zaber = False)

    # print("Clear the optical path, no ND filters")
    # Take the measurements with no ND filter
    #filter_name = str(args.ndFilter)
    #pandora_box.set_nd_filter(filter_name.upper())

    # pinhole mask filter name
    # mask_name = str(args.pinholeMask)
    # pandora_box.set_pinhole_mask(mask_name.upper())

    # check if you can flip the mount
    if args.flip is not None:
        name = str(args.flip)
        # flip name activate
        getattr(pandora_box, name).activate()
        print(f"Flip mount {name} is now activated")

    # TODO: Implement turn_on_sollar_cell
    # pandora_box.turn_on_sollar_cell()

    print(f"Scanning the wavelength from {args.lambda0} to {args.lambdaEnd} in steps of {args.step} with {args.nrepeats} repeats")
    print("this might take a while...")
    # Scan the wavelength in linear steps from lambda0 to lambdaEnd
    # Takes one dark, one exposure, one dark, moves to the next wavelength
    pandora_box.wavelength_scan2(args.lambda0, args.lambdaEnd, args.step, args.exptime, observation_type="throughput", nrepeats=args.nrepeats, dark_time=args.darktime)

    if args.flip is not None:
        name = str(args.flip)
        # flip name activate
        getattr(pandora_box, name).deactivate()
        print(f"Flip mount {name} is now activated")


    print(f"wavelength-scan saved on {pandora_box.pdb.run_data_file}")
    print("Done! Thanks for waiting")
    pass

def measurePandoraThroughput(args):
    print("Measuring Pandora throughput")
    check_measure_pandora_throughput(args)

    from pandora.pandora_controller import PandoraBox   
    pandora_box = PandoraBox(config_file=default_cfg, verbose=args.verbose, init_zaber=False)

    # print("Clear the optical path, no ND filters")
    # Take the measurements with no ND filter
    #filter_name = str(args.ndFilter)
    #pandora_box.set_nd_filter(filter_name.upper())

    # pinhole mask filter name
    # mask_name = str(args.pinholeMask)
    # pandora_box.set_pinhole_mask(mask_name.upper())

    # TODO: Implement turn_on_sollar_cell
    # pandora_box.turn_on_sollar_cell()

    # Select the pinhole mask
    # print("Select the pinhole mask")
    # pandora_box.set_pinhole_mask(args.maskPorts)

    print(f"Scanning the wavelength from {args.lambda0} to {args.lambdaEnd} in steps of {args.step} with {args.nrepeats} repeats")
    print("this might take a while...")
    # Scan the wavelength in linear steps from lambda0 to lambdaEnd
    # Takes one dark, one exposure, one dark, moves to the next wavelength
    pandora_box.wavelength_scan(args.lambda0, args.lambdaEnd, args.step, args.exptime, observation_type="throughput", nrepeats=args.nrepeats)
    print(f"wavelength-scan saved on {pandora_box.pdb.run_data_file}")

    # TODO: Implement the transmission curve calculation
    ####################################################
    # Compute the throughput
    # lambdaBins = np.arange(args.lambda0-args.step/2, args.lambdaEnd+args.step*3/2, args.step)
    # get solar cell qe curve
    # print("Getting solar cell QE curve")
    # TODO: Convert Diode QE data to calibration format
    # TODO: Convert solar cell QE data to calibration format
    # solarQE = pandora_box.get_qe_solarcell()
    # diodeQE = pandora_box.get_qe_diode()

    # get the data taken
    # df = pandora_box.get_database()

    # print("Calculating throughput")
    # transmission, dfCalib = measureTransmission(df, solarQE, diodeQE, specBins=lambdaBins)
    
    # print("Saving throughput calibration file")
    # Save the throughput calibration file
    # pandora_box.write_calibration(transmission, "throughput")

    print("Done! Thanks for waiting")
    pass
