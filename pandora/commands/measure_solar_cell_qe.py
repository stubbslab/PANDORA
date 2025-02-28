"""

Command line interface for measuring solar cell quantum efficiency.

Usage:
    pb measure-solar-cell-qe --lambda0 400 --lambdaEnd 700 --step 1 --nrepeats 3
"""

from pandora.calibration.solarcell_qe import computeSolarCellQE
from pandora.calibration.nist_qe import getNISTQE

import numpy as np

def measureSolarCellQE(args):
    print("Measuring Solar Cell QE")
    from pandora.pandora_controller import PandoraBox
    pandora_box = PandoraBox(config_file="../default.yaml", verbose=True)

    # Take the measurements with no ND filter
    pandora_box.move_nd_filter("CLEAR")

    print(f"Scanning the wavelength from {args.lambda0} to {args.lambdaEnd} in steps of {args.step} with {args.nrepeats} repeats")
    print("this might take a while...")
    # Scan the wavelength in linear steps from lambda0 to lambdaEnd
    # Takes one dark, one exposure, one dark, moves to the next wavelength
    pandora_box.solar_cell_qe_curve(args.lambda0, args.lambdaEnd, args.step, nrepeats=args.nrepeats)

    # Compute the throughput
    lambdaBins = np.arange(args.lambda0-args.step/2, args.lambdaEnd+args.step*3/2, args.step)

    # get the data taken
    df = pandora_box.get_database()

    # Get the NIST QE curve
    print("Getting NIST QE curve")
    qeNIST = getNISTQE()

    print("Calculating Solar Cell QE")
    transmission = computeSolarCellQE(df, qeNIST, specBins=lambdaBins)
    
    print("Saving solar cell qe")
    # Save the throughput calibration file
    pandora_box.write_calibration(transmission, "sollar_cell_qe")

    print("Done! Thanks for waiting")
    